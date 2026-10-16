#!/usr/bin/env python3
"""Draws docs/wiring.png + wiring.svg (schemdraw). Pin map for the ESP32-S3 is in docs/wiring.md."""
import os
import schemdraw
import schemdraw.elements as elm

HERE = os.path.dirname(os.path.abspath(__file__))
schemdraw.config(fontsize=11, lw=1.4)
GND_Y = -1.2

with schemdraw.Drawing(show=False) as d:
    d.config(unit=2.4)
    # battery -> fuse -> switch -> BUS+
    bat = d.add(elm.BatteryCell().up().at((0, 0)).label("4x AA NiMH\n4.8 V in series\n(kit holders)", loc="left"))
    d.add(elm.Line().up(0.8))
    d.add(elm.Fuse().right().label("F1 10 A", loc="bottom"))
    d.add(elm.Switch().right().label("S1 power", loc="bottom"))
    busA = d.add(elm.Dot().label("BUS+", loc="right", ofst=(0.1, 0.3)))
    x_bus = busA.center[0]; y_bus = busA.center[1]

    # solar panel -> mandatory diode -> BUS+
    pv = d.add(elm.Solar().up().at((-4.2, 0)).label("kit solar panel\n5.5 V / 0.88 W", loc="left"))
    d.add(elm.Line().at(pv.end).toy(y_bus + 1.6))
    d.add(elm.Schottky().right().tox(x_bus).label("D1 1N5819  (rule 4.3: no back-feed into the panel)", loc="top"))
    d.add(elm.Line().toy(y_bus))
    d.add(elm.Line().at(pv.start).toy(GND_Y))
    d.add(elm.Line().at(bat.start).toy(GND_Y))

    xs = {}
    def bus_to(x):
        d.add(elm.Line().at((x_bus if not xs else max(xs.values()), y_bus)).tox(x))
        xs[len(xs)] = x
        return d.add(elm.Dot())

    # bulk cap
    nB = bus_to(x_bus + 1.6)
    d.add(elm.Capacitor(polar=True).down().at(nB.center).label("C1 470 µF 10 V", loc="bottom").toy(GND_Y))

    # motors + flyback + MOSFET (low side)
    nC = bus_to(x_bus + 5.0)
    d.add(elm.Line().at(nC.center).down(0.5))
    top = d.add(elm.Dot())
    d.add(elm.Line().left(1.6))
    dfly = d.add(elm.Schottky().down().reverse().label("D2 SS34\nflyback", loc="left"))
    d.add(elm.Line().at(top.center).down(0.0001))
    m1 = d.add(elm.Motor().down().at(top.center).label("M1", loc="right"))
    d.add(elm.Line().at(top.center).right(1.6))
    m2 = d.add(elm.Motor().down().label("M2", loc="right"))
    d.add(elm.Line().at(m2.end).tox(m1.end))
    bot = d.add(elm.Dot().at(m1.end))
    d.add(elm.Line().at(dfly.end).tox(bot.center))
    q = d.add(elm.NFet().anchor("drain").at(bot.center).reverse().label("Q1  D4184\nMOSFET module", loc="right"))
    d.add(elm.Line().at(q.source).toy(GND_Y))
    d.add(elm.Line().at(q.gate).left(0.9))
    d.add(elm.Dot(open=True).label("ESP GPIO4\n(PWM 20 kHz)", loc="left", fontsize=10))

    # voltage divider
    nD = bus_to(x_bus + 9.0)
    d.add(elm.Resistor().down().at(nD.center).label("R1 100k", loc="right"))
    mid = d.add(elm.Dot())
    d.add(elm.Resistor().down().label("R2 47k", loc="right").toy(GND_Y))
    d.add(elm.Line().at(mid.center).left(0.9))
    d.add(elm.Dot(open=True).label("ESP GPIO1\n(ADC)", loc="left", fontsize=10))

    # boost converter feed
    nE = bus_to(x_bus + 12.0)
    d.add(elm.Line().down(0.9).at(nE.center))
    d.add(elm.Dot(open=True).label("MT3608 VIN  (VOUT 5.0 V -> ESP 5V pin,\nGND -> GND)", loc="right", fontsize=10))

    # ground rail
    d.add(elm.Line().at((pv.start[0], GND_Y)).tox(x_bus + 12.0))
    d.add(elm.Ground().at((bat.start[0], GND_Y)))

    # sensor block (3V3 side)
    y0 = GND_Y - 2.4
    d.add(elm.Dot(open=True).at((0, y0)).label("ESP 3V3", loc="left", fontsize=10))
    d.add(elm.Line().right(1.2)); n3 = d.add(elm.Dot())
    d.add(elm.Resistor().down().label("R3 10k", loc="right"))
    nh = d.add(elm.Dot())
    d.add(elm.Line().left(1.2)); d.add(elm.Dot(open=True).label("ESP GPIO6", loc="left", fontsize=10))
    d.add(elm.Line().at(nh.center).right(2.2))
    d.add(elm.Dot(open=True).label("DRV5023 OUT", loc="right", fontsize=10))
    d.add(elm.Line().at(n3.center).right(2.2))
    d.add(elm.Dot(open=True).label("DRV5023 VCC  (GND pin -> GND)", loc="right", fontsize=10))
    d.add(elm.Dot(open=True).at((11.0, y0 - 1.2)).label("ESP GPIO5", loc="left", fontsize=10))
    d.add(elm.Button().right().label("START"))
    d.add(elm.Ground().right())

    d.add(elm.Label().at((-4.5, y0 - 3.8)).label(
        "Hall sensor faces the 4 magnets in the front-left wheel (1 mm gap).  Switch S1 off before plugging in USB.\n"
        "Motor + battery wires >= 20 AWG and short.  All grounds common.",
        fontsize=10, halign="left"))
    d.save(os.path.join(HERE, "wiring.svg"))
    d.save(os.path.join(HERE, "wiring.png"), dpi=150)
print("ok")
