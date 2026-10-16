#!/usr/bin/env python3
"""
Pit / timing station for the solar car (Raspberry Pi 4).

- Web page (phone or laptop on the "solarpit" hotspot): http://<pi>:8080
- GO button -> starts the car over Wi-Fi (car in test mode) and starts the clock.
- Finish gate: IR break-beam on GPIO17 at the 12 m line stops the clock.
- After the run it downloads the car's 500 Hz log, stores everything in runs/, and plots
  speed vs. time together with the simulation prediction.
- Launch-control settings can be changed from the page (they are stored on the car).

Run on the Pi:   python3 pit.py
Test on a Mac:   python3 pit.py --mock      (fake car + fake gate, nothing to connect)
"""
import argparse, csv, io, json, math, os, threading, time
from flask import Flask, jsonify, request, Response

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
os.makedirs(RUNS, exist_ok=True)
SIM_TRACE = next((p for p in (os.path.join(HERE, "sim_trace.json"),
                              os.path.join(HERE, "..", "sim", "out", "sim_trace.json")) if os.path.exists(p)), None)

ap = argparse.ArgumentParser()
ap.add_argument("--car", default="http://solarcar.local", help="car base URL (or http://<ip>)")
ap.add_argument("--gate-pin", type=int, default=17, help="BCM pin of the finish-gate receiver")
ap.add_argument("--gate-broken-level", choices=("low", "high"), default="low",
                help="receiver pin level while the beam is broken (Adafruit break-beam: low). Check the 'gate' pill.")
ap.add_argument("--port", type=int, default=8080)
ap.add_argument("--mock", action="store_true", help="no car / no GPIO: simulate everything")
args = ap.parse_args()

# ------------------------------------------------------------------ car link
if args.mock:
    class FakeCar:
        """Replays the simulation so the whole page can be tested without hardware."""
        def __init__(self):
            self.cfg = dict(start_duty=0.45, ramp_ms=350, stop_m=14.0, timeout_ms=5000, mm_per_pulse=31.42,
                            start_delay_ms=0, pwm_hz=20000, wifi=True, hall=True)
            self.t0 = None
            self.trace = json.load(open(SIM_TRACE)) if SIM_TRACE else None
        def get(self, path):
            if path == "/status":
                st = "running" if self.t0 and time.time() - self.t0 < 2.6 else ("done" if self.t0 else "idle")
                return dict(state=st, vbat=5.21, config=self.cfg, last=dict(t12=2.33 if st == "done" else None))
            if path == "/config":
                return self.cfg
            if path == "/log.csv":
                out = ["t_ms,duty,vbat_V,pulses,dist_m"]
                tr = self.trace
                for t, x, vb in zip(tr["t"], tr["x"], tr["vbus"]):
                    d = min(1, self.cfg["start_duty"] + (1 - self.cfg["start_duty"]) * t * 1000 / max(1, self.cfg["ramp_ms"]))
                    p = int(x * 1000 / self.cfg["mm_per_pulse"])
                    out.append(f"{int(t*1000)},{d:.3f},{vb:.3f},{p},{p*self.cfg['mm_per_pulse']/1000:.4f}")
                return "\n".join(out) + "\n"
        def post(self, path, data=None):
            if path == "/go":
                self.t0 = time.time(); gate.fake_break(self.t0 + 2.33)
            if path == "/config" and data:
                for k, v in data.items():
                    if k in self.cfg:
                        self.cfg[k] = type(self.cfg[k])(v) if not isinstance(self.cfg[k], bool) else str(v).lower() in ("1", "true")
            return {"ok": True}
    car = FakeCar()
else:
    import requests
    class Car:
        def __init__(self, base): self.base = base.rstrip("/")
        def get(self, path):
            r = requests.get(self.base + path, timeout=3)
            return r.text if path.endswith(".csv") else r.json()
        def post(self, path, data=None):
            return requests.post(self.base + path, data=data or {}, timeout=3).json()
    car = Car(args.car)

