# Build guide

Order: **test prints → print everything → cast tyres → mechanics → electronics → firmware → calibrate → tune on the pit station.**

## 0. Before you print: two test pieces (15 min)

Fits depend on your printer and filament. Print these first and adjust `cad/params.py`, then run `build.py` again.

| Test | Print | Good when | Adjust |
|---|---|---|---|
| Bearing fit | 1× `bearing_cap.stl` + a chassis corner (or just print the chassis) | a 683ZZ drops into the U-slot with light finger pressure and doesn't wobble | `BRG_FIT` (7.05–7.12) |
| Axle press fit | 1× `rim_silicone.stl` | the 3 mm rod goes in with firm pressure (pliers/vise), can't be turned by hand | `PRESS_BORE` (2.85–2.95) |
| Motor | chassis | the motor drops into its cradle without force | `MOT_FIT` |

Also **measure the kit battery holders and the panel thickness** and set `BATT_HOLDER` and `PANEL_T`.

## 1. Printing (Bambu P1S, 0.4 nozzle)

Open the ready-made projects in `cad/out/print/` (`*.3mf`) in Bambu Studio, check them, and print. All parts are already oriented so they need **no supports**.

| Plate | Material | Why this material | Profile |
|---|---|---|---|
| 1 car | **ASA** (or ABS) | 14 % lighter than PLA, stays stiff next to warm motors and in a sunny car park. P1S: close the door, no fan for the first layers | 0.20 mm, 3 walls, 20 % infill |
| 2 wheels + spur | **PLA** | stiffest and most accurate → round wheels, tight press fit, clean m0.5 gear teeth | 0.12 mm, 3 walls, 25 % infill |
| 3 tyre mold | **PLA** (PETG also OK) | dimensionally accurate. Silicone does not stick to it if you use release agent | 0.20 mm |
| 4 TPU tyres *(option)* | **TPU 95A** | no casting needed, but less grip than soft silicone | 0.20 mm, slow (default TPU profile) |

Tips:
- **Spur gear m0.5** is at the limit of a 0.4 nozzle. Print 2 and use the best one. If the teeth are blobby, buy a POM 0.5M 42T gear (about €1) or print it with a 0.2 nozzle.
- Rims print **web-side down**, so the band and hub grow upwards and come out round.

## 2. Cast the silicone tyres (overmolded onto the rims)

The tyre is cast **directly onto the printed rim**. The dovetail rib + 12 notches on the rim lock the silicone so it cannot slip or roll off.

1. Clean the mold with soap and dry it. Wipe a **very thin** layer of vaseline on the cavity walls, the floor and the underside of the lid. Do **not** grease the rim band (the silicone must grip the rim).
2. Place a rim **outer face down** in each cavity. It drops over the centring ring, which makes the tyre concentric. The magnet side (inner face) points up.
3. Put the lid on (the pins locate it) and tighten the 5× M3 bolts + nuts evenly. Binder clips also work.
4. Mix the silicone (follow the label, usually 1:1 by weight). Stir slowly for 2 min, scraping the cup walls. You need **≈ 3 ml per tyre, mix 20 ml**.
5. Fill a 10 ml Luer syringe. Push it into a **gate on the side of the mold** and inject **slowly**. The silicone fills the cavity from the bottom and pushes the air out of the 4 vents in the lid. Stop when silicone appears in **all 4 vent cups**. Do the next cavity.
6. Leave it flat for the full cure time (often 4–24 h, warmth speeds it up). Platinum silicone: if the surface stays sticky against the PLA, seal the mold once with clear lacquer, or use tin-cure silicone.
7. Open the mold and push each wheel out from below through the centre hole (use the axle rod). Cut off the gate stub and the vent stalks with a sharp knife.
8. Check: tyre surface smooth, no big bubbles at the tread. A small bubble on a side face is OK.

TPU option: print `tyre_tpu.stl` (plate 4) and glue it onto `rim_tpu` (plate 5) with the kit's Loctite 3090.

## 3. Mechanics

