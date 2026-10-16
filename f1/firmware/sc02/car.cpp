#include <Arduino.h>
#include <Wire.h>
#include <Preferences.h>

// ------------------------------------------------------------------ pins
static const int EN1 = 4, PH1 = 5, EN2 = 6, PH2 = 7, SERVO = 9, HALL = 10, SDA_P = 1, SCL_P = 2, TXD = 17, RXD = 18, BTN = 0;

// ------------------------------------------------------------------ settings (flash, editable with "C,key=value")
struct Cfg {
  float vMotorMax = 4.8f;      // V average on the motors (130 motors). AA pack: no effect. 3S LiPo: PWM is capped.
  int servoCenter = 1500;      // us
  int servoSpan = 420;         // us for full lock (about 20 deg at the wheels)
  bool servoReverse = false;
  float steerRate = 6.0f;      // full-lock sweeps per second
  bool tc = true;              // traction control
  float launchD0 = 0.45f;      // race mode launch: start duty
  int launchRampMs = 350;
  float raceStopM = 14.0f;     // race mode: coast after this distance
  float mmPerPulse = 69.1f;    // spur sits on the rear axle: 2 magnets -> pi*44 mm / 2 per pulse (calibrate!)
  int failsafeMs = 300;
} cfg;
Preferences prefs;

// ------------------------------------------------------------------ state
volatile uint32_t pulses = 0, lastPulseUs = 0, pulsePeriodUs = 0;
float cmdThr = 0, cmdSteer = 0, cmdBrake = 0;      // from the Pi (-1..1, -1..1, 0..1)
uint32_t lastCmdMs = 0;
float steerOut = 0, dutyOut = 0;
float vbus = 0, ibat = 0, pmotorEst = 0, speedMs = 0, wheelAcc = 0;
enum Mode { DRIVE, RACE_ARMED, RACE_RUN, RACE_DONE } mode = DRIVE;
uint32_t raceT0 = 0;
uint32_t racePulses0 = 0;
float raceT12 = NAN;

// ------------------------------------------------------------------ INA226 (minimal driver)
static const uint8_t INA = 0x40;
static const float SHUNT = 0.002f, I_LSB = 0.001f;   // 1 mA/bit
bool inaOk = false;
void inaWrite(uint8_t reg, uint16_t v) { Wire.beginTransmission(INA); Wire.write(reg); Wire.write(v >> 8); Wire.write(v & 0xFF); Wire.endTransmission(); }
int16_t inaRead(uint8_t reg) {
  Wire.beginTransmission(INA); Wire.write(reg); if (Wire.endTransmission(false) != 0) return 0;
  Wire.requestFrom((int)INA, 2); if (Wire.available() < 2) return 0;
  return (int16_t)((Wire.read() << 8) | Wire.read());
}
void inaBegin() {
  Wire.begin(SDA_P, SCL_P, 400000);
  Wire.beginTransmission(INA); inaOk = Wire.endTransmission() == 0;
  if (!inaOk) return;
  inaWrite(0x00, 0x4127 | (0b001 << 9));                    // avg 4, 1.1 ms conversions, continuous
  inaWrite(0x05, (uint16_t)(0.00512f / (I_LSB * SHUNT)));    // calibration
}
void inaPoll() {
  if (!inaOk) return;
  vbus = (uint16_t)inaRead(0x02) * 1.25e-3f;
  ibat = inaRead(0x04) * I_LSB;
}

// ------------------------------------------------------------------ outputs
void motors(float d) {             // -1..1 ; brake = both low-side (EN=0 with DRV8874 PH/EN mode -> brake)
  d = constrain(d, -1.0f, 1.0f);
  int pwm = (int)(fabsf(d) * 1023);
  digitalWrite(PH1, d >= 0 ? HIGH : LOW); digitalWrite(PH2, d >= 0 ? HIGH : LOW);
  ledcWrite(EN1, pwm); ledcWrite(EN2, pwm);
}
void servoWrite(float s) {         // -1..1 (positive = left)
  if (cfg.servoReverse) s = -s;
  int us = cfg.servoCenter + (int)(s * cfg.servoSpan);
  ledcWrite(SERVO, (uint32_t)((uint64_t)us * 16383 / 20000));
}
void IRAM_ATTR hallIsr() {
  uint32_t now = micros(), dt = now - lastPulseUs;
  if (dt < 400) return;
  pulsePeriodUs = dt; lastPulseUs = now; pulses++;
}

