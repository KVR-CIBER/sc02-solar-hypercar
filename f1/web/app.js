// SC-02 – free-drive simulation (three.js r160). Physics in physics2.js.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { Sky } from "three/addons/objects/Sky.js";
import { createVehicle } from "./physics2.js";
import { rc, bindRcPanel } from "./rc.js";
import { createAudio } from "./audio.js";

const $ = (id) => document.getElementById(id);
const Q = new URLSearchParams(location.search);
const VIDEO = Q.has("video");
const MOBILE = matchMedia("(pointer: coarse)").matches;
if (VIDEO) document.body.classList.add("render");

// ------------------------------------------------------------------ renderer
const canvas = $("c");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance", preserveDrawingBuffer: VIDEO });
renderer.setPixelRatio(VIDEO ? 1 : Math.min(devicePixelRatio, MOBILE ? 1.5 : 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.62;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(36, 1, 0.02, 3000);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true; controls.enabled = false; controls.maxPolarAngle = Math.PI * 0.49;

// sky + sun (golden hour)
const sky = new Sky(); sky.scale.setScalar(2400); scene.add(sky);
const sunDir = new THREE.Vector3().setFromSphericalCoords(1, THREE.MathUtils.degToRad(76), THREE.MathUtils.degToRad(215));
Object.assign(sky.material.uniforms, {});
sky.material.uniforms.turbidity.value = 6; sky.material.uniforms.rayleigh.value = 1.6;
sky.material.uniforms.mieCoefficient.value = 0.004; sky.material.uniforms.mieDirectionalG.value = 0.86;
sky.material.uniforms.sunPosition.value.copy(sunDir);
const pmrem = new THREE.PMREMGenerator(renderer);
const envScene = new THREE.Scene(); const sky2 = sky.clone(); envScene.add(sky2);
scene.environment = pmrem.fromScene(envScene, 0, 0.1, 1000).texture;
scene.fog = new THREE.Fog(0xc9d3e0, 140, 900);
const sun = new THREE.DirectionalLight(0xffe2c0, 3.4);
sun.castShadow = true; sun.shadow.mapSize.set(VIDEO ? 4096 : 2048, VIDEO ? 4096 : 2048);
Object.assign(sun.shadow.camera, { left: -1.6, right: 1.6, top: 1.6, bottom: -1.6, near: 0.5, far: 30 });
sun.shadow.bias = -0.0003; sun.shadow.normalBias = 0.004;
scene.add(sun, sun.target);
scene.add(new THREE.HemisphereLight(0xcfe0ff, 0x4a3b28, 0.55));


function resize() {
  const w = VIDEO ? +(Q.get("w") || 3840) : innerWidth, h = VIDEO ? +(Q.get("h") || 2160) : innerHeight;
  renderer.setSize(w, h, !VIDEO);
  if (VIDEO) { canvas.style.width = "100vw"; canvas.style.height = "100vh"; }
  camera.aspect = w / h; camera.updateProjectionMatrix();
}
addEventListener("resize", resize);

// ------------------------------------------------------------------ textures
function tex(w, h, draw, rep, srgb = true) {
  const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c); if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8; t.wrapS = t.wrapT = THREE.RepeatWrapping; if (rep) t.repeat.set(...rep); return t;
}
function noise(g, w, h, base, amp, n = 9000, sz = 2) {
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  for (let i = 0; i < n; i++) { const v = (Math.random() - 0.5) * amp; g.fillStyle = `rgba(${v > 0 ? 255 : 0},${v > 0 ? 255 : 0},${v > 0 ? 255 : 0},${Math.abs(v)})`;
    g.fillRect(Math.random() * w, Math.random() * h, sz * Math.random() + 0.5, sz * Math.random() + 0.5); }
}
const asphaltT = tex(512, 512, (g, w, h) => { noise(g, w, h, "#3a3d42", 0.16, 60000, 1.6); }, [1, 1]);
const asphaltR = tex(256, 256, (g, w, h) => { noise(g, w, h, "#b0b0b0", 0.35, 12000, 2); }, [1, 1], false);
const grassT = tex(512, 512, (g, w, h) => {
  noise(g, w, h, "#4d6b2c", 0.12, 50000, 2);
  for (let i = 0; i < 9000; i++) { g.strokeStyle = `rgba(${90 + Math.random() * 60},${120 + Math.random() * 60},40,0.35)`; const x = Math.random() * w, y = Math.random() * h;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.random() * 2 - 1, y - 3 - Math.random() * 4); g.stroke(); }
}, [410, 410]);
const kerbT = tex(128, 16, (g, w, h) => { for (let i = 0; i < 4; i++) { g.fillStyle = i % 2 ? "#f2f2f2" : "#d01c1f"; g.fillRect(i * 32, 0, 32, h); } }, [1, 1]);
const wallT = tex(512, 64, (g, w, h) => { g.fillStyle = "#e8eaee"; g.fillRect(0, 0, w, h);
  g.fillStyle = "#b5121b"; g.fillRect(0, 10, w, 8); g.fillRect(0, h - 18, w, 8);
  g.fillStyle = "rgba(0,0,0,.18)"; for (let x = 0; x < w; x += 64) g.fillRect(x, 0, 2, h); }, [1, 1]);
