#!/usr/bin/env python3
"""SC-02 wiring diagram -> wiring_sc02.png / .svg (schemdraw)."""
import os
import schemdraw
import schemdraw.elements as elm

HERE = os.path.dirname(os.path.abspath(__file__))
schemdraw.config(fontsize=11, lw=1.4)
G = -1.4

with schemdraw.Drawing(show=False) as d:
    d.config(unit=2.4)
    bat = d.add(elm.BatteryCell().up().at((0, 0)).label("4×AA 4.8 V\nof 3S LiPo 11.1 V", loc="left"))
    d.add(elm.Line().up(0.8)); d.add(elm.Fuse().right().label("F1 10 A", loc="bottom"))
    d.add(elm.Switch().right().label("S1 (onder de vloer)", loc="bottom"))
    bus = d.add(elm.Dot().label("BUS+", loc="right", ofst=(0.1, 0.3)))
    xb, yb = bus.center
    pv = d.add(elm.Solar().up().at((-4.4, 0)).label("kit-paneel\n5.5 V 0.88 W", loc="left"))
    d.add(elm.Line().at(pv.end).toy(yb + 1.6))
    d.add(elm.Schottky().right().tox(xb).label("D1 1N5819 (regel 4.3)", loc="top")); d.add(elm.Line().toy(yb))
    d.add(elm.Line().at(pv.start).toy(G)); d.add(elm.Line().at(bat.start).toy(G))
    # shunt in the minus line -> INA226
    d.add(elm.Resistor().at((0, G)).right().label("R_s 2 mΩ\n(INA226)", loc="bottom"))
    gnd = d.add(elm.Dot().label("GND", loc="right", ofst=(0.25, -0.35)))
    d.add(elm.Line().at(pv.start + (0, G - pv.start[1]) if False else (pv.start[0], G)).tox(0))
    d.add(elm.Ground().at(gnd.center))
    xs = [xb + 2.2, xb + 6.2, xb + 10.4]
    labels = ["DRV8874 #1 → M1\n(EN GPIO4, PH GPIO5)", "DRV8874 #2 → M2\n(EN GPIO6, PH GPIO7)", "Pololu S13V30F5\n5 V 3 A buck-boost"]
    d.add(elm.Line().at((xb, yb)).tox(xs[-1]))
    for x, lab in zip(xs, labels):
        d.add(elm.Dot().at((x, yb)))
        box = d.add(elm.Ic(pins=[], size=(3.0, 1.4), label=lab, lblsize=10).anchor("center").at((x, yb - 1.9)))
        bb = box.get_bbox(transform=True)
        d.add(elm.Line().at((x, yb)).toy(bb.ymax))
        d.add(elm.Line().at((x, bb.ymin)).toy(G))
    d.add(elm.Line().at((gnd.center[0], G)).tox(xs[-1]))
    # 5 V rail
    d.add(elm.Line().at((box.get_bbox(transform=True).xmax, yb - 1.9)).right(1.2))
    r5 = d.add(elm.Dot().label("5 V", loc="top"))
    for lab, dy in (("Raspberry Pi 4 (5V pin 2/4)", 0.0), ("Servo MG90S (rood)", -1.0), ("ESP32-S3 5V-pin", -2.0)):
        d.add(elm.Line().at(r5.center).down(-dy if False else 0.0001))
        d.add(elm.Line().at((r5.center[0], r5.center[1] + dy)).right(1.0))
        d.add(elm.Dot(open=True).label(lab, loc="right", fontsize=10))
        if dy: d.add(elm.Line().at(r5.center).toy(r5.center[1] + dy))
    # signals
    y0 = G - 2.6
    sig = [("ESP GPIO17 (TX) → Pi GPIO15 RXD (pin 10)", 0), ("ESP GPIO18 (RX) ← Pi GPIO14 TXD (pin 8)", -0.7),
           ("ESP GPIO9 → servo signaal (oranje)", -1.4), ("ESP GPIO1 SDA / GPIO2 SCL → INA226", -2.1),
           ("ESP GPIO10 ← DRV5023 hall (2 magneten in het tandwiel)", -2.8), ("ESP GPIO0 = BOOT-knop: race-start", -3.5),
           ("Recon Cloud controller ⇢ Bluetooth ⇢ Pi 4 · gsm ⇢ wifi 'SC-02' ⇢ Pi 4", -4.4)]
    for txt, dy in sig:
        d.add(elm.Label().at((-4.6, y0 + dy)).label(txt, fontsize=10.5, halign="left"))
    d.add(elm.Label().at((-4.6, y0 - 5.3)).label("Alle massa's gemeenschappelijk · motor- en batterijdraden ≥ 20 AWG · S1 uit bij USB", fontsize=10, halign="left"))
    d.save(os.path.join(HERE, "wiring_sc02.svg")); d.save(os.path.join(HERE, "wiring_sc02.png"), dpi=150)
print("ok")