# ------------------------------------------------------------------ finish gate
class Gate:
    def __init__(self):
        self.t_break = None
        self.armed = False
        self.blocked = False
        if not args.mock:
            from gpiozero import DigitalInputDevice
            self.dev = DigitalInputDevice(args.gate_pin, pull_up=True)   # value 1 <=> pin LOW
            self.dev.when_activated = lambda: self._edge(pin_high=False)
            self.dev.when_deactivated = lambda: self._edge(pin_high=True)
    def _broken(self, pin_high):
        return pin_high if args.gate_broken_level == "high" else not pin_high
    def _edge(self, pin_high):
        t = time.perf_counter()
        self.blocked = self._broken(pin_high)
        if self.blocked and self.armed and self.t_break is None:
            self.t_break = t
    def state(self):
        return self.blocked if args.mock else self._broken(not self.dev.value)
    def fake_break(self, at_wall):
        def hit():
            if self.armed and self.t_break is None:
                self.t_break = time.perf_counter()
        threading.Timer(max(0, at_wall - time.time()), hit).start()

gate = Gate()

# ------------------------------------------------------------------ runs
current = {"state": "idle"}
lock = threading.Lock()

def run_thread(note):
    global current
    try:
        cfg = car.get("/config")
        gate.t_break = None
        gate.armed = True
        t_send = time.perf_counter()
        car.post("/go")
        t_ack = time.perf_counter()
        t_start = t_send + (t_ack - t_send) / 2            # best estimate of the car's start instant
        with lock:
            current = {"state": "running", "rtt_ms": round((t_ack - t_send) * 1000, 1)}
        deadline = time.time() + cfg.get("timeout_ms", 5000) / 1000 + 2
        while time.time() < deadline:
            st = car.get("/status")
            if st.get("state") in ("done", "idle") and time.time() > deadline - cfg.get("timeout_ms", 5000) / 1000 - 1.5:
                break
            time.sleep(0.2)
        time.sleep(0.3)
        gate.armed = False
        st = car.get("/status")
        log = car.get("/log.csv")
        gate_t = (gate.t_break - t_start) if gate.t_break else None
        run_id = time.strftime("%Y%m%d-%H%M%S")
        rec = dict(id=run_id, note=note, config=cfg, gate_t=gate_t, rtt_ms=current.get("rtt_ms"),
                   car=st.get("last"), vbat_before=st.get("vbat"))
        open(os.path.join(RUNS, run_id + ".csv"), "w").write(log)
        json.dump(rec, open(os.path.join(RUNS, run_id + ".json"), "w"), indent=1)
        with lock:
            current = {"state": "idle", "last": rec}
    except Exception as e:  # keep the page alive whatever happens
        gate.armed = False
        with lock:
            current = {"state": "error", "error": str(e)}

def list_runs():
    out = []
    for fn in sorted(os.listdir(RUNS), reverse=True):
        if fn.endswith(".json"):
            out.append(json.load(open(os.path.join(RUNS, fn))))
    return out