const checkerT = tex(64, 64, (g) => { for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) { g.fillStyle = (i + j) % 2 ? "#111" : "#f5f5f5"; g.fillRect(i * 8, j * 8, 8, 8); } }, [1, 1]);
const PANEL_MM = [60, 110], PANEL_X0 = 54;                   // AliExpress 1 W 5 V panel, crosswise on the deck (x along the car, y across)
const solarT = (() => {
  const [PW, PH] = PANEL_MM, px = 20, W = PW * px, H = PH * px;   // 20 px per mm
  const c = document.createElement("canvas"); c.width = W; c.height = H; const g = c.getContext("2d");
  g.fillStyle = "#0e2a22"; g.fillRect(0, 0, W, H);                    // green epoxy board edge
  const bar = 6 * px, bx = (W - bar) / 2;                             // green centre bar with the solder pads
  for (const [x0, w] of [[1.4 * px, bx - 2.2 * px], [bx + bar + 0.8 * px, W - bx - bar - 2.2 * px]]) {
    const n = 8, gap = 0.6 * px, y0 = 1.4 * px, h = (H - 2.8 * px - gap * (n - 1)) / n;
    for (let i = 0; i < n; i++) {
      const y = y0 + i * (h + gap);
      const gr = g.createLinearGradient(x0, y, x0 + w, y + h);
      gr.addColorStop(0, "#14204a"); gr.addColorStop(0.5, "#0c163a"); gr.addColorStop(1, "#111c44");
      g.fillStyle = gr; g.fillRect(x0, y, w, h);
      for (let k = 0; k < 500; k++) { g.fillStyle = `rgba(${40 + Math.random() * 30},${60 + Math.random() * 40},${140 + Math.random() * 60},${Math.random() * 0.06})`;
        g.fillRect(x0 + Math.random() * w, y + Math.random() * h, 6 + Math.random() * 30, 2 + Math.random() * 8); }
      g.strokeStyle = "rgba(175,185,205,0.28)"; g.lineWidth = 0.9;            // fine fingers
      for (let fy = y + 0.4 * px; fy < y + h; fy += 0.62 * px) { g.beginPath(); g.moveTo(x0 + 1, fy); g.lineTo(x0 + w - 1, fy); g.stroke(); }
      g.fillStyle = "rgba(200,206,218,0.72)"; g.fillRect(x0 + w * 0.5 - 0.16 * px, y, 0.32 * px, h);   // busbar
    }
  }
  g.fillStyle = "#1f7a5a"; g.fillRect(bx, 0, bar, H);                  // centre bar
  g.fillStyle = "rgba(255,255,255,.08)"; g.fillRect(bx + bar * 0.15, 0, bar * 0.12, H);
  for (const yy of [H * 0.3, H * 0.62]) {                                // solder pads + / -
    g.fillStyle = "#d9b25a"; g.beginPath(); g.arc(W / 2, yy, 1.6 * px, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#b28a3a"; g.beginPath(); g.arc(W / 2, yy, 0.7 * px, 0, Math.PI * 2); g.fill();
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 16; return t;
})();
const epoxyN = (() => {                                           // orange-peel normal map for the epoxy coat
  const S = 512, c = document.createElement("canvas"); c.width = c.height = S; const g = c.getContext("2d");
  g.fillStyle = "rgb(128,128,255)"; g.fillRect(0, 0, S, S);
  for (let i = 0; i < 2500; i++) { const r = 4 + Math.random() * 10, x = Math.random() * S, y = Math.random() * S;
    const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, `rgba(${128 + (Math.random() - 0.5) * 30},${128 + (Math.random() - 0.5) * 30},255,0.5)`); gr.addColorStop(1, "rgba(128,128,255,0)");
    g.fillStyle = gr; g.fillRect(x - r, y - r, 2 * r, 2 * r); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(3, 3); return t;
})();

// ------------------------------------------------------------------ circuit
const SCENE_N0 = scene.children.length;          // everything added from here up to the car is circuit scenery
const CTRL = [[0, 0], [16, 0], [21, 1], [23.5, 4.5], [22, 8], [18, 9.2], [13, 8.4], [9.5, 10.3], [8.5, 14], [11, 18], [17, 19.5], [24, 19],
  [30.5, 15], [33.5, 8], [33.5, 0], [30, -6], [23, -9.5], [13, -10.5], [4, -10.2], [-2.5, -8.6], [-6.6, -5], [-6.8, -1.6], [-4, 0]];
// world: x east, z south; track point (px, py) -> (px, 0, -py)
const curve = new THREE.CatmullRomCurve3(CTRL.map(([x, y]) => new THREE.Vector3(x, 0, -y)), true, "centripetal");
const NS = 2400;
const TP = curve.getSpacedPoints(NS);  TP.pop();
const TLEN = curve.getLength();
const TT = [], TN = [], TK = [];
for (let i = 0; i < NS; i++) {
  const a = TP[(i - 1 + NS) % NS], b = TP[(i + 1) % NS];
  const t = b.clone().sub(a).normalize(); TT.push(t); TN.push(new THREE.Vector3(-t.z, 0, t.x));
}
const TK0 = [];
for (let i = 0; i < NS; i++) {
  const t0 = TT[(i - 6 + NS) % NS], t1 = TT[(i + 6) % NS];
  TK0.push((t0.x * t1.z - t0.z * t1.x) / (12 * TLEN / NS));          // signed curvature
}
for (let i = 0; i < NS; i++) { let a = 0; for (let j = -10; j <= 10; j++) a += TK0[(i + j + NS) % NS]; TK.push(a / 21); }
const HALF = 0.65, WALL = 2.35;

function ribbon(off0, off1, y, mat, uScale = 1, filter = null, vRepeat = 1) {
  const pos = [], uv = [], idx = [];
  let s = 0, n = 0;
  for (let i = 0; i <= NS; i++) {
    const k = i % NS;
    if (i > 0) s += TP[k].distanceTo(TP[(k - 1 + NS) % NS]);
    const p = TP[k], nn = TN[k];
    const o0 = typeof off0 === "function" ? off0(k) : off0, o1 = typeof off1 === "function" ? off1(k) : off1;
    pos.push(p.x + nn.x * o0, y, p.z + nn.z * o0, p.x + nn.x * o1, y, p.z + nn.z * o1);
    uv.push(s * uScale, 0, s * uScale, vRepeat);
    if (i > 0 && (!filter || filter(k))) { const a = (i - 1) * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  const m = new THREE.Mesh(g, mat); m.receiveShadow = true; scene.add(m); return m;
}
const ground = new THREE.Mesh(new THREE.PlaneGeometry(3200, 3200), new THREE.MeshStandardMaterial({ map: grassT, roughness: 0.95 }));
ground.rotation.x = -Math.PI / 2; ground.position.set(14, -0.002, -5); ground.receiveShadow = true; scene.add(ground);
const asphalt = new THREE.MeshStandardMaterial({ map: asphaltT, roughnessMap: asphaltR, roughness: 0.9, metalness: 0 });
asphaltT.repeat.set(1, 1);
ribbon(-HALF - 0.12, HALF + 0.12, 0.001, asphalt, 0.8, null, 1.1);
const lineM = new THREE.MeshStandardMaterial({ color: 0xf2f2f2, roughness: 0.6 });
ribbon(-HALF + 0.02, -HALF + 0.05, 0.0018, lineM); ribbon(HALF - 0.05, HALF - 0.02, 0.0018, lineM);
const kerbM = new THREE.MeshStandardMaterial({ map: kerbT, roughness: 0.55 });
const kerbOn = (k) => Math.abs(TK[k]) > 0.22 || Math.abs(TK[(k + 25) % NS]) > 0.22 || Math.abs(TK[(k - 25 + NS) % NS]) > 0.22;
ribbon(HALF - 0.01, HALF + 0.16, 0.003, kerbM, 2.4, kerbOn);
ribbon(-HALF - 0.16, -HALF + 0.01, 0.003, kerbM, 2.4, kerbOn);
// walls (both sides, a gap at the hairpin where both walls meet)
function wall(off) {
  const pos = [], uv = [], idx = []; let s = 0;
  for (let i = 0; i <= NS; i++) {
    const k = i % NS; if (i > 0) s += TP[k].distanceTo(TP[(k - 1 + NS) % NS]);
    const p = TP[k], n = TN[k];
    const x = p.x + n.x * off, z = p.z + n.z * off;
    pos.push(x, 0, z, x, 0.22, z); uv.push(s * 0.5, 0, s * 0.5, 1);
    if (i > 0) { const a = (i - 1) * 2; idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ map: wallT, roughness: 0.7, side: THREE.DoubleSide }));
  m.castShadow = m.receiveShadow = true; scene.add(m);
}
wall(-WALL); wall(WALL);
// start/finish line + grid boxes + 12 m sprint marks
const sf = new THREE.Mesh(new THREE.PlaneGeometry(0.12, HALF * 2), new THREE.MeshStandardMaterial({ map: checkerT, roughness: 0.6 }));
checkerT.repeat.set(1, 10);
sf.rotation.x = -Math.PI / 2; sf.position.set(0.0, 0.0025, 0); scene.add(sf);
for (const x of [12]) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(0.04, HALF * 2), lineM); m.rotation.x = -Math.PI / 2; m.position.set(x, 0.0025, 0); scene.add(m);
}
// scenery: grandstand, light towers, trees, hills
function grandstand(x0, x1, z) {
  const g = new THREE.Group();
  const conc = new THREE.MeshStandardMaterial({ color: 0x9aa0a8, roughness: 0.85 });
  const seat = tex(64, 64, (c) => { for (let i = 0; i < 400; i++) { c.fillStyle = ["#1f3b8f", "#c8102e", "#e5e7eb", "#1f3b8f"][i % 4]; c.fillRect((i % 20) * 3.2, Math.floor(i / 20) * 3.2, 2.6, 2.6); } }, [12, 1]);
  for (let r = 0; r < 7; r++) {
    const step = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, 0.35, 0.7), r % 2 ? conc : new THREE.MeshStandardMaterial({ map: seat, roughness: 0.8 }));
    step.position.set((x0 + x1) / 2, 0.18 + r * 0.35, z + r * 0.7); step.castShadow = step.receiveShadow = true; g.add(step);
  }
  const roof = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0 + 2, 0.12, 6.5), new THREE.MeshStandardMaterial({ color: 0xe6e8eb, roughness: 0.4, metalness: 0.4 }));
  roof.position.set((x0 + x1) / 2, 4.6, z + 2.5); roof.castShadow = true; g.add(roof);
  for (let x = x0; x <= x1; x += 6) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 4.6, 8), conc); p.position.set(x, 2.3, z + 5); g.add(p); }
  scene.add(g);
}
grandstand(-2, 18, 4.2);
const trunkM = new THREE.MeshStandardMaterial({ color: 0x3b2a1c, roughness: 1 });
const leafM = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.92, flatShading: true });
const rnd = (() => { let s = 7; return () => (s = (s * 16807) % 2147483647) / 2147483647; })();
// layered pine: 4 stacked, slightly jittered cones merged into one geometry
function pineGeo() {
  const parts = [];
  for (let k = 0; k < 4; k++) {
    const g = new THREE.ConeGeometry(1.15 - k * 0.22, 1.7 - k * 0.15, 9, 1);
    g.translate(0, 1.5 + k * 0.82, 0);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { if (p.getY(i) < 1.5 + k * 0.82) { p.setX(i, p.getX(i) * (0.9 + Math.random() * 0.25)); p.setZ(i, p.getZ(i) * (0.9 + Math.random() * 0.25)); } }
    parts.push(g.toNonIndexed());
  }
  const merged = new THREE.BufferGeometry();
  const pos = []; parts.forEach((g) => pos.push(...g.attributes.position.array));
  merged.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3)); merged.computeVertexNormals();
  return merged;
}
const NT = 260;
const trees = new THREE.InstancedMesh(pineGeo(), leafM, NT);
const trunks = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.1, 0.16, 1.6, 6).translate(0, 0.8, 0), trunkM, NT);
const M4 = new THREE.Matrix4(), col = new THREE.Color();
for (let i = 0; i < NT; i++) {
  let x, z, ok = false;
  for (let t = 0; t < 40 && !ok; t++) {
    x = -55 + rnd() * 140; z = -70 + rnd() * 100;
    ok = TP.every((p, k) => k % 12 || p.distanceToSquared(new THREE.Vector3(x, 0, z)) > 42) && !(x > -4 && x < 20 && z > 2 && z < 12);
  }
  const s = 0.75 + rnd() * 0.9, q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), rnd() * 6.28);
  M4.compose(new THREE.Vector3(x, 0, z), q, new THREE.Vector3(s, s * (0.9 + rnd() * 0.35), s)); trees.setMatrixAt(i, M4); trunks.setMatrixAt(i, M4);
  col.setHSL(0.31 + rnd() * 0.06, 0.30 + rnd() * 0.12, 0.10 + rnd() * 0.06); trees.setColorAt(i, col);
}
trees.castShadow = true; scene.add(trees, trunks);
for (let i = 0; i < 9; i++) {
  const h = new THREE.Mesh(new THREE.SphereGeometry(60 + rnd() * 40, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0x5b7346, roughness: 1 }));
  const a = (i / 9) * Math.PI * 2; h.scale.y = 0.18 + rnd() * 0.12; h.position.set(14 + Math.cos(a) * 330, -2, -5 + Math.sin(a) * 330); h.userData.shared = true; scene.add(h);
}
ground.userData.shared = true;
const circuitG = new THREE.Group();
for (const o of scene.children.slice(SCENE_N0)) if (!o.userData.shared) circuitG.add(o);
scene.add(circuitG);

