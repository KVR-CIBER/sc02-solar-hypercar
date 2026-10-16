// Solar Challenger – browser simulation (three.js r160). Physics: physics.js (same model as sim/sim.py).
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { MOTORS, DEFAULTS, createCar, optimiseLaunch } from "./physics.js";

const $ = (id) => document.getElementById(id);
const Q = new URLSearchParams(location.search);
const VIDEO = Q.has("video");
if (VIDEO) document.body.classList.add("render");

// ------------------------------------------------------------------ renderer / scene
const canvas = $("view");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: VIDEO });
renderer.setPixelRatio(VIDEO ? 1 : Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled = true;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d1117);
scene.fog = new THREE.Fog(0x0d1117, 9, 26);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(38, 1, 0.005, 200);
camera.position.set(-0.5, 0.25, 0.45);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.target.set(0, 0.03, 0);
controls.enabled = false;

const hemi = new THREE.HemisphereLight(0xdfe8ff, 0x3a2a1a, 0.55);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff2e0, 2.6);
sun.castShadow = true;
sun.shadow.mapSize.set(VIDEO ? 4096 : 2048, VIDEO ? 4096 : 2048);
sun.shadow.camera.left = -0.6; sun.shadow.camera.right = 0.6; sun.shadow.camera.top = 0.6; sun.shadow.camera.bottom = -0.6;
sun.shadow.camera.near = 0.1; sun.shadow.camera.far = 6;
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.01;
scene.add(sun, sun.target);
// hall ceiling lights (soft)
for (let i = 0; i < 4; i++) {
  const l = new THREE.PointLight(0xffffff, 6, 14, 2);
  l.position.set(i * 4.5, 5, 0.6);
  scene.add(l);
}

function resize() {
  const w = VIDEO ? +(Q.get("w") || 3840) : innerWidth, h = VIDEO ? +(Q.get("h") || 2160) : innerHeight;
  renderer.setSize(w, h, !VIDEO);
  if (VIDEO) { canvas.style.width = "100vw"; canvas.style.height = "100vh"; }
  camera.aspect = w / h; camera.updateProjectionMatrix();
  drawGraph();
}
addEventListener("resize", resize);

// ------------------------------------------------------------------ hall + track
const LANES = [0, 0.42];          // z of lane 1 (our car) and lane 2 (ghost)
function canvasTex(w, h, draw, repeat) {
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); }
  return t;
}
const woodTex = canvasTex(1024, 1024, (g, w, h) => {
  const planks = 8;
  for (let i = 0; i < planks; i++) {
    let x = 0;
    while (x < w) {
      const len = 180 + Math.random() * 380;
      const base = 150 + Math.random() * 35;
      g.fillStyle = `rgb(${base + 40},${base - 10},${base - 70})`;
      g.fillRect(x, (i * h) / planks, len, h / planks);
      g.strokeStyle = "rgba(60,30,10,0.25)";
      for (let k = 0; k < 9; k++) {
        g.beginPath();
        const y = (i * h) / planks + Math.random() * (h / planks);
        g.moveTo(x, y); g.bezierCurveTo(x + len / 3, y + 3, x + (2 * len) / 3, y - 3, x + len, y + 1); g.stroke();
      }
      g.fillStyle = "rgba(40,20,5,0.55)"; g.fillRect(x, (i * h) / planks, 2, h / planks);
      x += len;
    }
    g.fillStyle = "rgba(40,20,5,0.5)"; g.fillRect(0, (i * h) / planks, w, 2);
  }
}, [14, 14]);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60),
  new THREE.MeshStandardMaterial({ map: woodTex, roughness: 0.38, metalness: 0.0 }));
floor.rotation.x = -Math.PI / 2; floor.position.set(6, 0, 0); floor.receiveShadow = true;
scene.add(floor);

const track = new THREE.Group(); scene.add(track);
const matLane = new THREE.MeshStandardMaterial({ color: 0x1f2329, roughness: 0.85 });
const matWhite = new THREE.MeshStandardMaterial({ color: 0xf2f2f2, roughness: 0.6 });
function plane(w, d, mat, x, z, y = 0.0006) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), mat);
  m.rotation.x = -Math.PI / 2; m.position.set(x, y, z); m.receiveShadow = true; track.add(m); return m;
}
for (const z of LANES) {
  plane(16.5, 0.36, matLane, 6.75, z);
  plane(16.5, 0.012, matWhite, 6.75, z - 0.18, 0.0008);
  plane(16.5, 0.012, matWhite, 6.75, z + 0.18, 0.0008);
}
const checker = canvasTex(256, 32, (g, w, h) => {
  for (let i = 0; i < 16; i++) for (let j = 0; j < 2; j++) { g.fillStyle = (i + j) % 2 ? "#111" : "#f4f4f4"; g.fillRect(i * 16, j * 16, 16, 16); }
});
for (const x of [0, 12]) {
  const m = plane(0.05, 0.84, new THREE.MeshStandardMaterial({ map: checker, roughness: 0.6 }), x, 0.21, 0.001);
  m.rotation.z = Math.PI / 2;
}
for (let i = 1; i <= 15; i++) {
  const t = canvasTex(128, 64, (g) => { g.fillStyle = "rgba(255,255,255,0.85)"; g.font = "bold 44px system-ui"; g.textAlign = "center"; g.fillText(i + " m", 64, 48); });
  const m = plane(0.16, 0.08, new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false }), i, -0.27, 0.001);
  m.rotation.z = Math.PI / 2;
  if (i <= 12) plane(0.006, 0.36, new THREE.MeshBasicMaterial({ color: 0x555b66 }), i, 0, 0.0009);
}
// timing gates
function gate(x, beamColor) {
  const g = new THREE.Group();
  const post = new THREE.MeshStandardMaterial({ color: 0x2b3038, roughness: 0.4, metalness: 0.6 });
  for (const z of [-0.5, 0.92]) {
    const p = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.12, 0.03), post);
    p.position.set(x, 0.06, z); p.castShadow = true; g.add(p);
    const led = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.012, 0.004), new THREE.MeshBasicMaterial({ color: beamColor }));
    led.position.set(x, 0.03, z + (z < 0 ? 0.016 : -0.016)); g.add(led);
  }
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.0012, 0.0012, 1.42, 6),
    new THREE.MeshBasicMaterial({ color: beamColor, transparent: true, opacity: 0.85 }));
  beam.rotation.x = Math.PI / 2; beam.position.set(x, 0.03, 0.21); g.add(beam);
  track.add(g);
  return beam;
}
const finishBeam = gate(12, 0xff2a2a);
// hall walls far away for depth
const wallMat = new THREE.MeshStandardMaterial({ color: 0x1a1f27, roughness: 0.9 });
const wall = new THREE.Mesh(new THREE.PlaneGeometry(60, 8), wallMat);
wall.position.set(6, 4, -6); scene.add(wall);
const wall2 = wall.clone(); wall2.position.set(6, 4, 7); wall2.rotation.y = Math.PI; scene.add(wall2);
const banner = canvasTex(1536, 128, (g, w, h) => {
  g.fillStyle = "#0f172a"; g.fillRect(0, 0, w, h);
  g.fillStyle = "#f59e0b"; g.font = "bold 64px system-ui"; g.fillText("SOLAR OLYMPIADE 2027", 40, 88);
  g.fillStyle = "#93c5fd"; g.font = "44px system-ui"; g.textAlign = "right"; g.fillText("CHALLENGER · 12 m", w - 40, 86);
});
const ban = new THREE.Mesh(new THREE.PlaneGeometry(9, 0.75), new THREE.MeshBasicMaterial({ map: banner }));
ban.position.set(6, 1.4, -5.98); scene.add(ban);