def speed_from_log(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    t = [int(r["t_ms"]) / 1000 for r in rows]
    x = [float(r["dist_m"]) for r in rows]
    vb = [float(r["vbat_V"]) for r in rows]
    v = []
    w = 25  # 50 ms window
    for i in range(len(t)):
        a, b = max(0, i - w), min(len(t) - 1, i + w)
        v.append((x[b] - x[a]) / (t[b] - t[a]) if t[b] > t[a] else 0)
    return dict(t=t, v=v, x=x, vbat=vb)

# ------------------------------------------------------------------ web
app = Flask(__name__)

@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")

@app.get("/api/state")
def api_state():
    try:
        st = car.get("/status"); ok = True
    except Exception as e:
        st, ok = {"error": str(e)}, False
    with lock:
        cur = dict(current)
    return jsonify(car_ok=ok, car=st, pit=cur, gate_blocked=gate.state())

@app.post("/api/go")
def api_go():
    if current.get("state") == "running":
        return jsonify(error="already running"), 409
    note = (request.get_json(silent=True) or {}).get("note", "")
    threading.Thread(target=run_thread, args=(note,), daemon=True).start()
    return jsonify(ok=True)

@app.post("/api/stop")
def api_stop():
    return jsonify(car.post("/stop"))

@app.post("/api/config")
def api_config():
    return jsonify(car.post("/config", request.get_json(silent=True) or {}))

@app.get("/api/runs")
def api_runs():
    return jsonify(list_runs())

@app.get("/api/run/<rid>")
def api_run(rid):
    rid = os.path.basename(rid)
    return jsonify(meta=json.load(open(os.path.join(RUNS, rid + ".json"))),
                   data=speed_from_log(open(os.path.join(RUNS, rid + ".csv")).read()))

@app.get("/api/sim")
def api_sim():
    return jsonify(json.load(open(SIM_TRACE)) if SIM_TRACE else {})

PAGE = r"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Solar pit</title><style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2230;--mut:#6b7385;--acc:#2563eb;--ok:#16a34a;--bad:#dc2626;--line:#e3e6ec}
@media (prefers-color-scheme:dark){:root{--bg:#11141a;--card:#1a1f28;--ink:#e8ebf1;--mut:#9aa3b5;--line:#2a313d}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 system-ui,sans-serif}
main{max-width:860px;margin:auto;padding:16px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:12px}
h1{font-size:20px;margin:4px 0 12px}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
button{font:inherit;border:0;border-radius:10px;padding:10px 16px;background:var(--line);color:var(--ink);cursor:pointer}
#go{background:var(--ok);color:#fff;font-size:22px;padding:14px 40px}#stop{background:var(--bad);color:#fff}
.pill{padding:3px 10px;border-radius:99px;background:var(--line);font-size:13px}.big{font-size:34px;font-weight:700}
label{font-size:13px;color:var(--mut)}input{font:inherit;width:90px;padding:6px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:6px;border-bottom:1px solid var(--line);text-align:left}tr:hover{background:var(--bg);cursor:pointer}
canvas{width:100%;height:260px}</style></head><body><main>
<h1>Solar car - pit</h1>
<div class=card><div class=row><button id=go onclick=go()>GO</button><button id=stop onclick="post('/api/stop')">STOP</button>
<span class=pill id=carst>car ?</span><span class=pill id=gate>gate ?</span><span class=pill id=vb>battery ?</span></div>
<div class=row style="margin-top:10px"><div><label>last time (finish gate)</label><div class=big id=tgate>-</div></div>
<div><label>car odometry 12 m</label><div class=big id=tcar>-</div></div><div><label>top speed</label><div class=big id=vmax>-</div></div></div></div>
<div class=card><b>Launch control</b> <span style="color:var(--mut);font-size:13px">(stored on the car)</span>
<div class=row style="margin-top:8px">
<div><label>start duty</label><br><input id=start_duty type=number step=0.05 min=0.1 max=1></div>
<div><label>ramp ms</label><br><input id=ramp_ms type=number step=25></div>
<div><label>stop after m</label><br><input id=stop_m type=number step=0.5></div>
<div><label>mm / pulse</label><br><input id=mm_per_pulse type=number step=0.01></div>
<div><label>start delay ms</label><br><input id=start_delay_ms type=number step=100></div>
<button onclick=saveCfg()>save</button></div></div>
<div class=card><b>Speed</b> <span style="color:var(--mut);font-size:13px">solid = run, dashed = simulation</span><canvas id=cv width=820 height=260></canvas></div>
<div class=card><b>Runs</b><table><thead><tr><th>time</th><th>gate s</th><th>car 12 m s</th><th>v max</th><th>duty / ramp</th><th>Vbat min</th></tr></thead><tbody id=runs></tbody></table></div>
</main><script>
const $=id=>document.getElementById(id);let sim=null,cfgLoaded=false;
async function post(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})});return r.json()}
async function go(){await post('/api/go',{})}
async function saveCfg(){const b={};for(const k of ['start_duty','ramp_ms','stop_m','mm_per_pulse','start_delay_ms'])b[k]=$(k).value;await post('/api/config',b)}
function f(x,d=3){return x==null||isNaN(x)?'-':(+x).toFixed(d)}
async function tick(){try{const s=await (await fetch('/api/state')).json();
$('carst').textContent=s.car_ok?('car: '+s.car.state):'car: offline';$('carst').style.background=s.car_ok?'':'var(--bad)';
$('gate').textContent=s.gate_blocked?'gate: BLOCKED':'gate: clear';$('vb').textContent='battery '+(s.car_ok?f(s.car.vbat,2)+' V':'?');
if(s.car_ok&&!cfgLoaded){for(const k in s.car.config){if($(k))$(k).value=s.car.config[k]}cfgLoaded=true}
if(s.pit.state==='error')$('carst').textContent='error: '+s.pit.error;
if(s.pit.last){$('tgate').textContent=f(s.pit.last.gate_t);$('tcar').textContent=f(s.pit.last.car&&s.pit.last.car.t12);$('vmax').textContent=f(s.pit.last.car&&s.pit.last.car.vmax,1)}
}catch(e){}}
async function runs(){const r=await (await fetch('/api/runs')).json();$('runs').innerHTML=r.map(x=>`<tr onclick="show('${x.id}')"><td>${x.id.slice(9).replace(/(..)(..)(..)/,'$1:$2:$3')}</td><td>${f(x.gate_t)}</td><td>${f(x.car&&x.car.t12)}</td><td>${f(x.car&&x.car.vmax,1)}</td><td>${x.config.start_duty} / ${x.config.ramp_ms}</td><td>${f(x.car&&x.car.vbat_min,2)}</td></tr>`).join('');if(r[0]&&!window.shown){show(r[0].id)}}
async function show(id){window.shown=id;const d=await (await fetch('/api/run/'+id)).json();draw(d.data)}
function draw(run){const c=$('cv'),g=c.getContext('2d'),W=c.width,H=c.height,css=getComputedStyle(document.body);g.clearRect(0,0,W,H);
const tm=Math.max(3,run?run.t[run.t.length-1]:0),vm=10,X=t=>40+t/tm*(W-50),Y=v=>H-25-v/vm*(H-35);
g.strokeStyle=css.getPropertyValue('--line');g.fillStyle=css.getPropertyValue('--mut');g.font='12px system-ui';
for(let v=0;v<=vm;v+=2){g.beginPath();g.moveTo(40,Y(v));g.lineTo(W-10,Y(v));g.stroke();g.fillText(v+' m/s',2,Y(v)+4)}
for(let t=0;t<=tm;t+=0.5){g.fillText(t+'s',X(t)-8,H-6)}
const line=(T,V,col,dash)=>{g.setLineDash(dash?[6,5]:[]);g.strokeStyle=col;g.lineWidth=2;g.beginPath();T.forEach((t,i)=>i?g.lineTo(X(t),Y(V[i])):g.moveTo(X(t),Y(V[i])));g.stroke();g.setLineDash([])};
if(sim&&sim.t)line(sim.t,sim.v,'#999',true);if(run)line(run.t,run.v,css.getPropertyValue('--acc'),false)}
fetch('/api/sim').then(r=>r.json()).then(j=>{sim=j;draw(null)});
setInterval(tick,500);setInterval(runs,3000);tick();runs();
</script></body></html>"""

if __name__ == "__main__":
    print(f"pit station on http://0.0.0.0:{args.port}  (car: {'MOCK' if args.mock else args.car})")
    app.run(host="0.0.0.0", port=args.port, threaded=True)