// ------------------------------------------------------------------ endless straight
// Periodic scenery (period SL) + the car is shifted back by SL when it gets too far,
// so it never leaves the high-precision zone around the origin and the shift is invisible.
const SL = 200, SPAN = 1300;
const straightG = new THREE.Group(); straightG.visible = false; scene.add(straightG);
function strip(z0, z1, y, mat, uPerM, vRep = 1) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute([-SPAN, y, z0, SPAN, y, z0, -SPAN, y, z1, SPAN, y, z1], 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute([-SPAN * uPerM, 0, SPAN * uPerM, 0, -SPAN * uPerM, vRep, SPAN * uPerM, vRep], 2));
  g.setIndex([0, 2, 1, 1, 2, 3]); g.computeVertexNormals();
  const m = new THREE.Mesh(g, mat); m.receiveShadow = true; straightG.add(m); return m;
}
strip(-HALF - 0.12, HALF + 0.12, 0.001, asphalt, 0.8, 1.1);
strip(-HALF + 0.02, -HALF + 0.05, 0.0018, lineM, 1); strip(HALF - 0.05, HALF - 0.02, 0.0018, lineM, 1);
{ // centre dashes (2 m period) – they give the sense of speed
  const n = Math.floor((2 * SPAN) / 2), dash = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.5, 0.025).rotateX(-Math.PI / 2), lineM, n);
  for (let i = 0; i < n; i++) { M4.makeTranslation(-SPAN + i * 2 + 1, 0.0018, 0); dash.setMatrixAt(i, M4); }
  dash.receiveShadow = true; straightG.add(dash);
}
for (const z of [-WALL, WALL]) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute([-SPAN, 0, z, SPAN, 0, z, -SPAN, 0.22, z, SPAN, 0.22, z], 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute([-SPAN * 0.5, 0, SPAN * 0.5, 0, -SPAN * 0.5, 1, SPAN * 0.5, 1], 2));
  g.setIndex([0, 1, 2, 1, 3, 2]); g.computeVertexNormals();
  const w = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ map: wallT, roughness: 0.7, side: THREE.DoubleSide })); w.castShadow = w.receiveShadow = true; straightG.add(w);
}
{ // 10 m boards on both walls + a chequered line every SL metres
  const boardM = new THREE.MeshStandardMaterial({ color: 0x15171c, roughness: 0.5 }), nb = Math.floor((2 * SPAN) / 10);
  const boards = new THREE.InstancedMesh(new THREE.BoxGeometry(0.03, 0.16, 0.012), boardM, nb * 2);
  for (let i = 0; i < nb; i++) for (const [j, z] of [[0, -WALL + 0.01], [1, WALL - 0.01]]) { M4.makeTranslation(-SPAN + i * 10, 0.3, z); boards.setMatrixAt(i * 2 + j, M4); }
  straightG.add(boards);
  for (let x = -SPAN + (SPAN % SL); x <= SPAN; x += SL) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.12, HALF * 2), new THREE.MeshStandardMaterial({ map: checkerT, roughness: 0.6 }));
    m.rotation.x = -Math.PI / 2; m.position.set(x, 0.0025, 0); straightG.add(m);
  }
}
{ // tree rows, periodic in SL
  const per = 46, copies = Math.ceil(SPAN / SL) * 2 + 1, n = per * copies, base = [];
  for (let i = 0; i < per; i++) { const side = i % 2 ? 1 : -1; base.push([rnd() * SL, side * (4 + rnd() * 34), 0.75 + rnd() * 0.9, rnd() * 6.28, 0.9 + rnd() * 0.35, rnd(), rnd(), rnd()]); }
  const st = new THREE.InstancedMesh(trees.geometry, leafM, n), sk = new THREE.InstancedMesh(trunks.geometry, trunkM, n);
  let k = 0;
  for (let c = -(copies - 1) / 2; c <= (copies - 1) / 2; c++) for (const [x, z, sc, rot, sy, h1, h2, h3] of base) {
    M4.compose(new THREE.Vector3(x + c * SL, 0, z), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), rot), new THREE.Vector3(sc, sc * sy, sc));
    st.setMatrixAt(k, M4); sk.setMatrixAt(k, M4); col.setHSL(0.31 + h1 * 0.06, 0.30 + h2 * 0.12, 0.10 + h3 * 0.06); st.setColorAt(k, col); k++;
  }
  st.castShadow = true; straightG.add(st, sk);
}
let TRACK = "circuit";
try { TRACK = Q.get("track") === "recht" ? "recht" : localStorage.getItem("sc02.track") || "circuit"; } catch { }
function applyTrack() {
  circuitG.visible = TRACK === "circuit"; straightG.visible = TRACK === "recht";
  $("map").style.display = TRACK === "recht" ? "none" : "";
  $("lb").textContent = "";
}