// ------------------------------------------------------------------ car model
const CAR_X0 = -0.188;           // front of the car on the start line
let info = null, carTemplate = null, ghostCar = null, mainCar = null, mold = null;
const partMeshes = [];           // for raycasting in the parts tab

function partOf(name) { return info.parts.find((p) => p.name === name) || { label: name, material: "", group: "static" }; }

function tuneMaterial(mesh) {
  const n = mesh.name;
  const m = mesh.material.clone();
  m.side = THREE.DoubleSide;
  if (n.startsWith("tyre")) { m.roughness = 0.93; m.metalness = 0; }
  else if (n.startsWith("motor")) { m.roughness = 0.32; m.metalness = 0.9; }
  else if (n.startsWith("pinion")) { m.color.set(0xc9a24a); m.roughness = 0.28; m.metalness = 1; }
  else if (n.startsWith("bearing")) { m.roughness = 0.22; m.metalness = 1; }
  else if (n.startsWith("axle")) { m.roughness = 0.35; m.metalness = 0.3; }
  else if (n === "cells") { m.roughness = 0.35; m.metalness = 0.1; }
  else if (n === "panel") { m.roughness = 0.15; m.metalness = 0.3; }
  else { m.roughness = 0.55; m.metalness = 0.0; }
  mesh.material = m;
  mesh.castShadow = true; mesh.receiveShadow = true;
}

const solarTex = canvasTex(512, 456, (g, w, h) => {
  g.fillStyle = "#0b1638"; g.fillRect(0, 0, w, h);
  const cx = 6, cy = 5;
  for (let i = 0; i < cx; i++) for (let j = 0; j < cy; j++) {
    const x = 8 + i * ((w - 16) / cx), y = 8 + j * ((h - 16) / cy), cw = (w - 16) / cx - 6, ch = (h - 16) / cy - 6;
    const gr = g.createLinearGradient(x, y, x + cw, y + ch);
    gr.addColorStop(0, "#1b2f73"); gr.addColorStop(1, "#0e1d4f");
    g.fillStyle = gr; g.fillRect(x, y, cw, ch);
    g.strokeStyle = "rgba(200,210,230,0.55)"; g.lineWidth = 1.5;
    for (let k = 1; k < 3; k++) { g.beginPath(); g.moveTo(x, y + (k * ch) / 3); g.lineTo(x + cw, y + (k * ch) / 3); g.stroke(); }
  }
});

// CadQuery writes one glTF primitive per B-rep face -> merge every part into a single mesh
function flatten(root) {
  const out = [];
  for (const node of [...root.children]) {
    const geos = [], mats = [];
    node.updateMatrixWorld(true);
    const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
    node.traverse((o) => {
      if (!o.isMesh) return;
      const g = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
      for (const k of Object.keys(g.attributes)) if (k !== "position" && k !== "normal") g.deleteAttribute(k);
      g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld));
      geos.push(g); mats.push(o.material);
    });
    root.remove(node);
    if (!geos.length) continue;
    const mesh = new THREE.Mesh(mergeGeometries(geos, false), mats[0]);
    mesh.name = node.name;
    root.add(mesh);
    out.push(mesh);
  }
  return out;
}

function buildCar(gltfScene) {
  const root = gltfScene.getObjectByName("car");
  root.updateMatrixWorld(true);
  const meshes = flatten(root);
  // car centre (mm, CAD) for exploding
  const box = new THREE.Box3();
  const holders = {};
  for (const mesh of meshes) {
    const name = mesh.name;
    tuneMaterial(mesh);
    mesh.geometry.computeBoundingBox();
    const c = mesh.geometry.boundingBox.getCenter(new THREE.Vector3());
    box.union(mesh.geometry.boundingBox);
    const p = partOf(name);
    const holder = new THREE.Group(); holder.name = "holder_" + name;
    holder.userData = { center: c, part: p };
    let parent = holder;
    let axis = null;
    if (p.group === "rear") axis = [0, info.axle_z, "rear"];
    else if (p.group === "front") axis = [info.wheelbase, info.axle_z, "front"];
    else if (p.group && p.group.startsWith("pinion@")) axis = [parseFloat(p.group.split("@")[1]), info.axle_z, "pinion"];
    if (axis) {
      const pv = new THREE.Group(); pv.name = "pivot_" + axis[2];
      pv.position.set(axis[0], 0, axis[1]);
      holder.add(pv); parent = pv;
      mesh.position.set(-axis[0], 0, -axis[1]);
    }
    if (mesh.parent) mesh.parent.remove(mesh);
    parent.add(mesh);
    root.add(holder);
    holders[name] = holder;
  }
  // printed solar cells on top of the panel
  const pb = holders.panel.children[0].geometry.boundingBox;
  const sp = new THREE.Mesh(new THREE.PlaneGeometry(pb.max.x - pb.min.x - 1, pb.max.y - pb.min.y - 1),
    new THREE.MeshStandardMaterial({ map: solarTex, roughness: 0.12, metalness: 0.35 }));
  sp.position.set((pb.min.x + pb.max.x) / 2, (pb.min.y + pb.max.y) / 2, pb.max.z + 0.05);
  sp.name = "panel_cells";
  holders.panel.add(sp);
  root.userData.center = box.getCenter(new THREE.Vector3());
  // remove empty nodes left by the loader
  [...root.children].forEach((ch) => { if (!ch.name.startsWith("holder_")) root.remove(ch); });
  const wrap = new THREE.Group();          // track-space wrapper: x along the lane
  gltfScene.scale.setScalar(0.001);
  wrap.add(gltfScene);
  return wrap;
}