// ------------------------------------------------------------------ config
void loadCfg() {
  prefs.begin("sc02", true);
  cfg.vMotorMax = prefs.getFloat("vmax", cfg.vMotorMax); cfg.servoCenter = prefs.getInt("sc", cfg.servoCenter);
  cfg.servoSpan = prefs.getInt("ss", cfg.servoSpan); cfg.servoReverse = prefs.getBool("sr", cfg.servoReverse);
  cfg.tc = prefs.getBool("tc", cfg.tc); cfg.launchD0 = prefs.getFloat("d0", cfg.launchD0);
  cfg.launchRampMs = prefs.getInt("ramp", cfg.launchRampMs); cfg.mmPerPulse = prefs.getFloat("mmpp", cfg.mmPerPulse);
  prefs.end();
}
void saveCfg() {
  prefs.begin("sc02", false);
  prefs.putFloat("vmax", cfg.vMotorMax); prefs.putInt("sc", cfg.servoCenter); prefs.putInt("ss", cfg.servoSpan);
  prefs.putBool("sr", cfg.servoReverse); prefs.putBool("tc", cfg.tc); prefs.putFloat("d0", cfg.launchD0);
  prefs.putInt("ramp", cfg.launchRampMs); prefs.putFloat("mmpp", cfg.mmPerPulse);
  prefs.end();
}
void setKey(const String &k, const String &v) {
  if (k == "vmax") cfg.vMotorMax = constrain(v.toFloat(), 1.0f, 8.0f);
  else if (k == "center") cfg.servoCenter = constrain(v.toInt(), 1000, 2000);
  else if (k == "span") cfg.servoSpan = constrain(v.toInt(), 100, 600);
  else if (k == "reverse") cfg.servoReverse = v.toInt() != 0;
  else if (k == "tc") cfg.tc = v.toInt() != 0;
  else if (k == "d0") cfg.launchD0 = constrain(v.toFloat(), 0.1f, 1.0f);
  else if (k == "ramp") cfg.launchRampMs = constrain(v.toInt(), 0, 2000);
  else if (k == "mmpp") cfg.mmPerPulse = v.toFloat();
  saveCfg();
}

// ------------------------------------------------------------------ Pi link
HardwareSerial &Pi = Serial1;
String rx;
void handleLine(const String &l) {
  if (l.startsWith("D,")) {                  // D,thr,steer,brake   (x1000)
    int a = l.indexOf(',', 2), b = l.indexOf(',', a + 1);
    cmdThr = constrain(l.substring(2, a).toInt() / 1000.0f, -1.0f, 1.0f);
    cmdSteer = constrain(l.substring(a + 1, b).toInt() / 1000.0f, -1.0f, 1.0f);
    cmdBrake = constrain(l.substring(b + 1).toInt() / 1000.0f, 0.0f, 1.0f);
    lastCmdMs = millis();
  } else if (l.startsWith("C,")) {
    int e = l.indexOf('=');
    if (e > 2) setKey(l.substring(2, e), l.substring(e + 1));
  } else if (l == "RACE") { mode = RACE_ARMED; }
  else if (l == "DRIVE") { mode = DRIVE; }
}
void pollPi() {
  while (Pi.available()) {
    char c = Pi.read();
    if (c == '\n') { rx.trim(); if (rx.length()) handleLine(rx); rx = ""; }
    else if (rx.length() < 80) rx += c;
  }
}

