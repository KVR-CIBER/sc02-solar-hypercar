/*
  Solar Olympiade 2027 - Challenger car controller (ESP32-S3 DevKitC-1)

  What it does
  - Launch control: PWM ramp from START_DUTY to 100 % over RAMP_MS (values from the simulation),
    so the silicone tyres do not spin at the start.
  - Odometry: hall sensor + 4 magnets in the front-left wheel -> distance, speed, time over 12 m.
  - Safety stop: after STOP_M metres, after TIMEOUT_MS, or when the wheel stops turning.
  - Logging: 500 Hz log (time, duty, battery voltage, wheel pulses) for the last run.
  - Test mode (Wi-Fi on): joins the pit Wi-Fi (Raspberry Pi hotspot), HTTP API + small web page.
    Race mode (Wi-Fi off): button start only, saves ~80 mA and needs no radio at the event.

  Start: hold the START button (LED yellow), let go -> car starts (after START_DELAY_MS).
  Toggle test/race mode: hold START while switching the car on (LED flashes the new mode).

  LED: blue = idle test mode, green = idle race mode, yellow = armed, red = running,
       purple = run finished (log ready), white blink = battery low.

  Wiring (see docs/wiring.md):
    GPIO4  -> MOSFET module PWM/SIG input (low-side switch of the two motors)
    GPIO5  <- START button to GND (internal pull-up)
    GPIO6  <- DRV5023 hall sensor OUT (10k pull-up to 3V3), magnets in front-left wheel
    GPIO1  <- battery voltage via 100k (top) / 47k (bottom) divider
    5V pin <- MT3608 boost module set to 5.0 V (keeps the ESP alive when the pack sags to ~2.7 V)
*/
// All code lives in car.cpp (plain C++, so the Arduino prototype generator cannot break it).
