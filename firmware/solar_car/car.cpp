#include <Arduino.h>
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
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ESPmDNS.h>

// ---------------- pins
static const int PIN_PWM = 4;
static const int PIN_BTN = 5;
static const int PIN_HALL = 6;
static const int PIN_VBAT = 1;
static const float VBAT_DIV = (100.0f + 47.0f) / 47.0f;

// ---------------- pit Wi-Fi (Raspberry Pi hotspot, see pit/README.md)
static const char *WIFI_SSID = "solarpit";
#include "secrets.h"                  // WIFI_PASS (copy secrets.example.h -> secrets.h, not in git)

// ---------------- settings (stored in flash, editable over HTTP)
struct Config {
  float start_duty = 0.45f;     // from sim/out/final_design.json
  uint32_t ramp_ms = 350;
  float stop_m = 14.0f;         // finish is at 12 m; coast after 14 m
  uint32_t timeout_ms = 5000;
  float mm_per_pulse = 31.42f;  // pi * 40 mm / 4 magnets -> calibrate by pushing the car 2 m
  uint32_t start_delay_ms = 0;
  uint32_t pwm_hz = 20000;
  bool wifi = true;             // false = race mode
  bool hall = true;             // false if no sensor fitted (then only the timeout stops the car)
} cfg;
Preferences prefs;

// ---------------- state
enum State { IDLE, ARMED, COUNTDOWN, RUNNING, DONE };
volatile State state = IDLE;
volatile uint32_t pulses = 0;
volatile uint32_t lastPulseUs = 0;
volatile uint32_t pulseTimes[64];       // first pulses for accurate split times
volatile uint16_t nPulseTimes = 0;
uint32_t runStartUs = 0, countdownStartMs = 0;

struct LogRow { uint16_t t_ms; uint16_t duty_pm; uint16_t vbat_mv; uint16_t pulses; };
static const int LOG_MAX = 4000;        // 8 s at 500 Hz
LogRow logBuf[LOG_MAX];
volatile int logN = 0;

struct Result { float t12 = NAN, vmax = 0, vmin_bat = 0, dist = 0; uint32_t run_ms = 0; char stop_reason[16] = "-"; } last;

WebServer server(80);

// explicit prototypes (the Arduino preprocessor trips over the lambdas below)
void finishRun(const char *reason);
void requestStart();
void setupWifi();
void sendCors();
String statusJson();
String configJson();

// ---------------- helpers
float readVbat() { return analogReadMilliVolts(PIN_VBAT) * VBAT_DIV / 1000.0f; }

void led(uint8_t r, uint8_t g, uint8_t b) { rgbLedWrite(RGB_BUILTIN, r, g, b); }

void setDuty(float d) {
  d = constrain(d, 0.0f, 1.0f);
  ledcWrite(PIN_PWM, (uint32_t)(d * 1023.0f + 0.5f));
}

void IRAM_ATTR hallIsr() {
  uint32_t now = micros();
  if (now - lastPulseUs < 300) return;  // debounce (9 m/s -> ~3.5 ms between magnets)
  lastPulseUs = now;
  pulses++;
  if (state == RUNNING && nPulseTimes < 64) pulseTimes[nPulseTimes++] = now;
}

void loadConfig() {
  prefs.begin("car", true);
  cfg.start_duty = prefs.getFloat("d0", cfg.start_duty);
  cfg.ramp_ms = prefs.getUInt("ramp", cfg.ramp_ms);
  cfg.stop_m = prefs.getFloat("stop", cfg.stop_m);
  cfg.timeout_ms = prefs.getUInt("tmo", cfg.timeout_ms);
  cfg.mm_per_pulse = prefs.getFloat("mmpp", cfg.mm_per_pulse);
  cfg.start_delay_ms = prefs.getUInt("delay", cfg.start_delay_ms);
  cfg.pwm_hz = prefs.getUInt("pwmhz", cfg.pwm_hz);
  cfg.wifi = prefs.getBool("wifi", cfg.wifi);
  cfg.hall = prefs.getBool("hall", cfg.hall);
  prefs.end();
}