function instance(template, ghost) {
  const obj = template.clone(true);
  const pivots = { rear: [], front: [], pinion: [] };
  const holders = [];
  obj.traverse((o) => {
    if (o.isMesh) {
      o.material = o.material.clone();
      if (ghost) {
        o.material.transparent = true; o.material.opacity = 0.38; o.material.depthWrite = false;
        o.material.color.lerp(new THREE.Color(0xff9a3c), 0.55); o.castShadow = false;
      }
      if (!ghost) partMeshes.push(o);
    }
    if (o.name.startsWith("pivot_")) pivots[o.name.slice(6)].push(o);
    if (o.name.startsWith("holder_")) holders.push(o);
  });
  scene.add(obj);
  return { obj, pivots, holders, ghost };
}

// ------------------------------------------------------------------ tyre mold
function buildMold(gltfScene) {
  const root = gltfScene.getObjectByName("mold");
  root.updateMatrixWorld(true);
  const items = {};
  const meshes = flatten(root);
  for (const m of meshes) {
    m.material = m.material.clone();
    m.material.side = THREE.DoubleSide;
    m.castShadow = m.receiveShadow = true;
    m.material.roughness = 0.5;
    if (m.name === "mold_lid") { m.material.transparent = true; m.material.opacity = 0.45; m.material.depthWrite = false; }
    if (m.name.startsWith("silicone")) { m.material.roughness = 0.9; m.material.clippingPlanes = [moldClip]; }
    items[m.name] = m;
  }
  gltfScene.scale.setScalar(0.001);
  const g = new THREE.Group(); g.add(gltfScene);
  g.position.set(-0.75, 0, -0.85);
  g.rotation.y = 0.5;
  scene.add(g);
  return { g, items, lidBase: items.mold_lid.position.clone() };
}
const moldClip = new THREE.Plane(new THREE.Vector3(0, -1, 0), 0);
function setMold(lid, fill) {
  if (!mold) return;
  const lidM = mold.items.mold_lid;
  lidM.position.copy(mold.lidBase);
  lidM.position.z += lid * 70;                                  // CAD mm (z up inside the glTF root)
  lidM.rotation.y = 0;
  const yb = mold.g.position.y + (info.mold.floor + fill * info.mold.tyre_w) * 0.001;
  moldClip.constant = fill <= 0 ? -1 : yb;
  for (let i = 0; i < 4; i++) mold.items["silicone_" + i].visible = fill > 0.001;
}

// ------------------------------------------------------------------ physics traces
const TRACE_DT = 0.001;
function computeTrace(cfg) {
  const car = createCar(cfg);
  const dt = 1e-4, every = Math.round(TRACE_DT / dt);
  const s = car.state, out = [];
  let k = 0, finish = null;
  while (s.t < 8) {
    if (k % every === 0) out.push({ t: s.t, x: s.x, v: s.v, u: s.u, I: s.I, Vb: s.Vbus, k: Math.max(0, s.kappa), d: s.d, ar: s.wheelAngleR, af: s.wheelAngleF, a: s.a });
    if (s.x >= 14) break;                                         // firmware stops after 14 m
    car.step(dt); k++;
    if (!finish && s.done) finish = { t12: s.t12, v12: s.v12, Ipk: s.Ipk, Vmin: s.Vmin };
  }
  // coast + catch net: decelerate to stop (visual only)
  let last = { ...out[out.length - 1] };
  const r = cfg.D / 2;
  while (last.v > 0) {
    const v = Math.max(0, last.v - 7 * TRACE_DT), x = last.x + v * TRACE_DT;
    last = { ...last, t: last.t + TRACE_DT, v, u: v, x, I: 0, d: 0, k: 0, a: -7, ar: last.ar + (v / r) * TRACE_DT, af: last.af + (v / r) * TRACE_DT };
    out.push(last);
  }
  return { cfg, samples: out, ...finish, mass: car.mass, G: car.G, motor: car.motor.name };
}
function sampleAt(tr, t) {
  if (!tr) return null;
  const S = tr.samples;
  const f = Math.max(0, t) / TRACE_DT;
  const i = Math.min(S.length - 2, Math.floor(f));
  if (i < 0) return S[0];
  const a = S[i], b = S[i + 1], w = Math.min(1, f - i);
  const o = {};
  for (const k in a) o[k] = a[k] + (b[k] - a[k]) * w;
  return o;
}

// ------------------------------------------------------------------ posing
function poseCar(inst, smp, laneZ, G, D) {
  if (!inst) return;
  inst.obj.visible = true;
  inst.obj.position.set(CAR_X0 + (smp ? smp.x : 0), 0, laneZ);
  inst.obj.rotation.z = smp ? THREE.MathUtils.clamp(smp.a * 0.0012, -0.012, 0.012) : 0;
  const ar = smp ? smp.ar : 0, af = smp ? smp.af : 0;
  inst.pivots.rear.forEach((p) => (p.rotation.y = ar));
  inst.pivots.front.forEach((p) => (p.rotation.y = af));
  inst.pivots.pinion.forEach((p) => (p.rotation.y = -ar * G));
}
function setExplode(inst, e) {
  if (!inst) return;
  for (const h of inst.holders) {
    const c = h.userData.center, n = h.name.slice(7);
    const extra = n === "panel" ? 95 : n === "panel_frame" ? 60 : n === "motor_clamp" ? 55 : n.startsWith("cap_") ? 30 : n === "cells" ? 28 : 0;
    h.position.set((c.x - 85) * 0.55 * e, c.y * 0.9 * e, ((c.z - 16) * 1.3 + extra) * e);
  }
}

