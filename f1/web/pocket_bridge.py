"""Pocket -> sim bridge: reads the RadioMaster Pocket as a HID joystick (USB 'Radiomaster Pocket Joystick' or Bluetooth
'ExpressLRS Joystick') and streams its 8 channels + buttons to the browser as Server-Sent Events on :8091.
The sim (rc.js) uses this instead of the browser Gamepad API, so no browser support / learning is needed.
Run: ~/Downloads/solar-olympiade/.venv/bin/python f1/web/pocket_bridge.py"""
import hid, json, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEVICES = {(0x1209, 0x4F54): ("Pocket USB", 2047.0), (0xE502, 0xBBAB): ("Pocket Bluetooth", 32767.0)}
state = {"name": None, "ch": [0.0] * 8, "btn": 0, "t": 0.0}


def reader():
    while True:
        dev = None
        for d in hid.enumerate():
            key = (d["vendor_id"], d["product_id"])
            if key in DEVICES and d["usage_page"] == 1 and d["usage"] in (4, 5):
                dev = (key, d["path"]); break
        if not dev:
            state["name"] = None; time.sleep(1.0); continue
        (key, path), (name, full) = dev, DEVICES[dev[0]]
        try:
            h = hid.device(); h.open_path(path); h.set_nonblocking(False)
            print("verbonden:", name, flush=True)
            while True:
                r = h.read(64, 1000)
                if not r:
                    continue
                # report: [id, buttons lo, buttons hi, 8x 16-bit little-endian channel values, (hat)]
                vals = [r[3 + 2 * i] | (r[4 + 2 * i] << 8) for i in range(8)]
                if name == "Pocket Bluetooth":           # ExpressLRS BLE joystick axes X,Y,Z,Rz,Rx,Ry,S1,S2 = CH1,2,5,6,3,4,7,8
                    vals = [vals[0], vals[1], vals[4], vals[5], vals[2], vals[3], vals[6], vals[7]]
                state.update(name=name, ch=[round(v / full * 2 - 1, 4) for v in vals], btn=r[1] | (r[2] << 8), t=time.time())
        except Exception as e:
            print("verbinding weg:", e, flush=True); state["name"] = None; time.sleep(1.0)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
        try:
            while True:
                fresh = state["name"] and time.time() - state["t"] < 0.5
                msg = {"name": state["name"] if fresh else None, "ch": state["ch"], "btn": state["btn"]}
                self.wfile.write(f"data: {json.dumps(msg)}\n\n".encode()); self.wfile.flush()
                time.sleep(1 / 60)
        except (BrokenPipeError, ConnectionResetError):
            pass


threading.Thread(target=reader, daemon=True).start()
print("Pocket-brug op http://localhost:8091  (Ctrl+C om te stoppen)", flush=True)
ThreadingHTTPServer(("127.0.0.1", 8091), H).serve_forever()
