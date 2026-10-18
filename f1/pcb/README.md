# SC-02 drive board (v1.0)

4-layer board that sits **on top of the Raspberry Pi 4 like a HAT**: 2x20 socket underneath on the Pi header,
4x M2.5 on the Pi 4 holes (58 x 49). It replaces the ESP32 DevKit bridge, both DRV8871 modules, the LM2596 and the
INA226 module of SC-02 - one board, a few solder pads, done.

| Block | Part | What it does |
|---|---|---|
| Brain | **ESP32-S3-WROOM-1-N16R8** | motors, steering, hall sensor, race mode; antenna hangs over the edge |
| Motors | 2x **DRV8871** | IN1/IN2 (forward / reverse / brake / coast), current limit 3.55 A each (R_ILIM 18k) |
| Battery | 3S LiPo pads, P-MOSFET reverse protection, TVS, 100 uF | |
| Measure | **INA226** + 2 mOhm shunt (I2C 0x40) | battery voltage + current (-> consumption in the app) |
| 5 V | TI **TPS54560B** buck, 5 V 5 A | Pi 4 (via header pins 2/4), servo, hall, lights |
| Pi link | UART + reset/boot lines | the Pi can talk to **and reflash** the ESP32 |
| Extra | servo header, hall header, Qwiic I2C, solar-panel ADC, light output, USB-C | |

Board: **65 x 70 mm**, 1.6 mm, 4 layers (F signals / In1 GND / In2 battery bus / B signals + 5 V band). The 14 mm
past the Pi's HDMI edge carries the ESP32 and the USB-C. A slot above the Pi's CSI connector lets the camera flex through.

## Connections

| Where | What |
|---|---|
| **BAT 3S** (left, big pads) | XT60 lead via the 10 A fuse and switch: BAT- / BAT+ |
| **MOTOR 1 / MOTOR 2** (left) | motor leads, A / B (swap A/B if a motor turns the wrong way) |
| **SERVO** (right) | MG90S: G (brown) V (red) S (orange) |
| **HALL** (bottom left) | A3144: G V S, 10k pull-up on the board |
| **ZONNEPANEEL** | panel - / + (measured on IO8, 100k/33k, nothing is charged) |
| **LICHTEN** | - / + : LED lights at 5 V (with their own resistors), switched by IO11 |
| **I2C** (Qwiic) | 3V3 I2C for an IMU or extra sensors (same bus as the INA226) |
| **USB-C** | flash / debug the ESP32 from the Mac (no battery needed) |

## ESP32-S3 pins

| GPIO | function | GPIO | function |
|---|---|---|---|
| 4 / 5 | motor 1 IN1 / IN2 | 6 / 7 | motor 2 IN1 / IN2 |
| 9 | servo | 10 | hall sensor |
| 1 / 2 | I2C SDA / SCL (INA226 + Qwiic) | 8 | solar panel voltage (x 4.03) |
| 11 | lights | 12 | yellow LED |
| 17 / 18 | UART TX / RX to the Pi (GPIO15 / GPIO14) | 0 | BOOT = race-mode button |

**Firmware:** `firmware/sc02/car.cpp` still uses the old DRV8874 EN/PH pins. It has to switch to DRV8871
IN1/IN2 (forward: IN1 = PWM, IN2 = 0; reverse: the other way round; brake: both high; coast: both low).

**Pi:** UART on `/dev/serial0` as before. Pi GPIO4 (pin 7) resets the ESP32 and Pi GPIO17 (pin 11) holds BOOT,
so `esptool` on the Pi can flash it without a USB cable.

## Power

The board feeds the Pi's 5 V pins directly (5 A buck). **Don't plug the Pi's own USB-C supply in at the same time.**
On USB only (no battery) the ESP32 runs from USB; the Pi, motors and servo stay off.

## Files

| File | |
|---|---|
| `sc02_drive.kicad_pro / .kicad_sch / .kicad_pcb` | open in KiCad 10 |
| `fab/` | gerbers zip, BOM + CPL with LCSC numbers (JLCPCB), schematic PDF, renders |
| `tools/design.py` | single source of truth: every part, net and position |
| `tools/build_all.sh` | regenerates everything (same toolchain as the ARACHNE boards) |

## To check before ordering

* The camera slot position (`CAM_SLOT` in design.py) is taken from the Pi 4 drawing (CSI at x 45 mm): hold the board
  on the Pi once and check.
* Fit in the body: the board sits ~11 mm above the Pi (stacking socket). The old ESP bridge sat higher, so it should fit,
  but the CAD (`f1/cad/car.py`) does not include this board yet.