// ------------------------------------------------------------------ smoke
const smokeTex = canvasTex(64, 64, (g) => {
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, "rgba(220,220,220,0.9)"); r.addColorStop(1, "rgba(220,220,220,0)");
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
});
const smoke = [];
for (let i = 0; i < 260; i++) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: smokeTex, transparent: true, depthWrite: false, opacity: 0 }));
  s.visible = false; scene.add(s); smoke.push({ s, life: 0, vel: new THREE.Vector3() });
}
let smokeIdx = 0;
function emitSmoke(x, z, slip, dt) {
  const n = Math.min(6, Math.floor(slip * 180 * dt + Math.random()));
  for (let i = 0; i < n; i++) {
    const p = smoke[smokeIdx++ % smoke.length];
    p.life = 1; p.s.visible = true;
    p.s.position.set(x - 0.01, 0.01, z + (Math.random() - 0.5) * 0.02);
    p.vel.set(-0.15 - Math.random() * 0.25, 0.05 + Math.random() * 0.12, (Math.random() - 0.5) * 0.15);
  }
}
function updateSmoke(dt) {
  for (const p of smoke) {
    if (p.life <= 0) continue;
    p.life -= dt * 0.9;
    p.s.position.addScaledVector(p.vel, dt);
    const sc = 0.02 + (1 - p.life) * 0.12;
    p.s.scale.set(sc, sc, sc);
    p.s.material.opacity = Math.max(0, p.life) * 0.45;
    if (p.life <= 0) p.s.visible = false;
  }
}
function clearSmoke() { smoke.forEach((p) => { p.life = 0; p.s.visible = false; }); }

// ------------------------------------------------------------------ state + UI
const cfg = { ...DEFAULTS };
let mainTrace = null, ghostTrace = null;
let playT = -1, playing = false, slow = 1, camMode = "chase", tab = "race", ghostMode = "nolc";
let runs = [];
try { runs = JSON.parse(localStorage.getItem("solar_runs") || "[]"); } catch (e) {}
let prevTrace = null, bestTrace = null;

function readUI() {
  cfg.motor = $("motor").value;
  cfg.pinion = +$("pinion").value; cfg.spur = +$("spur").value;
  cfg.D = +$("D").value / 1000; cfg.pi4 = $("pi4").checked; cfg.extraMass = +$("xm").value / 1000;
  cfg.launch = $("lc").checked; cfg.d0 = +$("d0").value; cfg.Tr = +$("Tr").value;
  cfg.mu = +$("mu").value; cfg.Rb = +$("Rb").value;
  $("Do").textContent = $("D").value + " mm"; $("xmo").textContent = $("xm").value + " g";
  $("d0o").textContent = Math.round(cfg.d0 * 100) + " %"; $("Tro").textContent = Math.round(cfg.Tr * 1000) + " ms";
  $("muo").textContent = cfg.mu.toFixed(2); $("Rbo").textContent = cfg.Rb.toFixed(2) + " Ω";
}
function segInit(id, cb) {
  $(id).addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    [...$(id).children].forEach((x) => x.classList.toggle("on", x === b));
    cb(b.dataset.v);
  });
}
function setSeg(id, v) { [...$(id).children].forEach((x) => x.classList.toggle("on", x.dataset.v == v)); }

for (const [k, m] of Object.entries(MOTORS)) $("motor").add(new Option(m.name, k, false, k === cfg.motor));
["motor", "pinion", "spur", "D", "pi4", "xm", "lc", "d0", "Tr", "mu", "Rb"].forEach((id) => $(id).addEventListener("input", () => { readUI(); resetRace(); }));
segInit("nmot", (v) => { cfg.nMotors = +v; resetRace(); });
segInit("voc", (v) => { cfg.Voc = +v; resetRace(); });
segInit("slowmo", (v) => (slow = +v));
segInit("cams", (v) => setCam(v));
segInit("ghost", (v) => { ghostMode = v; resetRace(); });
$("go").onclick = () => startRace();
$("reset").onclick = () => resetRace();
$("opt").onclick = () => {
  readUI();
  $("opt").textContent = "…";
  setTimeout(() => {
    const b = optimiseLaunch(cfg);
    $("d0").value = b.d0; $("Tr").value = b.Tr; $("lc").checked = true; readUI(); resetRace();
    $("opt").textContent = `⚡ ${b.d0 * 100 | 0}% / ${b.Tr * 1000 | 0} ms → ${b.t.toFixed(3)} s`;
  }, 30);
};
addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
  if (e.code === "Space") { e.preventDefault(); playing ? resetRace() : startRace(); }
  if (e.key === "r" || e.key === "R") resetRace();
  if (e.key === "c" || e.key === "C") { const L = ["chase", "side", "top", "finish", "free"]; setCam(L[(L.indexOf(camMode) + 1) % L.length]); }
});
document.querySelectorAll("#tabs button").forEach((b) => (b.onclick = () => setTab(b.dataset.tab)));

function setCam(v) {
  if (v !== camMode) startCamBlend();
  camMode = v; setSeg("cams", v);
  controls.enabled = v === "free" || tab !== "race";
}
function setTab(t) {
  tab = t;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === t));
  ["race", "parts", "mold", "files"].forEach((p) => $("pane-" + p).classList.toggle("hidden", p !== t));
  $("hud").classList.toggle("hidden", t !== "race");
  $("graph").classList.toggle("hidden", t !== "race");
  $("result").classList.add("hidden");
  controls.enabled = t !== "race" || camMode === "free";
  if (ghostCar) ghostCar.obj.visible = t === "race" && !!ghostTrace;
  if (t === "parts") { resetRace(); controls.target.set(-0.1, 0.03, 0); camera.position.set(-0.45, 0.28, -0.42); }
  if (t === "mold") { controls.target.copy(mold.g.position).add(new THREE.Vector3(0, 0.01, 0)); camera.position.copy(mold.g.position).add(new THREE.Vector3(0.22, 0.24, 0.26)); }
  if (t === "files") { controls.target.set(-0.1, 0.03, 0); camera.position.set(-0.5, 0.2, 0.5); }
  if (t !== "parts") { setExplode(mainCar, 0); $("explode").value = 0; $("exo").textContent = "0 %"; }
}

