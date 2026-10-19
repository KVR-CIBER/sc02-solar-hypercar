# SC-02 drive board (v3.0)

A **compact 86 x 90 mm board on 4x M3 standoffs**, with the 3S LiPo on top of it. No Raspberry Pi anymore, a **built-in
ExpressLRS 2.4 GHz receiver** for the RadioMaster Pocket, and a real **solar-panel connector**.
(v2 was the whole car floor; that is gone: the car floor goes back to the 2 mm acrylic / printed floor.)

| Block | Parts |
|---|---|
| Power (unchanged from v2) | **XT60**, 10 A fuse, power switch pads, P-MOSFET reverse protection, **INA226** + 2 mOhm shunt, **TPS54560B 5 V 5 A** buck |
| Car brain | **ESP32-S3-WROOM-1** (antenna at the bottom edge), USB-C at the edge, RESET / BOOT |
| Motor | **one brushless 2435 4500 KV + 40 A ESC** (11:35). The ESC takes its power straight from the battery (Y-cable on the XT60); this board only sends the throttle signal (**ESC** header, IO4) and reads a 10k NTC on the ESC/motor (**ESC TEMP**, IO5) for the boost limit |
| **ExpressLRS receiver** | **ESP32-C3-MINI-1** + **Ebyte E28-2G4M12S** (SX1280, 12.5 dBm, PCB antenna at the right edge), own 3.3 V LDO, RGB status LED, BIND button |
| Connectors | servo (MG90S), hall (A3144), lights (switched 5 V), **solar panel JST-XH 2-pin**, Qwiic I2C |

Checks: **DRC 0, unconnected 0, ERC 0, schematic parity 0.** JLC BOM/CPL in `fab/` with LCSC numbers.

## ExpressLRS: flashing and binding
The receiver is wired exactly like ExpressLRS' **"Generic C3 2400"** target (SCK 6, MOSI 4, MISO 5, NSS 7, BUSY 3, DIO1 1,
RST 2, LED 8, button 9, CRSF on 20/21), so the normal ExpressLRS firmware runs on it, no custom layout needed.
1. First flash: ExpressLRS Configurator -> target **Generic C3 2400 RX**, flash method **WiFi** or via the **RX USB** pads
   (D-, D+, GND: a cut USB cable) while holding **BIND** at power-on.
2. Bind with the Pocket (binding phrase, or press BIND 3x).
3. CRSF goes to the car ESP32-S3: C3 TX -> **IO16**, S3 **IO15** -> C3 RX (420000 baud). The S3 can reset the receiver
   (**IO17** -> EN) and start its bootloader (**IO18** -> IO9), so later updates can go through the car's USB-C.
Tip: keep the S3's own WiFi off while driving (same 2.4 GHz band).

## Solar panel
JST-XH 2-pin (**-** / **+**), voltage on IO8 (x 4.03). Solder jumper **JP1 (ZON>5V)**, open by default: closed, the panel
helps the 5 V rail through a Schottky diode. Only close it with a panel whose open-circuit voltage is at most 6 V.

## ESP32-S3 pins
| GPIO | | GPIO | |
|---|---|---|---|
| 4 | ESC throttle (servo PWM / DShot) | 5 | ESC/motor NTC (ADC) |
| 9 | servo | 38 | hall |
| 15 / 16 | CRSF TX / RX (receiver) | 17 / 18 | receiver EN / BOOT |
| 1 / 2 | I2C SDA / SCL (INA226 0x40 + Qwiic) | 8 | solar panel voltage |
| 11 | lights | 12 | yellow LED |

## Still to do
* Car CAD: floor back to acrylic + 4 standoff holes for this board, battery tray on top, USB-C opening at the new place.
* Firmware `car.cpp`: ESC on IO4 (with arming), CRSF on IO15/16, boost on CH5 with the NTC temperature limit, hall IO38.
* ESC wiring: XT60 Y-cable battery -> ESC + this board; do NOT connect the ESC's red BEC wire to the board.
