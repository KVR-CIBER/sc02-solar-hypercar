#!/usr/bin/env python3
"""
SC-02 on-board Raspberry Pi 4.

- Reads a Bluetooth gamepad (Turtle Beach Recon Cloud or any Xbox/PS layout) via evdev.
- Serves a phone controller + live power page over its own Wi-Fi (hotspot "SC-02"): http://10.42.0.1
- Forwards drive commands to the ESP32-S3 over UART (/dev/serial0, 115200) at 50 Hz, reads its telemetry.
- Priority: gamepad (if touched in the last 0.5 s) > phone > nothing (ESP failsafe stops the car after 0.3 s).

Gamepad: right trigger = throttle, left trigger = brake / reverse, left stick = steer,
         A = toggle drive/race mode (race = launch control on the ESP), Y = boost (6.0 V limit), B = normal (4.8 V).
Run:  python3 sc02_pi.py            (see README.md for the service + hotspot)
Test: python3 sc02_pi.py --mock     (no serial, no gamepad; fake telemetry)
"""
import argparse, asyncio, json, math, os, time
from aiohttp import web

ap = argparse.ArgumentParser()
ap.add_argument("--serial", default="/dev/serial0")
ap.add_argument("--port", type=int, default=80)
ap.add_argument("--mock", action="store_true")
args = ap.parse_args()

state = dict(thr=0.0, steer=0.0, brake=0.0, src="none", t_pad=0.0, t_phone=0.0,
             tel=dict(vbus=0, ibat=0, duty=0, steer=0, speed=0, mode=0, t12=None), pi_w=3.4, esp_w=0.45, mode="DRIVE")
HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ serial link to the ESP32-S3
class Link:
    def __init__(self):
        self.ser = None
        if not args.mock:
            import serial
            self.ser = serial.Serial(args.serial, 115200, timeout=0)
        self.buf = b""
    def send(self, line):
        if self.ser: self.ser.write((line + "\n").encode())
    def poll(self):
        if not self.ser:
            t = time.time(); d = state["thr"]
            state["tel"].update(vbus=12.4 - 1.2 * abs(d), ibat=0.45 + 3.5 * abs(d), duty=d, steer=state["steer"],
                                speed=abs(d) * 6 + 0.2 * math.sin(t), mode=0)
            return
        self.buf += self.ser.read(512)
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            p = line.decode(errors="ignore").strip().split(",")
            if len(p) >= 9 and p[0] == "T":
                state["tel"] = dict(vbus=int(p[2]) / 1000, ibat=int(p[3]) / 1000, duty=int(p[4]) / 1000, steer=int(p[5]) / 1000,
                                    speed=int(p[6]) / 1000, mode=int(p[7]), t12=None if int(p[8]) < 0 else int(p[8]) / 1000)
link = Link()

# ------------------------------------------------------------------ gamepad (evdev)
async def gamepad_task():
    if args.mock:
        return
    import evdev
    from evdev import ecodes as E
    while True:
        dev = None
        for path in evdev.list_devices():
            d = evdev.InputDevice(path)
            caps = d.capabilities().get(E.EV_ABS, [])
            codes = [c[0] if isinstance(c, tuple) else c for c in caps]
            if E.ABS_X in codes and (E.ABS_RZ in codes or E.ABS_GAS in codes):
                dev = d; break
        if not dev:
            await asyncio.sleep(2); continue
        print("gamepad:", dev.name)
        info = {c: dev.absinfo(c) for c in (E.ABS_X, E.ABS_Z, E.ABS_RZ, E.ABS_GAS, E.ABS_BRAKE) if c in [x[0] if isinstance(x, tuple) else x for x in dev.capabilities()[E.EV_ABS]]}
        def norm(code, v):
            a = info[code]; return (v - a.min) / max(1, a.max - a.min)
        rt = lt = sx = 0.0
        try:
            async for ev in dev.async_read_loop():
                if ev.type == E.EV_ABS:
                    if ev.code in (E.ABS_RZ, E.ABS_GAS): rt = norm(ev.code, ev.value)
                    elif ev.code in (E.ABS_Z, E.ABS_BRAKE): lt = norm(ev.code, ev.value)
                    elif ev.code == E.ABS_X: sx = norm(ev.code, ev.value) * 2 - 1
                    sx_d = 0 if abs(sx) < 0.07 else sx
                    if lt > 0.03 and state["tel"]["speed"] < 0.3: thr = -0.6 * lt; brk = 0.0
                    else: thr, brk = rt, lt
                    state.update(thr=thr, brake=brk, steer=-sx_d, src="pad", t_pad=time.time())
                elif ev.type == E.EV_KEY and ev.value == 1:
                    if ev.code in (E.BTN_SOUTH, E.BTN_A): toggle_mode()
                    elif ev.code in (E.BTN_NORTH, E.BTN_Y): link.send("C,vmax=6.0")
                    elif ev.code in (E.BTN_EAST, E.BTN_B): link.send("C,vmax=4.8")
        except OSError:
            print("gamepad disconnected"); await asyncio.sleep(1)

def toggle_mode():
    state["mode"] = "RACE" if state["mode"] == "DRIVE" else "DRIVE"
    link.send(state["mode"])

# ------------------------------------------------------------------ 50 Hz command loop
async def control_task():
    while True:
        now = time.time()
        if now - state["t_pad"] > 0.5 and now - state["t_phone"] > 0.5:
            state.update(thr=0.0, brake=0.0, steer=0.0, src="none")
        link.send(f"D,{int(state['thr'] * 1000)},{int(state['steer'] * 1000)},{int(state['brake'] * 1000)}")
        link.poll()
        await asyncio.sleep(0.02)

# ------------------------------------------------------------------ web: phone controller + telemetry websocket
async def ws_handler(req):
    ws = web.WebSocketResponse(heartbeat=5); await ws.prepare(req)
    async def push():
        while not ws.closed:
            t = state["tel"]; pm = max(0.0, t["vbus"] * t["ibat"] - state["pi_w"] - state["esp_w"])
            await ws.send_str(json.dumps(dict(v=t["vbus"], i=t["ibat"], p=t["vbus"] * t["ibat"], pm=pm, pi=state["pi_w"], esp=state["esp_w"],
                                              spd=t["speed"], mode=state["mode"], src=state["src"], t12=t["t12"])))
            await asyncio.sleep(0.1)
    task = asyncio.create_task(push())
    async for msg in ws:
        try:
            d = json.loads(msg.data)
            if "thr" in d and time.time() - state["t_pad"] > 0.5:
                state.update(thr=max(-1, min(1, d["thr"])), steer=max(-1, min(1, d["steer"])), brake=max(0, min(1, d.get("brake", 0))), src="phone", t_phone=time.time())
            if d.get("cmd") == "mode": toggle_mode()
            if d.get("cmd") == "vmax": link.send(f"C,vmax={float(d['v']):.1f}")
        except Exception:
            pass
    task.cancel(); return ws

async def index(req):
    return web.FileResponse(os.path.join(HERE, "phone.html"))

async def main():
    app = web.Application()
    app.router.add_get("/", index); app.router.add_get("/ws", ws_handler)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", args.port).start()
    print(f"SC-02 pi on :{args.port}  (serial {'MOCK' if args.mock else args.serial})")
    await asyncio.gather(control_task(), gamepad_task())

if __name__ == "__main__":
    asyncio.run(main())