void saveConfig() {
  prefs.begin("car", false);
  prefs.putFloat("d0", cfg.start_duty); prefs.putUInt("ramp", cfg.ramp_ms); prefs.putFloat("stop", cfg.stop_m);
  prefs.putUInt("tmo", cfg.timeout_ms); prefs.putFloat("mmpp", cfg.mm_per_pulse);
  prefs.putUInt("delay", cfg.start_delay_ms); prefs.putUInt("pwmhz", cfg.pwm_hz);
  prefs.putBool("wifi", cfg.wifi); prefs.putBool("hall", cfg.hall);
  prefs.end();
}

String configJson() {
  char b[320];
  snprintf(b, sizeof b,
           "{\"start_duty\":%.3f,\"ramp_ms\":%lu,\"stop_m\":%.2f,\"timeout_ms\":%lu,\"mm_per_pulse\":%.3f,"
           "\"start_delay_ms\":%lu,\"pwm_hz\":%lu,\"wifi\":%s,\"hall\":%s}",
           cfg.start_duty, (unsigned long)cfg.ramp_ms, cfg.stop_m, (unsigned long)cfg.timeout_ms, cfg.mm_per_pulse,
           (unsigned long)cfg.start_delay_ms, (unsigned long)cfg.pwm_hz, cfg.wifi ? "true" : "false",
           cfg.hall ? "true" : "false");
  return String(b);
}

// ---------------- run control (500 Hz task on core 1)
void finishRun(const char *reason) {
  setDuty(0);
  last.run_ms = (micros() - runStartUs) / 1000;
  strncpy(last.stop_reason, reason, sizeof last.stop_reason - 1);
  // time over 12 m from the pulse timestamps (interpolated)
  last.dist = pulses * cfg.mm_per_pulse / 1000.0f;
  last.t12 = NAN;
  float p12 = 12000.0f / cfg.mm_per_pulse;
  if (cfg.hall && pulses >= (uint32_t)ceilf(p12)) {
    // pulse k happens at distance k*mm_per_pulse; we kept the first 64 timestamps + we have the log
    for (int i = 1; i < logN; i++) {
      if (logBuf[i].pulses >= p12) {
        float a = (p12 - logBuf[i - 1].pulses) / max(1, logBuf[i].pulses - logBuf[i - 1].pulses);
        last.t12 = (logBuf[i - 1].t_ms + a * (logBuf[i].t_ms - logBuf[i - 1].t_ms)) / 1000.0f;
        break;
      }
    }
  }
  // max speed over 50 ms windows
  last.vmax = 0; last.vmin_bat = 99;
  for (int i = 25; i < logN; i++) {
    float v = (logBuf[i].pulses - logBuf[i - 25].pulses) * cfg.mm_per_pulse / 1000.0f /
              ((logBuf[i].t_ms - logBuf[i - 25].t_ms) / 1000.0f);
    if (v > last.vmax) last.vmax = v;
  }
  for (int i = 0; i < logN; i++) last.vmin_bat = min(last.vmin_bat, logBuf[i].vbat_mv / 1000.0f);
  state = DONE;
  Serial.printf("RUN DONE (%s): %lu ms, %.2f m, t12=%.3f s, vmax=%.2f m/s, Vbat min %.2f V\n", reason,
                (unsigned long)last.run_ms, last.dist, last.t12, last.vmax, last.vmin_bat);
}

void runTask(void *) {
  TickType_t wake = xTaskGetTickCount();
  for (;;) {
    if (state == RUNNING) {
      uint32_t t_us = micros() - runStartUs;
      uint32_t t_ms = t_us / 1000;
      float d = (cfg.ramp_ms == 0) ? 1.0f
                                   : cfg.start_duty + (1.0f - cfg.start_duty) * (float)t_ms / (float)cfg.ramp_ms;
      d = min(d, 1.0f);
      setDuty(d);
      uint32_t p = pulses;
      if (logN < LOG_MAX) {
        logBuf[logN] = {(uint16_t)t_ms, (uint16_t)(d * 1000), (uint16_t)(readVbat() * 1000), (uint16_t)p};
        logN++;
      }
      float dist = p * cfg.mm_per_pulse / 1000.0f;
      if (cfg.hall && dist >= cfg.stop_m) finishRun("distance");
      else if (t_ms >= cfg.timeout_ms) finishRun("timeout");
      else if (cfg.hall && t_ms > 1000 && (micros() - lastPulseUs) > 700000UL) finishRun("stalled");
    }
    vTaskDelayUntil(&wake, pdMS_TO_TICKS(2));
  }
}

void startRun() {
  pulses = 0; nPulseTimes = 0; logN = 0;
  lastPulseUs = micros();
  runStartUs = micros();
  state = RUNNING;
  led(255, 0, 0);
}