function ghostCfg() {
  if (ghostMode === "nolc") return { ...cfg, launch: false };
  return null;
}
function resetRace() {
  readUI();
  playing = false; playT = -1;
  mainTrace = computeTrace(cfg);
  ghostTrace = ghostMode === "nolc" ? computeTrace(ghostCfg()) : ghostMode === "prev" ? prevTrace : ghostMode === "best" ? bestTrace : null;
  clearSmoke();
  $("result").classList.add("hidden");
  $("countdown").classList.add("hidden");
  finishBeam.material.color.set(0xff2a2a);
  applyPose(0, true);
  drawGraph();
}
let countdownEnd = 0;
function startRace() {
  if (tab !== "race") setTab("race");
  resetRace();
  playing = true; playT = -1.8;                                     // 3-2-1 countdown in sim-independent time
  countdownEnd = performance.now() + 1800;
}

function finishRun() {
  const r = mainTrace;
  const row = { t: r.t12, v: r.v12 * 3.6, cfg: summary(cfg), when: Date.now() };
  runs.unshift(row); runs = runs.slice(0, 30);
  try { localStorage.setItem("solar_runs", JSON.stringify(runs)); } catch (e) {}
  prevTrace = r;
  if (!bestTrace || r.t12 < bestTrace.t12) bestTrace = r;
  renderRuns();
  const gt = ghostTrace && ghostTrace.t12;
  $("res-t").textContent = r.t12.toFixed(3) + " s";
  $("res-sub").textContent = `${(r.v12 * 3.6).toFixed(1)} km/h op de finish · piek ${r.Ipk.toFixed(1)} A · ${(r.mass * 1000).toFixed(0)} g` +
    (gt ? ` · spook ${gt.toFixed(3)} s (${(r.t12 - gt >= 0 ? "+" : "") + (r.t12 - gt).toFixed(3)})` : "");
  $("result").classList.remove("hidden");
}
function summary(c) {
  return `${c.nMotors}× ${MOTORS[c.motor].name.replace("Tamiya ", "")}, ${c.pinion}:${c.spur}, Ø${Math.round(c.D * 1000)}` +
    (c.launch ? `, LC ${Math.round(c.d0 * 100)}%/${Math.round(c.Tr * 1000)}ms` : ", geen LC") + (c.pi4 ? ", Pi4" : "") + (c.mu !== 0.9 ? `, µ${c.mu}` : "");
}
function renderRuns() {
  const best = Math.min(...runs.map((r) => r.t));
  $("runs").tBodies[0].innerHTML = runs.map((r, i) =>
    `<tr class="${r.t === best ? "best" : ""}"><td>${runs.length - i}</td><td>${r.t.toFixed(3)}</td><td>${r.v.toFixed(1)}</td><td>${r.cfg}</td></tr>`).join("");
}

// HUD + pose for a given sim time
function applyPose(t, quiet) {
  const s = sampleAt(mainTrace, t), gs = ghostTrace ? sampleAt(ghostTrace, t) : null;
  poseCar(mainCar, s, LANES[0], mainTrace.G, cfg.D);
  if (ghostCar) {
    ghostCar.obj.visible = !!gs;
    if (gs) poseCar(ghostCar, gs, LANES[1], ghostTrace.G, ghostTrace.cfg.D);
  }
  const shown = Math.min(t, mainTrace.t12);
  $("t").textContent = Math.max(0, shown).toFixed(3);
  $("spd").textContent = (s.v * 3.6).toFixed(1);
  $("dist").textContent = Math.min(12, s.x).toFixed(2);
  $("amp").textContent = s.I.toFixed(1);
  $("vb").textContent = s.Vb.toFixed(2);
  $("duty").textContent = Math.round(s.d * 100);
  const slip = Math.min(1, s.k);
  $("slip").textContent = Math.round(slip * 100);
  $("slipbar").style.width = slip * 100 + "%";
  finishBeam.material.color.set(s.x >= 12 && s.x < 12.4 ? 0x22ff66 : 0xff2a2a);
  return { s, gs };
}

// ------------------------------------------------------------------ graph
const gctx = $("graph").getContext("2d");
function drawGraph() {
  const c = $("graph"); if (!c || !mainTrace) return;
  const dpr = devicePixelRatio || 1;
  c.width = c.clientWidth * dpr; c.height = c.clientHeight * dpr;
  const g = gctx, W = c.width, H = c.height;
  g.clearRect(0, 0, W, H);
  const tmax = 3, L = 44 * dpr, R = W - 12 * dpr, T = 12 * dpr, B = H - 22 * dpr;
  const X = (t) => L + (t / tmax) * (R - L), Y = (v, max) => B - (v / max) * (B - T);
  g.font = `${11 * dpr}px system-ui`; g.fillStyle = "#8d97a8"; g.strokeStyle = "rgba(255,255,255,0.07)";
  for (let v = 0; v <= 10; v += 2.5) { g.beginPath(); g.moveTo(L, Y(v, 10)); g.lineTo(R, Y(v, 10)); g.stroke(); g.fillText(v + " m/s", 2 * dpr, Y(v, 10) + 4 * dpr); }
  for (let t = 0; t <= tmax; t += 0.5) g.fillText(t + " s", X(t) - 8 * dpr, H - 6 * dpr);
  const line = (tr, key, max, col, dash, lw = 2) => {
    if (!tr) return;
    g.setLineDash(dash ? [6 * dpr, 5 * dpr] : []); g.strokeStyle = col; g.lineWidth = lw * dpr; g.beginPath();
    const S = tr.samples;
    for (let i = 0; i < S.length; i += 4) { if (S[i].t > tmax) break; const p = [X(S[i].t), Y(S[i][key], max)]; i ? g.lineTo(...p) : g.moveTo(...p); }
    g.stroke(); g.setLineDash([]);
  };
  // slip area
  g.fillStyle = "rgba(239,68,68,0.22)";
  g.beginPath(); g.moveTo(L, B);
  for (const s of mainTrace.samples) { if (s.t > tmax) break; g.lineTo(X(s.t), Y(Math.min(1, s.k) * 10, 10)); }
  g.lineTo(X(Math.min(tmax, mainTrace.samples.at(-1).t)), B); g.fill();
  line(mainTrace, "I", 10, "rgba(180,190,210,0.55)", true, 1.3);
  line(ghostTrace, "v", 10, "#f59e0b", true);
  line(mainTrace, "v", 10, "#3b82f6", false, 2.4);
  if (mainTrace.t12) { g.strokeStyle = "rgba(34,197,94,0.7)"; g.beginPath(); g.moveTo(X(mainTrace.t12), T); g.lineTo(X(mainTrace.t12), B); g.stroke(); }
  if (playT > 0) { g.strokeStyle = "#fff"; g.lineWidth = 1 * dpr; g.beginPath(); g.moveTo(X(Math.min(playT, tmax)), T); g.lineTo(X(Math.min(playT, tmax)), B); g.stroke(); }
  g.fillStyle = "#3b82f6"; g.fillText("snelheid", R - 250 * dpr, T + 10 * dpr);
  g.fillStyle = "#f59e0b"; g.fillText("spook", R - 190 * dpr, T + 10 * dpr);
  g.fillStyle = "rgba(180,190,210,0.8)"; g.fillText("stroom (A)", R - 145 * dpr, T + 10 * dpr);
  g.fillStyle = "rgba(239,68,68,0.9)"; g.fillText("slip", R - 70 * dpr, T + 10 * dpr);
}

