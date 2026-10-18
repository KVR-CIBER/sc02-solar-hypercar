# SC-02 floor board (v2.0)

**The whole floor of the car is this PCB.** Same outline, same countersunk M3 holes and same Pi cooling slots as the
2 mm acrylic floor. It is a 2 mm, 4-layer board in black solder mask, and every printed part still screws on from below.
The electronics sit in the two sidepods, where the separate boards used to be. A copper strip under the battery tray
joins both pods; the rest of the floor is bare.

| Where | What |
|---|---|
| left pod (car left) | **XT60** (LiPo plugs in from above), **10 A fuse**, power switch pads, P-MOSFET reverse protection, **INA226** + 2 mOhm shunt, **TPS54560B 5 V 5 A** buck, 5V PI pads, PI UART pads, **ELRS** receiver pads, Qwiic I2C |
| right pod (car right) | **ESP32-S3** (antenna towards the side wall), **2x DRV8871** motor drivers + motor pads, hall header, servo header, solar panel + light pads, RESET/BOOT, **USB-C at the floor edge** |
| in front of the left pod | marked spot for the **RadioMaster RP2** ELRS receiver (double-sided tape) |

## Driving with the RadioMaster Pocket (ELRS)

1. Bind a **RadioMaster RP2** (ExpressLRS 2.4 GHz) to the Pocket.
2. Solder its 4 wires to the **ELRS RP2** pads: GND, 5V, TX, RX. The labels are the receiver's pins: receiver TX goes to the "TX" pad.
3. Stick it on the marked spot, away from the ESP32 on the other side of the car.
4. The ESP32 reads CRSF on **IO16 (RX) / IO15 (TX)** at 420000 baud.
5. Channels: steering = ch1, throttle = ch2/ch3 (set in the firmware). Failsafe: no CRSF frames for 300 ms gives motors off and the servo centred.

## Connections

| Pads / connector | What |
|---|---|
| **XT60** | LiPo 3S. `-` is the chamfered side of the XT60: **check this against your battery plug**. If it is reversed, the MOSFET blocks and nothing breaks. |
| **SCHAKELAAR** | the two wires of the power switch; the switch sits in the 6.2 mm hole in the floor (operated from below) |
| **MOTOR 1 / MOTOR 2** | motor leads A / B; swap them if a motor turns the wrong way |
| **HALL G V S** | A3144 hall sensor (10k pull-up on the board) |
| **SERVO G V S** | MG90S: brown GND, red 5 V, orange signal |
| **PANEEL** | solar panel - / + (only measured, on IO8) |
| **LICHT** | LED lights at 5 V, with their own resistors; switched by IO11 |
| **5V PI** | 5 V 3 A to the Pi 4: GPIO pin 2 or 4 (+5 V) and pin 6 (GND) |
| **PI UART** | GND, TXD, RXD to Pi pins 6 / 8 / 10 (1k resistors on the board) -> `/dev/serial0` on the Pi |
| **USB-C** | at the floor edge, reachable from outside through the opening in the body side: flash / debug the ESP32 from the Mac (no battery needed) |
| **I2C** (Qwiic) | 3.3 V I2C (same bus as the INA226) for an IMU or extra sensors |

## ESP32-S3 pins

| GPIO | function | GPIO | function |
|---|---|---|---|
| 4 / 5 | motor 1 IN1 / IN2 | 6 / 7 | motor 2 IN1 / IN2 |
| 9 | servo | 38 | hall sensor |
| 15 / 16 | ELRS TX / RX (CRSF) | 17 / 18 | UART TX / RX to the Pi |
| 1 / 2 | I2C SDA / SCL (INA226 + Qwiic) | 8 | solar panel voltage (x 4.03) |
| 11 | lights | 12 | yellow LED |
| 0 | BOOT = race-mode button | 19 / 20 | USB-C |

The firmware (`firmware/sc02/car.cpp`) still has to be adapted to these pins:
* DRV8871 uses IN1/IN2 instead of EN/PH;
* the hall sensor is on IO38;
* the CRSF/ELRS input is new.

## Body change

`f1/cad/build.py` cuts a 13 x 7 mm opening in the right body side at x = 118.5..131.5 mm for the USB-C plug.
The trays and the ESP bridge from the acrylic version (`power_tray_L/R`, `esp_bridge`) are no longer needed.

## Order (JLCPCB)

* 4 layers, **2.0 mm** thick, black solder mask.
* Upload `fab/sc02_drive_gerbers_JLCPCB.zip` plus the BOM + CPL; all LCSC numbers are filled in.
* The board is ~362 x 159 mm, so it costs more than a small board. It is also ~60-90 g heavier than the acrylic floor.
* **Countersunk holes:** order them as an option (all M3 holes, 90 deg, from the bottom), or use pan-head screws.
