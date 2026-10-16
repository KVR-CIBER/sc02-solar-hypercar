# Pit / timing station (Raspberry Pi 4)

The Pi makes its own Wi-Fi network, starts the car, times it with a light gate at 12 m, downloads the car's log, and shows every run next to the simulation. Use it on a phone or laptop at `http://10.42.0.1:8080`.

## Hardware

- Raspberry Pi 4 + power bank or USB-C supply
- IR break-beam pair (5 mm). Transmitter on one side of the finish line, receiver on the other, at about 25 mm height (the car body height, the wheels are lower).
  - receiver: red → 5V (pin 2), black → GND (pin 6), white/yellow (signal) → **GPIO17 (pin 11)**
  - transmitter: red → 5V, black → GND
  - Check the **gate** pill on the page: "clear" with the beam free, "BLOCKED" with your hand in it. If it's inverted, start with `--gate-broken-level high`.

## Setup (Raspberry Pi OS Bookworm)

```bash
sudo apt install -y python3-flask python3-requests python3-gpiozero
mkdir -p ~/solar-pit && cp pit.py sim_trace.json ~/solar-pit/
# Wi-Fi hotspot "solarpit" / <jouw-wachtwoord> (the car firmware joins this)
sudo nmcli dev wifi hotspot ifname wlan0 ssid solarpit password <jouw-wachtwoord>
sudo nmcli connection modify Hotspot connection.autoconnect yes
# run it
python3 ~/solar-pit/pit.py              # or --car http://10.42.0.xx if solarcar.local doesn't resolve
```

Auto-start at boot: create `/etc/systemd/system/solar-pit.service`

```ini
[Unit]
Description=Solar car pit station
After=network-online.target
[Service]
User=<your-user>
ExecStart=/usr/bin/python3 /home/<your-user>/solar-pit/pit.py
Restart=always
[Install]
WantedBy=multi-user.target
```
then `sudo systemctl enable --now solar-pit`.

## Use

1. Car switched on in **test mode** (LED blue, steady once it's on the Wi-Fi).
2. Put the car on the start line, with the gate at exactly 12.00 m.
3. Press **GO** on the page. The car starts, the gate stops the clock, and the run appears in the table with time, top speed and lowest battery voltage. The graph shows the run (solid) and the simulation (dashed).
4. Change start duty / ramp and press **save**. The values are stored on the car and survive a power cycle.

Timing accuracy: the Pi sends GO and takes the start instant as the middle of the HTTP round trip (typically 5–20 ms on the hotspot, shown as `rtt_ms` in each run). The car's own odometry time (from its log) does not depend on Wi-Fi.

Test it without hardware on any computer: `python3 pit.py --mock` (a fake car replays the simulation).