// ------------------------------------------------------------------ cameras
const camPos = new THREE.Vector3(), camTgt = new THREE.Vector3();
const camFrom = { p: new THREE.Vector3(), t: new THREE.Vector3() };
let camBlend = 1;
function camFor(mode, px) {
  switch (mode) {
    case "chase": return [[px - 0.62, 0.2, -0.32], [px + 0.5, 0.02, 0.12]];
    case "side": return [[px + 0.05, 0.075, -0.62], [px + 0.05, 0.03, 0.1]];
    case "top": return [[px - 0.35, 1.45, 0.21], [px + 0.15, 0, 0.21]];
    case "finish": return [[12.55, 0.11, -0.42], [11.6, 0.03, 0.2]];
    default: return null;
  }
}
function startCamBlend() { camFrom.p.copy(camera.position); camFrom.t.copy(controls.target); camBlend = 0; }
function updateCamera(dt, px, snap) {
  if (tab !== "race" || camMode === "free") {
    if (camMode === "free" && tab === "race") { controls.target.x += (px - controls.target.x) * Math.min(1, dt * 4); }
    controls.update();
    return;
  }
  const c = camFor(camMode, px);
  camPos.set(...c[0]); camTgt.set(...c[1]);
  if (snap) camBlend = 1;
  if (camBlend < 1) {                                  // smooth hand-over after a camera switch, then lock on
    camBlend = Math.min(1, camBlend + dt / 0.7);
    const e = camBlend * camBlend * (3 - 2 * camBlend);
    camPos.lerpVectors(camFrom.p, camPos, e); camTgt.lerpVectors(camFrom.t, camTgt, e);
  }
  camera.position.copy(camPos);
  controls.target.copy(camTgt);
  camera.lookAt(controls.target);
}
function updateSun(px) {
  sun.position.set(px + 1.2, 2.6, -1.4);
  sun.target.position.set(px + 0.1, 0, 0.2);
}

// ------------------------------------------------------------------ parts tab: hover / explode
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
let hovered = null;
canvas.addEventListener("pointermove", (e) => {
  if (tab !== "parts") { $("tip").classList.add("hidden"); return; }
  mouse.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(partMeshes, false)[0];
  setHover(hit ? hit.object : null);
  if (hit) {
    const p = partOf(hit.object.name);
    $("tip").innerHTML = `<b>${p.label}</b><br><span style="color:#8d97a8">${p.material}${p.mass_g ? " · " + p.mass_g + " g" : ""}</span>`;
    $("tip").style.left = e.clientX + 14 + "px"; $("tip").style.top = e.clientY + 10 + "px";
    $("tip").classList.remove("hidden");
  } else $("tip").classList.add("hidden");
});
function setHover(m) {
  if (hovered === m) return;
  if (hovered) hovered.material.emissive.set(0x000000);
  hovered = m;
  if (m) m.material.emissive.set(0x1d4ed8);
}
$("explode").addEventListener("input", () => { const e = +$("explode").value; setExplode(mainCar, e); $("exo").textContent = Math.round(e * 100) + " %"; });
$("xray").addEventListener("change", () => {
  for (const m of partMeshes) if (["chassis", "front_carrier", "panel_frame", "panel", "panel_cells"].includes(m.name)) {
    m.material.transparent = $("xray").checked; m.material.opacity = $("xray").checked ? 0.18 : 1; m.material.depthWrite = !$("xray").checked;
  }
});
function renderPartList() {
  const agg = {};
  for (const p of info.parts) {
    const k = p.label;
    agg[k] = agg[k] || { label: k, material: p.material, mass: 0, n: 0, name: p.name };
    agg[k].mass += p.mass_g || 0; agg[k].n++;
  }
  $("partlist").tBodies[0].innerHTML = Object.values(agg).sort((a, b) => b.mass - a.mass)
    .map((a) => `<tr data-name="${a.name}"><td>${a.n > 1 ? a.n + "× " : ""}${a.label}</td><td>${a.material}</td><td>${a.mass.toFixed(1)}</td></tr>`).join("") +
    `<tr><td><b>Totaal</b></td><td></td><td><b>${info.parts.reduce((s, p) => s + (p.mass_g || 0), 0).toFixed(0)}</b></td></tr>`;
  $("partlist").onclick = (e) => {
    const tr = e.target.closest("tr[data-name]"); if (!tr) return;
    const m = partMeshes.find((x) => x.name === tr.dataset.name);
    setHover(m);
    const p = partOf(tr.dataset.name);
    $("partinfo").innerHTML = `<b>${p.label}</b><br>${p.material}${p.mass_g ? " · " + p.mass_g + " g" : ""}`;
    $("partinfo").classList.remove("hidden");
  };
}

