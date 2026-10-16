/*
  SC-02 Solar Hypercar – ESP32-S3 DevKitC-1 low-level controller.
  All code lives in car.cpp (plain C++; the Arduino prototype generator breaks on lambdas).

  Pins
    GPIO4  -> DRV8874 #1 EN (PWM)      GPIO5 -> DRV8874 #1 PH (direction)
    GPIO6  -> DRV8874 #2 EN (PWM)      GPIO7 -> DRV8874 #2 PH (direction)
    GPIO9  -> steering servo signal (MG90S, 50 Hz)
    GPIO10 <- DRV5023 hall sensor (2 magnets in the spur gear), 10k pull-up to 3V3
    GPIO1  -> INA226 SDA, GPIO2 -> INA226 SCL (0x40, 2 mOhm shunt in the battery minus line)
    GPIO17 -> Pi RX (GPIO15, pin 10)   GPIO18 <- Pi TX (GPIO14, pin 8)   + common GND
    GPIO0  <- BOOT button = race start (hold, release -> go)
*/