// ------------------------------------------------------------------ control loop (500 Hz)
void control(float dt) {
  uint32_t now = millis();
  // wheel speed from the spur magnets (rear wheels, includes wheelspin)
  uint32_t per = pulsePeriodUs, age = micros() - lastPulseUs;
  float v = (per > 0 && age < 250000) ? (cfg.mmPerPulse / 1000.0f) / (per * 1e-6f) : 0.0f;
  wheelAcc = 0.9f * wheelAcc + 0.1f * ((v - speedMs) / dt);
  speedMs = v;
  float thr = 0, steer = 0, brake = 0;
  bool link = now - lastCmdMs < (uint32_t)cfg.failsafeMs;
  if (mode == DRIVE) {
    if (link) { thr = cmdThr; steer = cmdSteer; brake = cmdBrake; }
    else { thr = 0; brake = 1; }                          // failsafe: stop
  } else if (mode == RACE_RUN) {
    float t = (now - raceT0) / 1000.0f;
    thr = cfg.launchRampMs ? min(1.0f, cfg.launchD0 + (1 - cfg.launchD0) * t * 1000 / cfg.launchRampMs) : 1.0f;
    steer = link ? cmdSteer : 0;                          // optional steering correction from the Pi
    float dist = (pulses - racePulses0) * cfg.mmPerPulse / 1000.0f;
    if (isnan(raceT12) && dist >= 12.0f) raceT12 = t;
    if (dist >= cfg.raceStopM || t > 6) { mode = RACE_DONE; }
  } else { thr = 0; brake = 0.6f; }
  // traction control: wheel can't physically accelerate faster than ~1.2 g -> it is spinning
  static float tcGain = 1.0f;
  if (cfg.tc && fabsf(thr) > 0.05f && wheelAcc > 12.0f) tcGain = max(0.35f, tcGain - 4.0f * dt);
  else tcGain = min(1.0f, tcGain + 2.0f * dt);
  // motor voltage cap (3S LiPo -> keep the 130 motors at their happy voltage)
  float cap = (vbus > 1.0f) ? min(1.0f, cfg.vMotorMax / vbus) : 1.0f;
  float d = (brake > 0.05f && fabsf(thr) < 0.05f) ? 0.0f : thr * tcGain * cap;
  dutyOut = d;
  motors(d);
  // speed-sensitive steering limit (same as the simulation): less lock at speed -> no spin-outs
  if (mode == DRIVE) steer *= constrain(2.2f / (fabsf(speedMs) + 0.6f), 0.22f, 1.0f);
  // steering servo, rate limited
  float maxStep = cfg.steerRate * 2.0f * dt;
  steerOut += constrain(steer - steerOut, -maxStep, maxStep);
  servoWrite(steerOut);
  pmotorEst = fabsf(d) * vbus * max(0.0f, ibat);
}

void setup() {
  pinMode(PH1, OUTPUT); pinMode(PH2, OUTPUT);
  ledcAttach(EN1, 20000, 10); ledcAttach(EN2, 20000, 10); motors(0);
  ledcAttach(SERVO, 50, 14);
  pinMode(HALL, INPUT_PULLUP); attachInterrupt(digitalPinToInterrupt(HALL), hallIsr, FALLING);
  pinMode(BTN, INPUT_PULLUP);
  Serial.begin(115200);
  Pi.begin(115200, SERIAL_8N1, RXD, TXD);
  loadCfg();
  servoWrite(0);
  inaBegin();
  Serial.printf("SC-02 ready, INA226 %s\n", inaOk ? "ok" : "MISSING");
}

void loop() {
  static uint32_t lastCtl = micros(), lastTel = 0, lastIna = 0, pressedMs = 0;
  static bool wasPressed = false;
  pollPi();
  uint32_t nowUs = micros();
  if (nowUs - lastCtl >= 2000) { float dt = (nowUs - lastCtl) * 1e-6f; lastCtl = nowUs; control(dt); }
  uint32_t now = millis();
  if (now - lastIna >= 5) { lastIna = now; inaPoll(); }
  // BOOT button: hold 0.3 s to arm race mode, release to launch
  bool pressed = digitalRead(BTN) == LOW;
  if (pressed && !wasPressed) pressedMs = now;
  if (pressed && now - pressedMs > 300 && mode != RACE_RUN) { mode = RACE_ARMED; rgbLedWrite(RGB_BUILTIN, 60, 40, 0); }
  if (!pressed && wasPressed && mode == RACE_ARMED) { mode = RACE_RUN; raceT0 = now; racePulses0 = pulses; raceT12 = NAN; rgbLedWrite(RGB_BUILTIN, 60, 0, 0); }
  if (pressed && !wasPressed && mode == RACE_RUN) { mode = RACE_DONE; }
  wasPressed = pressed;
  // telemetry to the Pi, 20 Hz:  T,ms,vbus_mV,ibat_mA,duty_x1000,steer_x1000,speed_mm_s,mode,t12_ms
  if (now - lastTel >= 50) {
    lastTel = now;
    Pi.printf("T,%lu,%d,%d,%d,%d,%d,%d,%d\n", (unsigned long)now, (int)(vbus * 1000), (int)(ibat * 1000), (int)(dutyOut * 1000),
              (int)(steerOut * 1000), (int)(speedMs * 1000), (int)mode, isnan(raceT12) ? -1 : (int)(raceT12 * 1000));
    if (mode == DRIVE) rgbLedWrite(RGB_BUILTIN, 0, (now - lastCmdMs < 300) ? 40 : 0, (now - lastCmdMs < 300) ? 0 : 40);
  }
}