// ------------------------------------------------------------------ mold tab
let fillAnim = null;
$("lid").addEventListener("input", () => { setMold(+$("lid").value, +$("fillr").value); $("lido").textContent = +$("lid").value > 0.02 ? "open" : "dicht"; });
$("fillr").addEventListener("input", () => { setMold(+$("lid").value, +$("fillr").value); $("fillo").textContent = Math.round($("fillr").value * 100) + " %"; });
$("fill").onclick = () => { $("lid").value = 0; fillAnim = { t: 0, phase: "fill" }; };
$("openmold").onclick = () => { fillAnim = { t: 0, phase: "open" }; };

// ------------------------------------------------------------------ files tab
async function renderFiles() {
  try {
    const f = await (await fetch("files/files.json")).json();
    $("filelist").innerHTML = f.map((sec) => `<h3>${sec.title}</h3>` + sec.items.map((it) =>
      `<a href="files/${it.path}" download><span>${it.label}</span><small>${it.size}</small></a>`).join("")).join("");
  } catch (e) {
    $("filelist").innerHTML = `<p class="hint">Geen downloads gevonden (files/files.json).</p>`;
  }
}

// ------------------------------------------------------------------ main loop
let lastT = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - lastT) / 1000); lastT = now;
  if (!VIDEO) {
    if (tab === "race" && mainTrace) {
      if (playing) {
        if (now < countdownEnd) {
          const n = Math.ceil((countdownEnd - now) / 600);
          $("countdown").textContent = n; $("countdown").classList.remove("hidden");
          playT = 0;
        } else {
          $("countdown").classList.add("hidden");
          const before = playT;
          playT += dt * slow;
          const { s, gs } = applyPose(playT);
          if (s.k > 0.25) emitSmoke(CAR_X0 + s.x + 0.0, LANES[0] - 0.06, s.k, dt * slow);
          if (gs && gs.k > 0.25) { emitSmoke(CAR_X0 + gs.x, LANES[1] - 0.06, gs.k, dt * slow); emitSmoke(CAR_X0 + gs.x, LANES[1] + 0.06, gs.k, dt * slow); }
          if (before < mainTrace.t12 && playT >= mainTrace.t12) finishRun();
          if (playT > mainTrace.samples.at(-1).t + 0.6 && (!ghostTrace || playT > ghostTrace.samples.at(-1).t)) playing = false;
          drawGraph();
        }
      }
      const px = CAR_X0 + sampleAt(mainTrace, Math.max(0, playT)).x + 0.1;
      updateCamera(dt, px);
      updateSun(px);
    } else {
      updateCamera(dt, 0);
      updateSun(tab === "mold" ? mold.g.position.x : 0);
    }
    if (tab === "parts" && $("spinparts").checked && mainCar) {
      const a = now / 1000 * 3;
      mainCar.pivots.rear.forEach((p) => (p.rotation.y = a)); mainCar.pivots.front.forEach((p) => (p.rotation.y = a));
      mainCar.pivots.pinion.forEach((p) => (p.rotation.y = -a * mainTrace.G));
    }
    if (fillAnim) {
      fillAnim.t += dt;
      if (fillAnim.phase === "fill") {
        const f = Math.min(1, fillAnim.t / 4); $("fillr").value = f; $("fillo").textContent = Math.round(f * 100) + " %"; setMold(0, f);
        if (f >= 1) fillAnim = null;
      } else {
        const l = Math.min(1, fillAnim.t / 1.5); $("lid").value = l; $("lido").textContent = "open"; setMold(l, +$("fillr").value);
        if (l >= 1) fillAnim = null;
      }
    }
    updateSmoke(dt * (tab === "race" ? slow : 1));
    renderer.render(scene, camera);
  }
  requestAnimationFrame(frame);
}