void requestStart() {
  if (state == RUNNING || state == COUNTDOWN) return;
  if (cfg.start_delay_ms == 0) startRun();
  else { state = COUNTDOWN; countdownStartMs = millis(); led(255, 120, 0); }
}

// ---------------- HTTP API (test mode)
void sendCors() { server.sendHeader("Access-Control-Allow-Origin", "*"); }

String statusJson() {
  char b[420];
  const char *st[] = {"idle", "armed", "countdown", "running", "done"};
  snprintf(b, sizeof b,
           "{\"state\":\"%s\",\"vbat\":%.3f,\"pulses\":%lu,\"log_rows\":%d,\"uptime_ms\":%lu,"
           "\"last\":{\"t12\":%s,\"vmax\":%.3f,\"vbat_min\":%.3f,\"dist\":%.3f,\"run_ms\":%lu,\"stop\":\"%s\"},"
           "\"config\":%s}",
           st[state], readVbat(), (unsigned long)pulses, logN, (unsigned long)millis(),
           isnan(last.t12) ? "null" : String(last.t12, 3).c_str(), last.vmax, last.vmin_bat, last.dist,
           (unsigned long)last.run_ms, last.stop_reason, configJson().c_str());
  return String(b);
}

void handleRoot() {
  sendCors();
  server.send(200, "text/html",
              "<!doctype html><meta name=viewport content='width=device-width'><title>Solar car</title>"
              "<body style='font-family:sans-serif;max-width:480px;margin:auto;padding:12px'>"
              "<h2>Solar car</h2><button style='font-size:28px;width:100%' onclick=\"fetch('/go',{method:'POST'})\">GO</button>"
              "<p><button onclick=\"fetch('/stop',{method:'POST'})\">STOP</button></p><pre id=s></pre>"
              "<p><a href=/log.csv>download last log (CSV)</a></p>"
              "<script>setInterval(()=>fetch('/status').then(r=>r.json()).then(j=>s.textContent=JSON.stringify(j,null,1)),500)</script>");
}

void handleConfig() {
  sendCors();
  if (server.method() == HTTP_POST) {
    if (server.hasArg("start_duty")) cfg.start_duty = constrain(server.arg("start_duty").toFloat(), 0.1f, 1.0f);
    if (server.hasArg("ramp_ms")) cfg.ramp_ms = server.arg("ramp_ms").toInt();
    if (server.hasArg("stop_m")) cfg.stop_m = server.arg("stop_m").toFloat();
    if (server.hasArg("timeout_ms")) cfg.timeout_ms = constrain((int)server.arg("timeout_ms").toInt(), 200, 15000);
    if (server.hasArg("mm_per_pulse")) cfg.mm_per_pulse = server.arg("mm_per_pulse").toFloat();
    if (server.hasArg("start_delay_ms")) cfg.start_delay_ms = server.arg("start_delay_ms").toInt();
    if (server.hasArg("pwm_hz")) { cfg.pwm_hz = constrain((int)server.arg("pwm_hz").toInt(), 1000, 40000);
                                   ledcChangeFrequency(PIN_PWM, cfg.pwm_hz, 10); }
    if (server.hasArg("wifi")) cfg.wifi = server.arg("wifi") == "true" || server.arg("wifi") == "1";
    if (server.hasArg("hall")) cfg.hall = server.arg("hall") == "true" || server.arg("hall") == "1";
    saveConfig();
  }
  server.send(200, "application/json", configJson());
}

void handleLog() {
  sendCors();
  server.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server.send(200, "text/csv", "");
  server.sendContent("t_ms,duty,vbat_V,pulses,dist_m\n");
  char line[64];
  String chunk;
  for (int i = 0; i < logN; i++) {
    snprintf(line, sizeof line, "%u,%.3f,%.3f,%u,%.4f\n", logBuf[i].t_ms, logBuf[i].duty_pm / 1000.0f,
             logBuf[i].vbat_mv / 1000.0f, logBuf[i].pulses, logBuf[i].pulses * cfg.mm_per_pulse / 1000.0f);
    chunk += line;
    if (chunk.length() > 1200) { server.sendContent(chunk); chunk = ""; }
  }
  if (chunk.length()) server.sendContent(chunk);
  server.sendContent("");
}

void setupWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("solarcar");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  WiFi.setSleep(false);
  server.on("/", handleRoot);
  server.on("/status", [] { sendCors(); server.send(200, "application/json", statusJson()); });
  server.on("/go", HTTP_POST, [] {
    sendCors();
    if (state == RUNNING) { server.send(409, "application/json", "{\"error\":\"running\"}"); return; }
    requestStart();
    server.send(200, "application/json", "{\"ok\":true}");
  });
  server.on("/stop", HTTP_POST, [] { sendCors(); if (state == RUNNING) finishRun("remote"); server.send(200, "application/json", "{\"ok\":true}"); });
  server.on("/config", handleConfig);
  server.on("/log.csv", handleLog);
  server.begin();
  MDNS.begin("solarcar");                 // reachable as http://solarcar.local
  MDNS.addService("http", "tcp", 80);
}

// ---------------- setup / loop
void setup() {
  pinMode(PIN_PWM, OUTPUT);
  digitalWrite(PIN_PWM, LOW);           // motors off before anything else
  Serial.begin(115200);
  pinMode(PIN_BTN, INPUT_PULLUP);
  pinMode(PIN_HALL, INPUT_PULLUP);
  analogSetPinAttenuation(PIN_VBAT, ADC_11db);
  loadConfig();
  ledcAttach(PIN_PWM, cfg.pwm_hz, 10);
  setDuty(0);
  attachInterrupt(digitalPinToInterrupt(PIN_HALL), hallIsr, FALLING);

  // hold START at power-on -> toggle test/race mode
  if (digitalRead(PIN_BTN) == LOW) {
    cfg.wifi = !cfg.wifi;
    saveConfig();
    for (int i = 0; i < 6; i++) { cfg.wifi ? led(0, 0, 255) : led(0, 255, 0); delay(150); led(0, 0, 0); delay(150); }
    while (digitalRead(PIN_BTN) == LOW) delay(10);
  }
  if (cfg.wifi) setupWifi();
  else WiFi.mode(WIFI_OFF);
  xTaskCreatePinnedToCore(runTask, "run", 4096, nullptr, configMAX_PRIORITIES - 2, nullptr, 1);
  Serial.printf("Solar car ready. Mode: %s, Vbat %.2f V\n", cfg.wifi ? "TEST (Wi-Fi)" : "RACE", readVbat());
}

void loop() {
  static uint32_t pressedMs = 0, lastLed = 0;
  static bool wasPressed = false;
  static bool ignoreUntilRelease = false;   // a press that stopped a run must never re-arm the car
  bool pressed = digitalRead(PIN_BTN) == LOW;

  if (cfg.wifi) server.handleClient();

  // button: hold >= 300 ms to arm, release to start; pressing while running = emergency stop
  if (pressed && !wasPressed) {
    pressedMs = millis();
    if (state == RUNNING || state == COUNTDOWN) { finishRun("button"); ignoreUntilRelease = true; }
  }
  if (!pressed) ignoreUntilRelease = false;
  if (pressed && !ignoreUntilRelease && state != RUNNING && state != COUNTDOWN && state != ARMED &&
      millis() - pressedMs >= 300) {
    state = ARMED;
    led(255, 160, 0);
  }
  if (!pressed && wasPressed && state == ARMED) requestStart();
  wasPressed = pressed;

  if (state == COUNTDOWN && millis() - countdownStartMs >= cfg.start_delay_ms) startRun();

  if (millis() - lastLed > 250 && (state == IDLE || state == DONE)) {
    lastLed = millis();
    float vb = readVbat();
    static bool blink = false; blink = !blink;
    if (vb > 0.5f && vb < 4.4f) led(blink ? 60 : 0, blink ? 60 : 0, blink ? 60 : 0);   // pack needs charging
    else if (state == DONE) led(150, 0, 255);
    else if (cfg.wifi) led(0, 0, WiFi.status() == WL_CONNECTED ? 255 : (blink ? 255 : 0));
    else led(0, 255, 0);
  }

  // serial commands for bench tests: g = go, s = stop, d = dump log
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'g') requestStart();
    if (c == 's' && state == RUNNING) finishRun("serial");
    if (c == 'd') for (int i = 0; i < logN; i++)
        Serial.printf("%u,%u,%u,%u\n", logBuf[i].t_ms, logBuf[i].duty_pm, logBuf[i].vbat_mv, logBuf[i].pulses);
  }
  delay(1);
}