// ------------------------------------------------------------------ car
let info = null, car = null, ghostFX = null;
const paintMat = new THREE.MeshPhysicalMaterial({ color: 0xb10818, roughness: 0.34, metalness: 0.45, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.15 });
// livery: carbon underside band + centre stripe, done in the shader from object-space position (no UVs needed)
paintMat.onBeforeCompile = (sh) => {
  sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vObj;").replace("#include <begin_vertex>", "#include <begin_vertex>\nvObj = position;");
  sh.fragmentShader = sh.fragmentShader.replace("#include <common>", "#include <common>\nvarying vec3 vObj;").replace("#include <color_fragment>", `#include <color_fragment>
    float band = smoothstep(14.5, 14.0, vObj.z);                                   // carbon lower band
    float stripe = smoothstep(9.0, 8.4, abs(vObj.y)) * step(32.0, vObj.z) * (1.0 - step(abs(vObj.y), 1.2));
    vec3 carbon = vec3(0.025) + 0.012 * step(0.5, fract((vObj.x + vObj.y) * 0.5));
    diffuseColor.rgb = mix(diffuseColor.rgb, carbon, band);
    diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.92), stripe * 0.9);
    float seam = 1.0 - smoothstep(0.18, 0.42, abs(vObj.x - 150.0));            // panel shut line between the two body halves
    diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.01), seam * 0.92);`);
};
const M = {
  body: paintMat,
  canopy: (() => {
    const m = new THREE.MeshPhysicalMaterial({ color: 0x05070b, roughness: 0.03, metalness: 0.25, clearcoat: 1, clearcoatRoughness: 0.01, envMapIntensity: 1.8 });
    m.onBeforeCompile = (sh) => {                                   // black rubber seal along the canopy base
      sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vO;").replace("#include <begin_vertex>", "#include <begin_vertex>\nvO = position;");
      sh.fragmentShader = sh.fragmentShader.replace("#include <common>", "#include <common>\nvarying vec3 vO;")
        .replace("#include <roughnessmap_fragment>", "#include <roughnessmap_fragment>\nroughnessFactor = mix(roughnessFactor, 0.8, 1.0 - smoothstep(42.4, 43.4, vO.z));");
    };
    return m;
  })(),
  carbon: new THREE.MeshPhysicalMaterial({ color: 0x08090b, roughness: 0.45, metalness: 0.2, clearcoat: 0.5, clearcoatRoughness: 0.35, envMapIntensity: 0.5 }),
  floor: (() => {
    const m = new THREE.MeshPhysicalMaterial({ color: 0x050506, roughness: 0.04, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.02, envMapIntensity: 0.9 });
    m.onBeforeCompile = (sh) => {
      sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vON;").replace("#include <begin_vertex>", "#include <begin_vertex>\nvON = normal;");
      sh.fragmentShader = sh.fragmentShader.replace("#include <common>", "#include <common>\nvarying vec3 vON;")
        .replace("#include <color_fragment>", "#include <color_fragment>\nfloat edge = 1.0 - smoothstep(0.3, 0.6, abs(vON.z));\ndiffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.055, 0.058, 0.062), edge);")
        .replace("#include <roughnessmap_fragment>", "#include <roughnessmap_fragment>\nroughnessFactor = mix(roughnessFactor, 0.75, 1.0 - smoothstep(0.3, 0.6, abs(vON.z)));");
    };
    return m;
  })(),
  splitterM: new THREE.MeshPhysicalMaterial({ color: 0x0a0b0d, roughness: 0.38, metalness: 0.15, clearcoat: 0.6, clearcoatRoughness: 0.3, envMapIntensity: 0.6 }),
  tyre: new THREE.MeshPhysicalMaterial({ color: 0x141517, roughness: 0.72, metalness: 0, sheen: 0.4, sheenRoughness: 0.6, sheenColor: new THREE.Color(0x3a3d42) }),
  rim: new THREE.MeshPhysicalMaterial({ color: 0x34373d, roughness: 0.28, metalness: 0.95, clearcoat: 0.8, clearcoatRoughness: 0.08 }),
  panel: new THREE.MeshPhysicalMaterial({ map: solarT, roughness: 0.42, metalness: 0.1, clearcoat: 1, clearcoatRoughness: 0.06,
    clearcoatNormalMap: epoxyN, clearcoatNormalScale: new THREE.Vector2(0.25, 0.25), envMapIntensity: 0.8 }),
  inner: new THREE.MeshStandardMaterial({ color: 0x3a3d44, roughness: 0.6 }),
  led: new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xe8f4ff, emissiveIntensity: 3.2 }),
  ledR: new THREE.MeshStandardMaterial({ color: 0xff2030, emissive: 0xff1020, emissiveIntensity: 3.0 }),
};
function flatten(root) {
  const out = {};
  root.updateMatrixWorld(true);
  const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
  root.traverse((o) => {
    if (!o.isMesh) return;
    const g = o.geometry.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld));
    out[o.name || o.parent.name] = g;
  });
  return out;
}
function smooth(g, deg = 40) { g = g.index ? g : g; g.deleteAttribute("normal"); return toCreasedNormals(g, THREE.MathUtils.degToRad(deg)); }
function toCreasedNormals(geometry, creaseAngle) {   // compact version of BufferGeometryUtils.toCreasedNormals
  const cos = Math.cos(creaseAngle), g = geometry.index ? geometry.toNonIndexed() : geometry, pos = g.attributes.position;
  const vn = {}, fn = [], a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), n = new THREE.Vector3();
  const key = (i) => `${Math.round(pos.getX(i) * 100)},${Math.round(pos.getY(i) * 100)},${Math.round(pos.getZ(i) * 100)}`;
  for (let i = 0; i < pos.count; i += 3) {
    a.fromBufferAttribute(pos, i); b.fromBufferAttribute(pos, i + 1); c.fromBufferAttribute(pos, i + 2);
    n.subVectors(c, b).cross(a.clone().sub(b)).normalize(); fn.push(n.clone());
    for (let j = 0; j < 3; j++) { const k = key(i + j); (vn[k] = vn[k] || []).push(fn.length - 1); }
  }
  const nrm = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const f = fn[Math.floor(i / 3)], acc = new THREE.Vector3();
    for (const j of vn[key(i)]) if (fn[j].dot(f) > cos) acc.add(fn[j]);
    acc.normalize(); nrm[i * 3] = acc.x; nrm[i * 3 + 1] = acc.y; nrm[i * 3 + 2] = acc.z;
  }
  g.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
  return g;
}
function planarUV(g, x0, x1, y0, y1) {
  const p = g.attributes.position, uv = new Float32Array(p.count * 2);
  for (let i = 0; i < p.count; i++) { uv[i * 2] = (p.getX(i) - x0) / (x1 - x0); uv[i * 2 + 1] = (p.getY(i) - y0) / (y1 - y0); }
  g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
}