// ------------------------------------------------------------------ video timeline (deterministic, used by tools/render_video.mjs)
const ease = (x) => x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
const lerp = (a, b, t) => a + (b - a) * t;
const lerp3 = (a, b, t) => a.map((v, i) => lerp(v, b[i], t));
function videoSetup() {
  const vtr = computeTrace({ ...DEFAULTS });
  const gtr = computeTrace({ ...DEFAULTS, launch: false });
  const DUR = 27, FPS = +(Q.get("fps") || 60);
  let lastSmokeT = 0;
  const title = (h, p) => {
    if (!h) { $("title-card").classList.add("hidden"); return; }
    $("tc-h").textContent = h; $("tc-p").textContent = p || ""; $("title-card").classList.remove("hidden");
  };
  const orbit = (ang, r, h, tgt) => [[tgt[0] + Math.cos(ang) * r, h, tgt[2] + Math.sin(ang) * r], tgt];
  window.__video = {
    fps: FPS, duration: DUR, frames: Math.round(DUR * FPS),
    frame(i) {
      const T = i / FPS, dtv = 1 / FPS;
      let cam, simT = 0, simGT = 0, showGhost = false, hud = false, ex = 0, lid = 0, fill = 0, slowFactor = 1;
      $("countdown").classList.add("hidden"); $("result").classList.add("hidden");
      mainTrace = vtr; ghostTrace = gtr;
      if (T < 4.5) {                                            // S1 hero orbit
        cam = orbit(lerp(3.6, 4.6, T / 4.5), lerp(0.46, 0.38, T / 4.5), lerp(0.1, 0.16, T / 4.5), [-0.08, 0.025, 0]);
        title("SOLAR CHALLENGER", "Solar Olympiade 2027 · 2× Hyper-Dash 3 · 310 g · 131 mm breed");
      } else if (T < 9) {                                       // S2 exploded view
        const u = (T - 4.5) / 4.5;
        ex = ease(u / 0.4) * (1 - ease((u - 0.7) / 0.3));
        cam = orbit(lerp(4.6, 5.9, u), lerp(0.55, 0.6, u), lerp(0.24, 0.3, u), [-0.08, 0.05, 0]);
        title("Parametrisch CAD", "32 onderdelen · 0 botsingen · alles 3D-printbaar zonder support");
      } else if (T < 10.8) {                                    // S3 countdown
        const u = ease((T - 9) / 1.8);
        cam = [lerp3(orbit(5.9, 0.6, 0.3, [-0.08, 0.05, 0])[0], [-0.75, 0.2, -0.3], u), lerp3([-0.08, 0.05, 0], [0.3, 0.02, 0.18], u)];
        showGhost = true; title(null);
        const n = 3 - Math.floor((T - 9) / 0.6);
        $("countdown").textContent = n; $("countdown").classList.remove("hidden");
        hud = true;
      } else if (T < 13.6) {                                    // S4 race real time
        simT = simGT = T - 10.8; showGhost = true; hud = true;
        const pm = CAR_X0 + (sampleAt(vtr, simT).x + sampleAt(gtr, simT).x) / 2;
        const u = ease((simT - 0.3) / 1.2);
        cam = [[pm - lerp(0.75, 1.15, u), lerp(0.16, 0.36, u), lerp(-0.35, 0.21, u)], [pm + 0.45, 0.01, 0.21]];
        title(null);
      } else if (T < 17.6) {                                    // S5 slow-motion launch replay
        const u = (T - 13.6) / 4;
        simT = simGT = u * 0.7; slowFactor = 0.175; showGhost = true; hud = true;
        const pm = CAR_X0 + (sampleAt(vtr, simT).x + sampleAt(gtr, simT).x) / 2;
        cam = [[pm - 0.42, 0.075, lerp(0.05, 0.37, ease(u))], [pm + 0.05, 0.02, 0.21]];
        title("Launch control", "blauw: 45 % → 100 % gas in 350 ms · oranje: vol gas → 90 % wielslip");
      } else if (T < 20.6) {                                    // S6 finish
        const u = (T - 17.6) / 3;
        simT = simGT = lerp(vtr.t12 - 0.35, gtr.t12 + 0.15, ease(u)); showGhost = true; hud = true;
        cam = [[12.5, 0.1, -0.42], [11.7, 0.03, 0.21]];
        if (simT >= vtr.t12) {
          $("res-t").textContent = vtr.t12.toFixed(2) + " s";
          $("res-sub").textContent = `${(vtr.v12 * 3.6).toFixed(0)} km/h · zonder launch control ${gtr.t12.toFixed(2)} s`;
          $("result").classList.remove("hidden");
          hud = false;
        }
        title(null);
      } else if (T < 24) {                                      // S7 tyre mold
        const u = (T - 20.6) / 3.4;
        fill = ease(u / 0.6); lid = ease((u - 0.65) / 0.3);
        const mp = mold.g.position;
        cam = orbit(lerp(0.9, 1.6, u), lerp(0.2, 0.17, u), lerp(0.13, 0.1, u), [mp.x, 0.012, mp.z]);
        title("Zelf gegoten siliconen banden", "4-holtes mal · rechtstreeks op de velg · ±3 ml per band");
      } else {                                                  // S8 outro
        const u = (T - 24) / 3;
        cam = orbit(lerp(2.4, 3.2, u), lerp(0.5, 0.42, u), lerp(0.12, 0.09, u), [-0.08, 0.025, 0]);
        title(`${vtr.t12.toFixed(2)} s over 12 meter`, "simulatie · CAD · bandenmal · ESP32-S3 firmware · Pi 4 pit-station");
      }
      // apply
      setExplode(mainCar, ex);
      setMold(lid, fill);
      const s = sampleAt(vtr, simT);
      poseCar(mainCar, s, LANES[0], vtr.G, 0.04);
      ghostCar.obj.visible = showGhost;
      const gs = sampleAt(gtr, simGT);
      if (showGhost) poseCar(ghostCar, gs, LANES[1], gtr.G, 0.04);
      $("hud").classList.toggle("hidden", !hud);
      if (hud) {
        $("t").textContent = Math.min(simT, vtr.t12).toFixed(3); $("spd").textContent = (s.v * 3.6).toFixed(1);
        $("dist").textContent = Math.min(12, s.x).toFixed(2); $("amp").textContent = s.I.toFixed(1); $("vb").textContent = s.Vb.toFixed(2);
        $("duty").textContent = Math.round(s.d * 100); $("slip").textContent = Math.round(Math.min(1, s.k) * 100);
        $("slipbar").style.width = Math.min(1, s.k) * 100 + "%";
      }
      finishBeam.material.color.set(s.x >= 12 && s.x < 12.6 ? 0x22ff66 : 0xff2a2a);
      // smoke (deterministic enough: emitted per frame from the ghost while slipping)
      const sdt = dtv * slowFactor;
      if (simT > 0 && simT !== lastSmokeT) {
        if (gs.k > 0.25 && showGhost) { emitSmoke(CAR_X0 + gs.x, LANES[1] - 0.06, gs.k, sdt * 3); emitSmoke(CAR_X0 + gs.x, LANES[1] + 0.06, gs.k, sdt * 3); }
        if (s.k > 0.25) emitSmoke(CAR_X0 + s.x, LANES[0] - 0.06, s.k, sdt * 3);
      }
      if (simT === 0 || T < 10.8 || T >= 20.6) clearSmoke();
      lastSmokeT = simT;
      updateSmoke(dtv * Math.max(slowFactor, 0.35));
      camera.position.set(...cam[0]); controls.target.set(...cam[1]); camera.lookAt(controls.target);
      updateSun(cam[1][0]);
      renderer.render(scene, camera);
      return new Promise((r) => requestAnimationFrame(() => r(true)));
    },
  };
}

// ------------------------------------------------------------------ load
const loader = new GLTFLoader();
const load = (u) => new Promise((res, rej) => loader.load(u, res, (e) => {
  if (e.total) $("loadtxt").textContent = `3D-model laden… ${Math.round((e.loaded / e.total) * 100)} %`;
}, rej));
(async function init() {
  info = await (await fetch("models/parts.json")).json();
  const [carG, moldG] = await Promise.all([load("models/car.glb"), load("models/mold.glb")]);
  carTemplate = buildCar(carG.scene);
  mainCar = instance(carTemplate, false);
  ghostCar = instance(carTemplate, true);
  mold = buildMold(moldG.scene);
  setMold(0, 0);
  renderPartList();
  renderRuns();
  renderFiles();
  resize();
  resetRace();
  updateCamera(0, CAR_X0 + 0.1, true);
  $("loading").classList.add("hidden");
  window.__dbg = { mainCar, ghostCar, scene, camera };
  if (VIDEO) { videoSetup(); window.__ready = true; }
  requestAnimationFrame(frame);
})().catch((e) => { $("loadtxt").textContent = "Fout bij laden: " + e.message; console.error(e); });