1. **Axles**: cut the 3 mm carbon rod into 2× 132 mm (fine saw or a Dremel cut-off disc, wear a mask: carbon dust). Lightly chamfer the ends.
2. **Magnets**: push 4 magnets into the pockets on the inner face of **one front wheel** (front-left), **all with the same pole up**. A drop of glue on each.
3. **Front axle**: wheel – spacer – bearing (in the carrier) – … – bearing – spacer – wheel. Press the first wheel on, slide the axle through the bearings and spacers, then press the second wheel on until the axle has **0.2–0.3 mm end play** (it must spin freely for > 5 s when flicked).
4. **Rear axle**: same, but slide the **spur gear** on first and position it so it lines up with the pinions (centre at y = −10 mm, see the render). Glue it with Loctite 3090 once the mesh is checked.
5. Close the bearing slots with the **bearing caps** (2× M2×8 each). Don't over-tighten.
6. **Motors**: press an 8T brass pinion onto each motor shaft until the pinion is flush with the shaft end (use a vise, support the motor's rear shaft end, never hammer). Drop the motors into the cradles, with the motor face against the front wall. Fit the **motor clamp** (4× M2×8).
7. **Mesh check**: turn the rear wheels by hand. You should feel a tiny bit of play between the teeth and no tight spot over a full turn. If it's tight, add one layer of tape under the clamp pads, or rebuild with `BACKLASH_CD` + 0.05.
8. **Front carrier**: screw it on from below (M3×6 in the centre + 2 in the slots). Leave the slot screws slightly loose for alignment (step 7 of the calibration).
9. Battery holders into the bay (zip ties through the slots). Panel frame on the four posts (a drop of glue on the pins). Lay the panel in and hold it with two elastic bands in the grooves (no drilling or gluing on the panel, rule 4.5).
10. Stick the **team stickers on both side walls** (rule: left and right).

## 4. Electronics

See [wiring.md](wiring.md) and `wiring.png`.

- Power path: holders (series) → **fuse** → **switch** → BUS+. Keep it short, 20 AWG.
- **Panel → 1N5819 → BUS+** (the stripe on the diode points to BUS+). Mandatory, rule 4.3.
- Motors in parallel, **both turning the same way** (check with the car on a stand before gluing anything). SS34 flyback diode across the motors, stripe to BUS+.
- MOSFET module: V+/V− (or "DC+ / DC−") to the motors' minus side and GND, PWM/SIG to GPIO4, GND to ESP GND.
- MT3608: **set it to 5.0 V with a multimeter BEFORE connecting the ESP** (turn the small pot), then OUT+ → ESP 5V pin.
- Hall sensor DRV5023 in the holder on the front carrier, flat face toward the wheel magnets, 1 mm gap.
- ESP32-S3 with zip ties on the electronics bay. Switch and START button in the dash.

## 5. Firmware

```bash
arduino-cli compile -b esp32:esp32:esp32s3:CDCOnBoot=cdc firmware/solar_car
arduino-cli upload  -b esp32:esp32:esp32s3:CDCOnBoot=cdc -p /dev/cu.usbmodem* firmware/solar_car
```
**Switch the car off (S1) while USB is plugged in**, and put the car on a stand (wheels free) for the first test.
Serial monitor (115200): `g` = go, `s` = stop, `d` = dump the log.

## 6. Calibration

1. **Motor direction**: car on a stand, `g` in the serial monitor. The rear wheels must turn forward. If not, swap both motor wires.
2. **Distance per pulse** (`mm_per_pulse`, default 31.42): push the car slowly over exactly 2.00 m, read `pulses` on the status page, then set `mm_per_pulse = 2000 / pulses`.
3. **Straight line**: do 3 slow runs (start duty 0.4, ramp 0) on the real floor. If it drifts left, rotate the front carrier slightly clockwise (seen from above) in its slots, and vice versa. Tighten the screws. Also check that both rear tyres have the same diameter (± 0.1 mm).
4. **Launch control** with the pit station: start at the simulated values (start duty 0.45, ramp 350 ms). Then vary one at a time (±0.1 duty, ±100 ms) and keep the fastest. Each run is stored, and the page overlays the simulation.

## 7. Race-day checklist

- [ ] Cells charged the evening before (simulation: fresh 5.2 V pack 2.33 s, rested 4.9 V pack 2.42 s)
- [ ] Car in **race mode** (hold START while switching on until the LED flashes green; Wi-Fi off)
- [ ] Tyres clean (wipe with a damp cloth; dust kills grip)
- [ ] Fuse in, switch on, LED green
- [ ] Spare: fuse, pinion, rim + tyre, bearing caps, screws, Loctite
- [ ] To start: hold START (LED yellow), let go → go. Pressing START while running = stop.
- [ ] Hand back the panel + cells + holders at the end of the day (rule 1.7)
