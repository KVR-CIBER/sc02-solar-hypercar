"""Pocket -> sim bridge: reads the RadioMaster Pocket as a HID joystick (USB 'Radiomaster Pocket Joystick' or Bluetooth
'ExpressLRS Joystick') and streams its 8 channels + buttons to the browser as Server-Sent Events on :8091.
The sim (rc.js) uses this instead of the browser Gamepad API, so no browser support / learning is needed.
The radio is only opened while a browser is listening, and never exclusively, so other apps (FPV.SkyDive) keep the joystick.
Two-way: with the Pocket in "USB Serial (VCP)" (VCP port mode LUA) sc02.lua sends its channels as text lines
"C,ch1,...,ch8" (-1024..1024) and gets the sim speed back as "S<km/h>"; the page posts that speed to /speed?v=<km/h>.
HTTPS on :8092 when ~/.sc02/cert.pem + key.pem exist (self-signed for 127.0.0.1, trusted in the login keychain):
Safari blocks http://127.0.0.1 from the https GitHub Pages site, so the page tries https first.
Run: ~/Downloads/solar-olympiade/.venv/bin/python f1/web/pocket_bridge.py"""
import ctypes, hid, json, os, ssl, threading, time
import serial
from serial.tools import list_ports
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEVICES = {(0x1209, 0x4F54): ("Pocket USB", 2047.0), (0xE502, 0xBBAB): ("Pocket Bluetooth", 32767.0)}
state = {"name": None, "ch": [0.0] * 8, "btn": 0, "t": 0.0}
port = None                                             # open serial port to the Pocket (VCP), for the speed back
clients = 0                                             # open browser streams; the radio is only held while > 0
try:                                                    # macOS hidapi seizes the device by default -> other apps see nothing
    ctypes.CDLL(hid.__file__).hid_darwin_set_open_exclusive(0)
except (OSError, AttributeError):
    pass


def reader():
    while True:
        if clients == 0:
            state["name"] = None; time.sleep(0.5); continue
        dev = None
        for d in hid.enumerate():
            key = (d["vendor_id"], d["product_id"])
            if key in DEVICES and d["usage_page"] == 1 and d["usage"] in (4, 5):
                dev = (key, d["path"]); break
        if not dev:                                     # no HID radio (maybe serial): the stream goes stale by itself
            time.sleep(1.0); continue
        (key, path), (name, full) = dev, DEVICES[dev[0]]
        try:
            h = hid.device(); h.open_path(path); h.set_nonblocking(False)
            print("verbonden:", name, flush=True)
            while clients > 0:
                r = h.read(64, 1000)
                if not r:
                    continue
                # report: [id, buttons lo, buttons hi, 8x 16-bit little-endian channel values, (hat)]
                vals = [r[3 + 2 * i] | (r[4 + 2 * i] << 8) for i in range(8)]
                if name == "Pocket Bluetooth":           # ExpressLRS BLE joystick axes X,Y,Z,Rz,Rx,Ry,S1,S2 = CH1,2,5,6,3,4,7,8
                    vals = [vals[0], vals[1], vals[4], vals[5], vals[2], vals[3], vals[6], vals[7]]
                state.update(name=name, ch=[round(v / full * 2 - 1, 4) for v in vals], btn=r[1] | (r[2] << 8), t=time.time())
            h.close(); state["name"] = None
            print("losgelaten (geen browser meer)", flush=True)
        except Exception as e:
            print("verbinding weg:", e, flush=True); state["name"] = None; time.sleep(1.0)


def serial_reader():
    global port
    while True:
        p = next((c.device for c in list_ports.comports() if (c.vid, c.pid) == (0x0483, 0x5740)
                  or "edgetx" in f"{c.product} {c.manufacturer}".lower()), None) if clients > 0 else None
        if not p:
            time.sleep(1.0); continue
        try:
            s = serial.Serial(p, 115200, timeout=0.5)
            print("verbonden: Pocket serieel", p, flush=True)
            port, buf = s, b""
            while clients > 0:
                buf += s.read(s.in_waiting or 1)
                *lines, buf = buf.split(b"\n")
                for ln in lines:
                    f = ln.strip().split(b",")
                    if len(f) == 9 and f[0] == b"C":
                        state.update(name="Pocket serieel", ch=[round(int(v) / 1024, 4) for v in f[1:]], btn=0, t=time.time())
            port = None; s.close()
            print("losgelaten (geen browser meer)", flush=True)
        except (OSError, ValueError, serial.SerialException) as e:
            port = None; print("serieel weg:", e, flush=True); time.sleep(1.0)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def cors(self):                                     # any site may read it: localhost, GitHub Pages (https), lvdell
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")   # Chrome: public/LAN page -> localhost
        self.send_header("Access-Control-Allow-Local-Network", "true")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(204); self.cors(); self.end_headers()

    def do_POST(self):                                  # /speed?v=<km/h> from the sim -> the Pocket screen
        self.send_response(204); self.cors(); self.end_headers()
        try:
            v = int(float(self.path.split("v=", 1)[1]))
            if port:
                port.write(f"S{v}\n".encode())
        except (IndexError, ValueError, OSError, serial.SerialException):
            pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache")
        self.cors(); self.end_headers()
        global clients
        clients += 1
        try:
            while True:
                fresh = state["name"] and time.time() - state["t"] < 0.5
                msg = {"name": state["name"] if fresh else None, "ch": state["ch"], "btn": state["btn"]}
                self.wfile.write(f"data: {json.dumps(msg)}\n\n".encode()); self.wfile.flush()
                time.sleep(1 / 60)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            clients -= 1


threading.Thread(target=reader, daemon=True).start()
threading.Thread(target=serial_reader, daemon=True).start()
CERT = os.path.expanduser("~/.sc02/cert.pem"), os.path.expanduser("~/.sc02/key.pem")
if all(map(os.path.exists, CERT)):
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(*CERT)
    srv = ThreadingHTTPServer(("127.0.0.1", 8092), H); srv.socket = tls.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("ook https://127.0.0.1:8092 (Safari)", flush=True)
print("Pocket-brug op http://localhost:8091  (Ctrl+C om te stoppen)", flush=True)
ThreadingHTTPServer(("127.0.0.1", 8091), H).serve_forever()