function buildCar(geo) {
  const root = new THREE.Group();                 // track space: x forward, y up
  const cad = new THREE.Group(); cad.rotation.x = -Math.PI / 2; cad.scale.setScalar(0.001); root.add(cad);   // CAD mm, z up
  const meshes = {};
  const mk = (name, mat, parent = cad, crease = 35) => {
    if (!geo[name]) return null;
    const g = smooth(geo[name], crease);
    const m = new THREE.Mesh(g, mat); m.name = name; m.castShadow = true; m.receiveShadow = true;
    parent.add(m); meshes[name] = m; return m;
  };
  mk("body", M.body, cad, 40); mk("canopy", M.canopy, cad, 60);
  for (const n of ["rear_wing", "diffuser"]) mk(n, M.carbon, cad, 30);
  mk("splitter", M.splitterM, cad, 30); mk("floor", M.floor, cad, 20);
  { const m = new THREE.Mesh(new THREE.PlaneGeometry(PANEL_MM[0], PANEL_MM[1]), M.panel); m.position.set(PANEL_X0 + 0.3 + PANEL_MM[0] / 2, 0, 41.96); m.receiveShadow = true; cad.add(m); meshes.panel = m; }
  const inside = new THREE.Group(); cad.add(inside);
  for (const n of Object.keys(geo)) if (/^(rear_module|motor_clamp|front_module|battery_tray|pi_tray|esp_bridge|power_tray|clip_|battery|pi4|esp32s3|power|servo|motor_|bearing|axle_rear|tie_rod|steering_horn)/.test(n))
    mk(n, n === "pi4" ? new THREE.MeshStandardMaterial({ color: 0x1d7a3a, roughness: 0.5 }) : n === "battery" ? new THREE.MeshStandardMaterial({ color: 0x15171c, roughness: 0.4 })
      : n.endsWith("_can") ? new THREE.MeshPhysicalMaterial({ color: 0xc8cbd0, metalness: 1, roughness: 0.2 })
      : n.endsWith("_cap") ? new THREE.MeshStandardMaterial({ color: 0x0b0b0c, roughness: 0.5 })
      : n.endsWith("_term") ? new THREE.MeshStandardMaterial({ color: 0xc9a24a, metalness: 1, roughness: 0.3 })
      : n.endsWith("_shaft") ? new THREE.MeshStandardMaterial({ color: 0xd0d4da, metalness: 1, roughness: 0.15 })
      : n === "esp32s3" ? new THREE.MeshStandardMaterial({ color: 0x0f3d24 })
      : n === "servo" ? new THREE.MeshStandardMaterial({ color: 0x2850c8 }) : M.inner, inside, 30);
  // rear axle assembly
  const rearPivot = new THREE.Group(); rearPivot.position.set(0, 0, info.axle_rz); cad.add(rearPivot);
  const spinR = new THREE.Group(); rearPivot.add(spinR);
  for (const n of ["rim_RL", "tyre_RL", "rim_RR", "tyre_RR", "spur"]) {
    const m = mk(n, n.startsWith("rim") ? M.rim : n.startsWith("tyre") ? M.tyre : M.inner, spinR, n.startsWith("tyre") ? 50 : 30);
    if (m) m.position.set(0, 0, -info.axle_rz);
  }
  const pinions = [];
  for (const [n, cx] of [["pinion_F", info.cd], ["pinion_B", -info.cd]]) {
    const pv = new THREE.Group(); pv.position.set(cx, 0, info.axle_rz); inside.add(pv);
    const m = mk(n, new THREE.MeshStandardMaterial({ color: 0xc9a24a, metalness: 1, roughness: 0.3 }), pv); if (m) m.position.set(-cx, 0, -info.axle_rz);
    pinions.push(pv);
  }
  // front: steer pivot at the kingpin, spin pivot at the wheel centre
  const steer = [], spinF = [];
  for (const [side, s] of [["L", 1], ["R", -1]]) {
    const st = new THREE.Group(); st.position.set(info.wb, s * info.kingpin_y, 0); cad.add(st);
    const up = mk("front_upright_" + side, M.inner, st); if (up) up.position.set(-info.wb, -s * info.kingpin_y, 0);
    const sp = new THREE.Group(); sp.position.set(0, s * (info.track_f / 2 - info.kingpin_y), info.axle_fz); st.add(sp);
    for (const n of ["rim_F" + side, "tyre_F" + side]) {
      const m = mk(n, n.startsWith("rim") ? M.rim : M.tyre, sp, n.startsWith("tyre") ? 50 : 30);
      if (m) m.position.set(-info.wb, -s * info.track_f / 2, -info.axle_fz);
    }
    steer.push(st); spinF.push(sp);
  }
  // light signature: LED bars front + rear (bloom)
  const ledF = new THREE.Mesh(new THREE.BoxGeometry(1.2, 24, 1.3), M.led);
  for (const s of [1, -1]) { const l = ledF.clone(); l.position.set(323.6, s * 27, 12.6); l.rotation.z = -s * 0.12; cad.add(l); }
  const ledR = new THREE.Mesh(new THREE.BoxGeometry(1.4, 112, 2.2), M.ledR); ledR.position.set(-52.5, 0, 27); cad.add(ledR);
  const glowT = tex(64, 64, (g) => { const r = g.createRadialGradient(32, 32, 0, 32, 32, 32); r.addColorStop(0, "rgba(255,255,255,1)"); r.addColorStop(0.25, "rgba(255,255,255,.35)"); r.addColorStop(1, "rgba(255,255,255,0)"); g.fillStyle = r; g.fillRect(0, 0, 64, 64); });
  const glow = (x, y, z, col, sx, sy) => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowT, color: col, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0.55 }));
    sp.position.set(x, y, z); sp.scale.set(sx, sy, 1); cad.add(sp); };
  for (const s of [1, -1]) for (let k = -1; k <= 1; k++) glow(326, s * (27 + k * 8), 12.6, 0xdff0ff, 14, 10);
  for (let k = -2; k <= 2; k++) glow(-54, k * 22, 27, 0xff2030, 22, 16);
  const csT = tex(128, 128, (g) => { const r = g.createRadialGradient(64, 64, 4, 64, 64, 64); r.addColorStop(0, "rgba(0,0,0,0.75)"); r.addColorStop(0.55, "rgba(0,0,0,0.35)"); r.addColorStop(1, "rgba(0,0,0,0)"); g.fillStyle = r; g.fillRect(0, 0, 128, 128); });
  const cs = new THREE.Mesh(new THREE.PlaneGeometry(0.46, 0.24), new THREE.MeshBasicMaterial({ map: csT, transparent: true, depthWrite: false, opacity: 0.85 }));
  cs.rotation.x = -Math.PI / 2; cs.position.set(0.135, 0.0012, 0); cs.renderOrder = 1; root.add(cs);
  root.userData = { cad, meshes, inside, spinR, pinions, steer, spinF };
  inside.visible = false;
  scene.add(root);
  return root;
}

// ------------------------------------------------------------------ vehicle + input
let veh = null;
const cfg = { battery: "lipo3s", vMotorMax: 4.8, tc: true };
function makeVeh() {
  veh = createVehicle({ ...cfg });
  veh.reset(-0.25, 0, 0);
}
const keys = {};
addEventListener("keydown", (e) => { keys[e.code] = true; if (e.code === "KeyC") nextCam(); if (e.code === "KeyR") resetCar(); if (e.code === "Space") e.preventDefault(); lastInput = performance.now(); });
addEventListener("keyup", (e) => { keys[e.code] = false; });
let rcRev = false, boostAsk = false, touchSteer = 0, touchGas = 0, touchBrake = 0, lastInput = -1e9, steerSm = 0, lastDt = 0.016;
function bindTouch() {
  const ts = $("tsteer"), knob = ts.querySelector("i");
  const st = (e) => { const r = ts.getBoundingClientRect(); const t = [...e.touches].find((t) => t.clientX < r.right + 40) || e.touches[0]; if (!t) return;
    touchSteer = Math.max(-1, Math.min(1, ((t.clientX - r.left) / r.width) * 2 - 1)); knob.style.left = ((touchSteer + 1) / 2) * 100 + "%"; lastInput = performance.now(); e.preventDefault(); };
  ts.addEventListener("touchstart", st, { passive: false }); ts.addEventListener("touchmove", st, { passive: false });
  ts.addEventListener("touchend", () => { touchSteer = 0; knob.style.left = "50%"; });
  const gz = (el, set) => { el.addEventListener("touchstart", (e) => { set(1); lastInput = performance.now(); e.preventDefault(); }, { passive: false }); el.addEventListener("touchend", () => set(0)); };
  gz($("tgas"), (v) => (touchGas = v)); gz($("tbrake"), (v) => (touchBrake = v));
}
bindTouch();
// control-link latency, as if the controller drove the real car: BT pad → Pi 4 (python) → UART → ESP32-S3,
// or the phone over the hotspot (wifi + browser + websocket). [base ms, jitter ms] – estimates, not measured yet.
const LAGS = { "0": [0, 0], bt: [35, 8], gsm: [120, 40] };
let lagMode = "0", lagLast = 0, lagHeld = { throttle: 0, brake: 0, steer: 0 };
try { lagMode = localStorage.getItem("sc02.lag") || "0"; if (!LAGS[lagMode]) lagMode = "0"; } catch { }
const lagQ = [];
function lagSend(inp, now) {                            // controller side: one packet per frame
  const [base, jit] = LAGS[lagMode];
  const arr = Math.max(lagLast, now + base + (Math.random() * 2 - 1) * jit);   // packets arrive in order
  lagLast = arr; lagQ.push({ arr, inp: { ...inp } });
}
function lagAt(t) {                                      // car side: what the ESP has received at wall time t (ms)
  while (lagQ.length && lagQ[0].arr <= t) lagHeld = lagQ.shift().inp;
  return lagHeld;
}
function readInput() {
  let thr = 0, brk = 0, steer = 0, boost = !!(keys.ShiftLeft || keys.ShiftRight);
  if (keys.KeyW || keys.ArrowUp) thr = 1;
  if (keys.KeyS || keys.ArrowDown) { if (veh.s.vx > 0.4) brk = 1; else thr = -0.6; }
  if (keys.KeyA || keys.ArrowLeft) steer += 1;
  if (keys.KeyD || keys.ArrowRight) steer -= 1;
  if (keys.Space) brk = 1;
  const r = rc.read();                                   // RadioMaster Pocket as USB joystick (learned mapping)
  if (r) {
    if (Math.abs(r.steer) > 0.02 || Math.abs(r.thr) > 0.03 || r.boost) lastInput = performance.now();
    // gas stick: forward = gas (backwards when the reverse switch is on, max 60 %), back = brake to a standstill
    if (r.thr > 0) thr = r.rev ? Math.min(thr, -0.6 * r.thr) : Math.max(thr, r.thr);
    else if (r.thr < 0) brk = Math.max(brk, -r.thr);
    rcRev = r.rev;
    steer += r.steer; boost = boost || r.boost;
  }
  for (const gp of navigator.getGamepads ? navigator.getGamepads() : []) {
    if (!gp || (rc.map && gp.id === rc.map.id)) continue;
    if (gp.buttons[5]?.pressed) boost = true;          // RB = boost on an Xbox-style pad
    const rt = gp.buttons[7]?.value || 0, lt = gp.buttons[6]?.value || 0, sx = Math.abs(gp.axes[0]) > 0.08 ? gp.axes[0] : 0;
    if (rt > 0.02 || lt > 0.02 || sx) lastInput = performance.now();
    thr = Math.max(thr, rt);
    if (lt > 0.02) { if (veh.s.vx > 0.4) brk = Math.max(brk, lt); else thr = -0.6 * lt; }
    steer -= sx * Math.min(1, Math.abs(sx) * 1.2);
    if (gp.buttons[3]?.pressed && !gp._y) nextCam(); gp._y = gp.buttons[3]?.pressed;
    if (gp.buttons[0]?.pressed && !gp._a) resetCar(); gp._a = gp.buttons[0]?.pressed;
  }
  if (MOBILE) { thr = Math.max(thr, touchGas); if (touchBrake) { if (veh.s.vx > 0.4) brk = 1; else thr = -0.6; } steer -= touchSteer; }
  if (brk > 0.05) thr = 0;                              // brake always wins over gas (W + space used to keep accelerating)
  // speed-sensitive steering (same limiter as the ESP firmware) + smoothing for digital keys
  const v = Math.abs(veh.s.vx), lim = Math.max(0.22, Math.min(1, 2.2 / (v + 0.6)));
  steerSm += (Math.max(-1, Math.min(1, steer)) * lim - steerSm) * Math.min(1, lastDt * 9);
  boostAsk = boost;
  return { throttle: thr, brake: brk, steer: steerSm, boost };
}

