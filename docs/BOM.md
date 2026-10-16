# Bill of materials

Prices are typical Belgian/EU web-shop prices (AliExpress, Amazon.de, bol.com, Conrad, Mini 4WD shops) in October 2026, rounded. Pack prices are listed when you can't buy a single part. The organisers refund **up to €50** (rule 1.5, keep every receipt and photo). There is also a Budget prize.

Supplied by the organisers (not in the cost): 4× AA NiMH 2000 mAh, battery holders, solar panel, DC motor, Loctite 3090.
Already owned: ESP32-S3 DevKitC-1, Raspberry Pi 4, P1S printer.

## Car

| # | Part | Qty | Price | Note / search term |
|---|---|---|---|---|
| 1 | Tamiya Hyper-Dash 3 motor (item 15477) | 2 | €17.00 | Mini 4WD motor, 130 size, 2 mm shaft. **Budget:** 2× "130 motor high speed 3V" (€3 total) |
| 2 | Brass pinion 8T, module 0.5, 2 mm bore | 2 | €2.50 | "0.5M 8T brass pinion 2mm" (pack of 10) |
| 3 | Spur gear 42T m0.5 | 1 | €0 | printed (PLA, fine profile). Or a POM "0.5M 42T 3mm bore" for about €1 |
| 4 | Ball bearing 683ZZ (3×7×3 mm) | 4 | €3.50 | pack of 10 |
| 5 | Carbon rod Ø3 mm × 500 mm | 1 | €2.50 | cut 2× 132 mm. A Ø3 mm silver-steel rod also fits (+12 g) |
| 6 | Neodymium magnet 3×2 mm | 4 | €2.50 | pack of 50, all with the same pole facing the sensor |
| 7 | Screws M2×8 self-tapping (16), M3×6 (3) | – | €3.00 | bearing caps, motor clamp, front carrier |
| 8 | Zip ties 2.5 mm | 10 | €1.00 | battery holders, ESP |

## Electronics

| # | Part | Qty | Price | Note |
|---|---|---|---|---|
| 9 | MOSFET module "D4184 dual MOS trigger switch" | 1 | €1.50 | low-side switch, works with a 3.3 V PWM input |
| 10 | MT3608 boost module (set to 5.0 V) | 1 | €3.00 | pack of 5. Keeps the ESP alive when the pack sags to 2.7 V |
| 11 | DRV5023 hall sensor (TO-92) | 1 | €1.50 | works at 3.3 V. **A3144 does not**, it needs 4.5 V |
| 12 | Schottky 1N5819 (panel diode, rule 4.3) + SS34 (flyback) | 1+1 | €1.00 | |
| 13 | Mini blade fuse holder + 10 A fuse | 1 | €1.50 | rule 5.7 recommends a fuse |
| 14 | Mini toggle switch MTS-102 (6 mm hole) | 1 | €0.80 | power |
| 15 | Push button, 7 mm hole | 1 | €0.50 | START |
| 16 | Resistors 100k, 47k, 10k; capacitor 470 µF 10 V | – | €1.00 | |
| 17 | Silicone wire 20 AWG red/black, 1 m each | – | €2.50 | |

## Tyres

| # | Part | Qty | Price | Note |
|---|---|---|---|---|
| 18 | Silicone casting rubber, Shore A 20–30, 1:1 | 250 g | €15.00 | You need about 15 ml per set of 4. Platinum (addition-cure) gives the best grip. Tin-cure also works and never cure-inhibits on PLA |
| 19 | Luer-slip syringe 10 ml (no needle) | 3 | €1.50 | fits the mold's gates |
| 20 | Mold release | – | €0 | thin layer of vaseline, or dish soap and dry |

## Filament (Bambu P1S, sliced, see `cad/out/print/print_report.json`)

| Plate | Material | Grams | Time | Cost |
|---|---|---|---|---|
| 1 car (chassis, front carrier, clamp, panel frame, 4 caps) | ASA | 55 g | 2 h 36 | €1.40 |
| 2 wheels (5 rims, 2 spur gears, 6 spacers) | PLA | 21 g | 1 h 28 | €0.40 |
| 3 tyre mold (base + lid) | PLA | 121 g | 2 h 38 | €2.40 |
| 4 *option* TPU tyres | TPU 95A | 15 g | 1 h 00 | €0.50 |
| 5 *option* rims for TPU tyres | PLA | 13 g | 0 h 44 | €0.30 |

## Pit / timing station

| # | Part | Qty | Price | Note |
|---|---|---|---|---|
| 21 | IR break-beam sensor pair 5 mm | 1 | €3.00 | finish gate on Pi GPIO17 |
| 22 | Dupont jumpers, 2 m 3-core cable | – | €1.00 | |

## Totals

| Version | What changes | Total |
|---|---|---|
| **Full** (as designed) | Tamiya Hyper-Dash 3 ×2, silicone tyres | **≈ €70** |
| **Budget** (fits the €50 refund) | generic 130 motors (−€14), TPU tyres instead of silicone (−€16.50, no mold plate) | **≈ €38** |

The budget motors are slower. The simulation for 2× generic FA-130 gives 2.65 s with the 42T spur, or **2.54 s with a 30T spur** (set `SPUR_Z = 30` in `cad/params.py` and rebuild; the motor cradles move automatically). The full version does 2.33 s. TPU grips less than soft silicone, so expect a little more on top of that. Buy one pair of Tamiya motors first, measure them (docs/motor_measurement.md), and only then decide.