// autopilot (demo when nobody drives + used for the video)
function nearestIdx(x, z, hint = -1) {
  let best = 0, bd = 1e9;
  const from = hint < 0 ? 0 : hint - 80, to = hint < 0 ? NS : hint + 80;
  for (let i = from; i < to; i++) { const k = (i + NS) % NS; const d = (TP[k].x - x) ** 2 + (TP[k].z - z) ** 2; if (d < bd) { bd = d; best = k; } }
  return best;
}
let apIdx = 0;
function autopilot() {
  if (TRACK === "recht") { const s = veh.s, want = Math.max(-0.4, Math.min(0.4, -0.5 * s.y));
    return { throttle: 1, brake: 0, steer: Math.max(-1, Math.min(1, (want - Math.atan2(Math.sin(s.psi), Math.cos(s.psi))) * 3)) }; }
  const s = veh.s, wx = s.x, wz = -s.y;
  apIdx = nearestIdx(wx, wz, apIdx);
  const look = Math.round((0.45 + 0.16 * Math.abs(s.vx)) / (TLEN / NS));
  const tgt = TP[(apIdx + look) % NS];
  const dx = tgt.x - wx, dz = tgt.z - wz;
  const ang = Math.atan2(-dz, dx) - s.psi;
  const a = Math.atan2(Math.sin(ang), Math.cos(ang));
  const steer = Math.max(-1, Math.min(1, (Math.atan2(2 * 0.23 * Math.sin(a), Math.hypot(dx, dz)) / veh.c.steerMax) * 1.25));
  let kmax = 0; for (let j = 10; j < 260; j += 10) kmax = Math.max(kmax, Math.abs(TK[(apIdx + j) % NS]) / (1 + j / 260));
  const vt = Math.min(10.5, Math.sqrt((0.86 * 9.81) / Math.max(kmax, 0.02)));
  const e = vt - s.vx;
  return { throttle: Math.max(-1, Math.min(1, e * 0.9 + 0.25)), brake: e < -0.8 ? Math.min(1, -e * 0.6) : 0, steer };
}

// ------------------------------------------------------------------ walls + laps
let lapStart = 0, best = null, lastIdx = 0, lapValid = false;
let odoOff = 0, sprint = null, sprintBest = null;
function shiftWorld(d) {                                  // move car + camera + smoke by d metres along x
  veh.s.x += d; odoOff -= d; camera.position.x += d; controls.target.x += d;
  for (const P of puffs) P.sp.position.x += d;
}
function collideStraight() {
  const s = veh.s, lim = WALL - 0.11;
  if (Math.abs(s.y) > lim) {
    const sgn = Math.sign(s.y); s.y = sgn * lim;
    const cs = Math.cos(s.psi), sn = Math.sin(s.psi);
    let vwx = s.vx * cs - s.vy * sn, vwy = s.vx * sn + s.vy * cs;
    if (vwy * sgn > 0) { vwy = -0.4 * vwy; vwx *= 0.75; s.vx = vwx * cs + vwy * sn; s.vy = -vwx * sn + vwy * cs; s.r *= 0.5; }
  }
  if (s.x > SL / 2) shiftWorld(-SL); else if (s.x < -SL / 2) shiftWorld(SL);
  // 12 m sprint from standstill (same distance as the Challenger rule)
  const odo = s.x + odoOff;
  if (s.speed < 0.03) sprint = { t0: null };
  else if (sprint && sprint.t0 === null) sprint = { t0: s.t, x0: odo };
  if (sprint && sprint.t0 !== null && odo - sprint.x0 >= 12) { const t = s.t - sprint.t0; sprintBest = sprintBest == null ? t : Math.min(sprintBest, t); $("lb").textContent = `12 m · ${t.toFixed(2)} s · best ${sprintBest.toFixed(2)} s`; sprint = null; }
}
function collide() {
  if (TRACK === "recht") return collideStraight();
  const s = veh.s, wx = s.x, wz = -s.y;
  const k = nearestIdx(wx, wz, lastIdx);
  const p = TP[k], n = TN[k];
  const off = (wx - p.x) * n.x + (wz - p.z) * n.z;
  const lim = WALL - 0.11;
  if (Math.abs(off) > lim) {
    const sgn = Math.sign(off), push = Math.abs(off) - lim;
    s.x -= n.x * sgn * push; s.y += n.z * sgn * push;
    // reflect velocity component into the wall
    const cs = Math.cos(s.psi), sn = Math.sin(s.psi);
    const vwx = s.vx * cs - s.vy * sn, vwz = -(s.vx * sn + s.vy * cs);
    const vn = vwx * n.x * sgn + vwz * n.z * sgn;
    if (vn > 0) {
      const nx = vwx - 1.4 * vn * n.x * sgn, nz = vwz - 1.4 * vn * n.z * sgn;
      const vxW = nx * 0.75, vyW = -nz * 0.75;
      s.vx = vxW * cs + vyW * sn; s.vy = -vxW * sn + vyW * cs; s.r *= 0.5;
    }
  }
  // lap timing at index 0 crossing
  if (lastIdx > NS * 0.9 && k < NS * 0.1) { const t = veh.s.t - lapStart; if (lapValid) { best = best == null ? t : Math.min(best, t); $("lb").textContent = fmt(best); } lapStart = veh.s.t; lapValid = true; }
  if (lastIdx < NS * 0.1 && k > NS * 0.9) lapValid = false;
  lastIdx = k;
}
const fmt = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(3).padStart(6, "0")}`;
function resetCar() { makeVeh(); lapStart = 0; lastIdx = 0; apIdx = 0; lapValid = false; odoOff = 0; sprint = null; }

// ------------------------------------------------------------------ cameras
const CAMS = ["chase", "tv", "onboard", "orbit"];
let cam = "chase", camT = 0;
const camPos = new THREE.Vector3(), camLook = new THREE.Vector3(), tmpV = new THREE.Vector3();
function nextCam() { cam = CAMS[(CAMS.indexOf(cam) + 1) % CAMS.length]; controls.enabled = cam === "orbit"; if (cam === "orbit") controls.target.copy(car.position); }
const TVCAMS = [[-3, 0.6, 2.8], [14, 0.5, 2.6], [26, 0.9, -3], [12, 0.7, -16], [30, 0.8, -21], [36, 0.7, -6], [24, 0.6, 12], [2, 0.7, 13], [-9, 0.8, 4]];
function updateCamera(dt, snap = false) {
  const s = veh.s;
  const p = car.position, yaw = s.psi;
  const fwd = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
  if (cam === "chase") {
    const sp = Math.min(1, s.speed / 9);
    camPos.copy(p).addScaledVector(fwd, -(0.38 + sp * 0.12)).add(new THREE.Vector3(0, 0.105 + sp * 0.015, 0));
    camLook.copy(p).addScaledVector(fwd, 0.5).add(new THREE.Vector3(0, 0.03, 0));
    if (snap) camera.position.copy(camPos); else camera.position.lerp(camPos, 1 - Math.exp(-dt * 7));
    camera.lookAt(camLook);
    camera.fov = 34 + sp * 8; camera.updateProjectionMatrix();
  } else if (cam === "onboard") {
    camPos.copy(p).addScaledVector(fwd, 0.17).add(new THREE.Vector3(0, 0.072, 0));
    camLook.copy(p).addScaledVector(fwd, 2.5).add(new THREE.Vector3(0, 0.03, 0));
    camera.position.copy(camPos); camera.lookAt(camLook); camera.fov = 58; camera.updateProjectionMatrix();
  } else if (cam === "tv" && TRACK === "recht") {
    const cx = Math.round((p.x + 5) / 12) * 12;
    camera.position.set(cx, 0.5, 1.9); camera.lookAt(p.x, 0.05, p.z);
    camera.fov = THREE.MathUtils.clamp(9 * Math.hypot(cx - p.x, 1.9 - p.z) / 4, 6, 40); camera.updateProjectionMatrix();
  } else if (cam === "tv") {
    let bi = 0, bd = 1e9; TVCAMS.forEach((c, i) => { const d = (c[0] - p.x) ** 2 + (c[2] - p.z) ** 2; if (d < bd) { bd = d; bi = i; } });
    camera.position.set(...TVCAMS[bi]); camera.lookAt(p.x, 0.05, p.z);
    camera.fov = THREE.MathUtils.clamp(9 * Math.sqrt(bd) / 4, 6, 40); camera.updateProjectionMatrix();
  } else { controls.target.lerp(p, 1 - Math.exp(-dt * 4)); controls.update(); }
}

// ------------------------------------------------------------------ smoke
const smokeT = tex(64, 64, (g) => { const r = g.createRadialGradient(32, 32, 0, 32, 32, 32); r.addColorStop(0, "rgba(235,235,235,.8)"); r.addColorStop(1, "rgba(235,235,235,0)"); g.fillStyle = r; g.fillRect(0, 0, 64, 64); });
const puffs = []; for (let i = 0; i < 180; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: smokeT, transparent: true, depthWrite: false, opacity: 0 })); sp.visible = false; scene.add(sp); puffs.push({ sp, life: 0, v: new THREE.Vector3() }); }
let pi = 0;
function smoke(dt) {
  const s = veh.s, slip = Math.max(Math.abs(s.kappa) - 0.25, Math.abs(s.alphaR) - 0.22);
  if (slip > 0 && s.speed > 0.3) {
    const n = Math.min(4, Math.floor(slip * 120 * dt + Math.random()));
    for (let i = 0; i < n; i++) { const P = puffs[pi++ % puffs.length]; P.life = 1; P.sp.visible = true;
      const side = Math.random() < 0.5 ? 1 : -1; const yaw = s.psi;
      P.sp.position.set(car.position.x - Math.cos(yaw) * 0.01 + Math.sin(yaw) * 0.075 * side, 0.012, car.position.z + Math.sin(yaw) * 0.01 + Math.cos(yaw) * 0.075 * side);
      P.v.set((Math.random() - 0.5) * 0.3, 0.1 + Math.random() * 0.1, (Math.random() - 0.5) * 0.3); }
  }
  for (const P of puffs) { if (P.life <= 0) continue; P.life -= dt * 0.8; P.sp.position.addScaledVector(P.v, dt); const sc = 0.03 + (1 - P.life) * 0.22; P.sp.scale.set(sc, sc, sc);
    P.sp.material.opacity = Math.max(0, P.life) * 0.35; if (P.life <= 0) P.sp.visible = false; }
}

// ------------------------------------------------------------------ HUD + minimap
const mapC = $("map").getContext("2d");
let mapBox = null;
function drawMap() {
  if (TRACK === "recht") return;
  const g = mapC, W = 260;
  if (!mapBox) { let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9; TP.forEach((p) => { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); z0 = Math.min(z0, p.z); z1 = Math.max(z1, p.z); });
    const sc = (W - 30) / Math.max(x1 - x0, z1 - z0); mapBox = { x0, z0, sc, ox: (W - (x1 - x0) * sc) / 2, oz: (W - (z1 - z0) * sc) / 2 }; }
  const P = (x, z) => [mapBox.ox + (x - mapBox.x0) * mapBox.sc, mapBox.oz + (z - mapBox.z0) * mapBox.sc];
  g.clearRect(0, 0, W, W);
  g.lineJoin = "round"; g.strokeStyle = "rgba(255,255,255,0.75)"; g.lineWidth = 7; g.beginPath();
  TP.forEach((p, i) => { if (i % 8) return; const [x, y] = P(p.x, p.z); i ? g.lineTo(x, y) : g.moveTo(x, y); }); g.closePath(); g.stroke();
  g.strokeStyle = "rgba(10,12,17,0.9)"; g.lineWidth = 3.5; g.stroke();
  const [cx, cy] = P(car.position.x, car.position.z);
  g.fillStyle = "#ff2d3c"; g.beginPath(); g.arc(cx, cy, 8, 0, Math.PI * 2); g.fill(); g.strokeStyle = "#fff"; g.lineWidth = 2; g.stroke();
}
const fx = (v, d = 1) => v.toFixed(d);
function hud() {
  const s = veh.s, P = s.P;
  $("kmh").textContent = Math.round(s.speed * 3.6);
  $("vb").textContent = fx(s.Vbus, 1); $("ptot").textContent = fx(P.total, 1);
  $("soc").style.width = Math.round(s.soc * 100) + "%";
  $("soc").style.background = s.soc > 0.3 ? "#33d17a" : s.soc > 0.12 ? "#f6c344" : "#ff3b30";
  const bars = [["pm", "bm", P.motor, 30], ["pp", "bp", P.pi, 6], ["pe", "be", P.esp, 2], ["ps", "bs", P.servo, 3]];
  for (const [t, b, v, mx] of bars) { $(t).textContent = fx(v, 1); $(b).style.width = Math.min(100, (v / mx) * 100) + "%"; }
  const T = s.Tm, c = veh.c;
  $("tmp").textContent = Math.round(T) + " / " + Math.round(s.Tdrv); $("btm").style.width = Math.min(100, Math.max(0, (T - c.Tamb) / (c.Tlock - c.Tamb) * 100)) + "%";
  $("btm").style.background = T < c.Trearm ? "#33d17a" : T < c.Tlock - 6 ? "#f6c344" : "#ff3b30";
  const bx = $("boost"); bx.classList.toggle("on", s.boost); bx.classList.toggle("lock", !!s.boostLock);
  $("bstate").textContent = (rcRev ? "R · " : "") + (s.drvOff ? "DRIVER UIT" : s.boostLock === "heet" ? "MOTOR HEET" : s.boostLock === "driver" ? "DRIVER HEET" : s.boostLock === "batterij" ? "BATTERIJ" : s.boost ? "BOOST" : boostAsk ? "BOOST · geef gas" : "boost klaar");
  $("lt").textContent = TRACK === "recht" ? `${Math.round(Math.max(0, s.x + odoOff))} m` : fmt(Math.max(0, s.t - lapStart));
}

// ------------------------------------------------------------------ settings
function seg(id, cb) { $(id).addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; [...$(id).children].forEach((x) => x.classList.toggle("on", x === b)); cb(b.dataset.v); }); }
$("bset").onclick = () => $("sheet").classList.toggle("hidden");
bindRcPanel($);
const audio = createAudio();
const sndIcon = () => $("bsnd").classList.toggle("off", audio.muted);
sndIcon();
$("bsnd").onclick = () => { audio.start(); audio.setMuted(!audio.muted); sndIcon(); };
const wake = () => { if (!audio.muted) audio.start(); };       // browsers only allow sound after a click / key
addEventListener("pointerdown", wake); addEventListener("keydown", wake);
$("bcam").onclick = () => nextCam();
$("bres").onclick = () => resetCar();
function coolDown() { const s = veh.s; s.Tm = s.Tdrv = veh.c.Tamb; s.boostLock = ""; s.drvOff = false; }   // test button: motors + drivers back to air temperature
$("btemp").onclick = () => coolDown();
addEventListener("keydown", (e) => { if (e.code === "KeyT") coolDown(); });
seg("sbat", (v) => { cfg.battery = v; resetCar(); });
seg("strk", (v) => { TRACK = v; try { localStorage.setItem("sc02.track", v); } catch { } applyTrack(); if (car) { resetCar(); updateCamera(0.016, true); } });
[...$("strk").children].forEach((b) => b.classList.toggle("on", b.dataset.v === TRACK));
applyTrack();
seg("slim", (v) => { cfg.vMotorMax = +v; veh.c.vMotorMax = +v; });
seg("slag", (v) => { lagMode = v; lagQ.length = 0; try { localStorage.setItem("sc02.lag", v); } catch { } });
[...$("slag").children].forEach((b) => b.classList.toggle("on", b.dataset.v === lagMode));
seg("stc", (v) => { cfg.tc = v === "1"; veh.c.tc = cfg.tc; });
seg("sxr", (v) => { const xr = v === "1"; car.userData.inside.visible = xr; M.body.transparent = xr; M.body.opacity = xr ? 0.18 : 1; M.body.depthWrite = !xr;
  M.canopy.transparent = xr; M.canopy.opacity = xr ? 0.2 : 1; M.canopy.depthWrite = !xr;
  M.body.needsUpdate = true; M.canopy.needsUpdate = true; });
$("paint").addEventListener("click", (e) => { const i = e.target.closest("i"); if (!i) return; [...$("paint").children].forEach((x) => x.classList.toggle("on", x === i)); M.body.color.set(i.dataset.c); });

// ------------------------------------------------------------------ main loop
let last = performance.now(), demo = true, userDrove = false;
function poseCar() {
  const s = veh.s;
  car.position.set(s.x, 0, -s.y);
  car.rotation.y = s.psi;
  const u = car.userData;
  // body pitch / roll from accelerations (stiff little car: tiny angles)
  u.cad.rotation.z = THREE.MathUtils.clamp(-s.ax * 0.0009, -0.01, 0.01);
  u.cad.rotation.x = -Math.PI / 2 + THREE.MathUtils.clamp(s.ay * 0.0007, -0.012, 0.012);
  u.spinR.rotation.y = s.wheelR;
  u.pinions.forEach((p) => (p.rotation.y = -s.wheelR * veh.c.G));
  u.steer.forEach((st) => (st.rotation.z = s.delta));
  u.spinF.forEach((sp) => (sp.rotation.y = s.wheelF));
}
function step(dt) {
  lastDt = dt;
  const user = readInput();
  if (lastInput > 0) userDrove = true;                // demo autopilot only until the first input – it never takes over again
  demo = !userDrove;
  const n = Math.ceil(dt / 0.001), h = dt / n;
  if (!demo && LAGS[lagMode][0]) {                       // delayed link: packets land inside the 1 ms physics substeps
    const now = performance.now(); lagSend(user, now);
    for (let i = 0; i < n; i++) veh.step(h, lagAt(now - (dt - (i + 1) * h) * 1000));
  } else {
    lagQ.length = 0; lagHeld = user;
    const inp = demo ? autopilot() : user;
    for (let i = 0; i < n; i++) veh.step(h, inp);
  }
  collide();
}
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (!VIDEO && veh) {
    if (!window.__freeze) step(dt);
    poseCar(); smoke(dt); updateCamera(dt); hud(); drawMap(); audio.update(veh.s, veh.c, veh.s.boost);
    sun.position.copy(car.position).addScaledVector(sunDir, 12); sun.target.position.copy(car.position);
    renderer.render(scene, camera);
  }
  requestAnimationFrame(frame);
}

// ------------------------------------------------------------------ video (deterministic)
function videoSetup() {
  document.body.classList.add("clean");
  // record one AI lap at fixed dt
  makeVeh(); const rec = []; const DT = 1 / 240; $("lb").textContent = "";
  for (let i = 0; i < 240 * 40; i++) { const inp = autopilot(); for (let k = 0; k < 4; k++) veh.step(DT / 4, inp); collide(); rec.push({ ...veh.s, P: { ...veh.s.P } }); }
  $("lb").textContent = "";
  const FPS = +(Q.get("fps") || 60), DUR = +(Q.get("dur") || 30);
  const sample = (t) => rec[Math.max(0, Math.min(rec.length - 1, Math.round(t * 240)))];
  window.__video = {
    fps: FPS, frames: Math.round(FPS * DUR),
    frame(i) {
      const T = i / FPS;
      // shots: 0-6 showroom orbit at standstill, 6-30 driving with camera changes
      let st;
      if (T < 6) { st = rec[0]; Object.assign(veh.s, st); poseCar();
        const a = 2.6 + T * 0.32, r = 0.62 - T * 0.02; camera.position.set(car.position.x + Math.cos(a) * r, 0.11 + T * 0.012, car.position.z + Math.sin(a) * r);
        camera.lookAt(car.position.x + 0.02, 0.03, car.position.z); camera.fov = 34; camera.updateProjectionMatrix();
      } else {
        const t = (T - 6) * 1.0; st = sample(t); Object.assign(veh.s, st); poseCar();
        const shot = Math.floor((T - 6) / 4) % 4;
        cam = ["chase", "tv", "chase", "onboard"][shot];
        // chase: smooth within a shot, snap at the cut
        const cut = Math.floor((T - 6) / 4) !== Math.floor((T - 6 - 1 / FPS) / 4) || i === Math.round(6 * FPS);
        updateCamera(1 / FPS, cut);
        lapStart = 0; document.body.classList.remove("clean"); hud();
      }
      sun.position.copy(car.position).addScaledVector(sunDir, 12); sun.target.position.copy(car.position);
      renderer.render(scene, camera);
      return new Promise((r) => requestAnimationFrame(() => r(true)));
    },
  };
}

// ------------------------------------------------------------------ boot
const loader = new GLTFLoader();
(async () => {
  info = await (await fetch("models/sc02.json")).json();
  const gltf = await new Promise((res, rej) => loader.load("models/sc02.glb", res, (e) => { if (e.total) $("lp").style.width = (e.loaded / e.total) * 100 + "%"; }, rej));
  const geo = flatten(gltf.scene);
  car = buildCar(geo);
  makeVeh(); poseCar();
  resize();
  camera.position.set(car.position.x - 0.7, 0.25, car.position.z + 0.5); camera.lookAt(car.position);
  $("veil").style.opacity = 0; setTimeout(() => $("veil").classList.add("hidden"), 900);
  window.__dbg = { get veh() { return veh; }, car, scene, camera, controls, setCam: (c) => { cam = c; controls.enabled = c === "orbit"; }, M };
  if (VIDEO) { videoSetup(); window.__ready = true; }
  requestAnimationFrame(frame);
})().catch((e) => { console.error(e); document.querySelector("#veil .mark").textContent = "error: " + e.message; });
