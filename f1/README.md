# SC-02 · Solar Hypercar

Een gesloten raceprototype in Le-Mans-stijl voor de Solar Olympiade. De wielen zitten in wielkasten, en van buiten zie je niets van de binnenkant. De vloer is lasergesneden zwart plexi. De Pi 4 en de ESP32-S3 zitten binnenin, je stuurt met de Recon Cloud-controller (Bluetooth) of met je gsm (wifi).

**Simulatie:** draai de sim lokaal met `cd f1/web && python3 -m http.server` en open http://localhost:8000 (vrij rijden, verbruik live), of zet de map `f1/web` op je eigen server. **Downloads:** de printbestanden staan in [`PRINTEN_PLA_TPU/`](../PRINTEN_PLA_TPU/).

| | |
|---|---|
| Afmetingen | 376 × 176 × 62 mm (regel: breedte ≤ 300 mm), rijhoogte 4 mm |
| Gewicht | ± 715 g (3S LiPo + Pi 4), zie `cad/out/mass.json` |
| Aandrijving | 2× Tamiya Hyper-Dash 3 → 8T:42T (5,25:1) → achteras, 2× DRV8874 (vooruit/achteruit/remmen) |
| Sturen | MG90S-servo, ophanging binnen de voorwielkasten, ±20° |
| Wielen | achter Ø44×20, voor Ø42×15, gegoten banden die op de velg klikken (zoals een fietsband) |
| Simulatie | 12 m in **2,5 s**, topsnelheid ± 39 km/h (motor 4,8 V; 6 V ≈ 48, 7,4 V ≈ 59 km/h), 0,9 g in de bocht |
| Verbruik rijden | Pi 4 ≈ 3,4 W, ESP32 ≈ 0,5 W, servo 0,1–2 W, motoren 5–40 W |

## Batterij: 4,8 V of 12 V?
- **Kit (wedstrijd):** 4× AA NiMH = **4,8 V** (5,2 V vers). Voor de wedstrijd verplicht (regel 1.6/5.1).
- **3S LiPo = 11,1 V (12,6 V vol)**: voor rijden met de Pi 4 en de controller. De Pi krijgt stabiel 5 V, en je rijdt veel langer.
  De ESP beperkt de motorspanning standaard tot 4,8 V (instelbaar tot 6 / 7,4 V = "boost"; de 130-motortjes worden dan wel warm).
- Het batterijvak (78 × 68 × 26 mm) past op beide.

## Wat is wat

| Map | Inhoud |
|---|---|
| `cad/` | Parametrisch model: `p.py` (maten), `body.py` (carrosserie), `car.py` (alle onderdelen), `build.py` (STL, DXF, GLB en controles) |
| `cad/out/floor_2mm_acrylic.dxf` | **Lasersnijbestand vloer** (2 mm zwart plexi, verzonken M3-gaten) |
| `cad/out/print/*.3mf` | **Printklare Bambu P1S-platen** + `print_report.json` |
| `P1S_STEP/` | **STEP per printplaat + per onderdeel**, 3mf's, `LEESMIJ.md` (PLA of ASA?) |
| `cad/out/stl/` | Alle onderdelen als STL (printoriëntatie) |
| `firmware/sc02/` | ESP32-S3: motoren, servo, INA226, tractiecontrole, failsafe, race-launch |
| `pi/` | Pi 4: Bluetooth-controller + gsm-besturing + live verbruik (`sc02_pi.py`, `phone.html`) |
| `web/` | De 3D-simulatie (three.js) |
| `docs/wiring_sc02.png` | Elektrisch schema |

## Bouwen

### 1. Vloer laseren
`floor_2mm_acrylic.dxf` → 2 mm **zwart** acrylaat (opaak, zodat je ook van onder niets ziet). Maten in mm.
Verzink de M3-gaten aan de onderkant 90° (of laat ze verzinken bij de laserservice). De 6 sleuven onder de Pi zijn voor koeling.

### 2. Printen (P1S, 0,4 mm nozzle)
| Plaat | Materiaal | Opmerking |
|---|---|---|
| 1 body main, 2 body nose | ASA (rood of in kleur naar keuze) | tree supports binnenin, naad bij x = 150 mm valt onder de koepel |
| 3 canopy | smoke/zwart PETG | glanzend, eventueel polijsten |
| 4 chassis parts | ASA | modules, fusees, lagerblokken, trays, magneetklemmen |
| 5 aero | zwart ASA | achtervleugel (op zijn eindplaat geprint), splitter, diffuser |
| 6 wheels | PLA (grafiet) | velgen + tandwiel 42T m0,5 |
| 7a tyre mold bottom + cores, 7b tyre mold top | PLA | 3-delige mal per band (de 2 malhelften zijn elk 132 mm, dus 2 platen) |
| 8 optie | TPU 95A | banden printen in plaats van gieten |

Tip: lichtgewicht-ASA (bv. colorFabb LW-ASA) maakt de body ± 40 g lichter.

### 3. Banden gieten (fietsband-principe)
1. Kern (oranje, velgvorm) op de pin in de onderste mal, bovenste mal erop, 7× M3 aanspannen.
2. ± 6 ml (achter) / 4 ml (voor) PU-rubber Shore 50A of siliconen Shore 40A met een spuit via de zij-ingang inspuiten, tot het uit alle 6 ontluchtingen komt.
3. Na het uitharden de mal openen en de band van de kern trekken. Daarna **over de velgflens rollen**: de bead-randen klikken onder de haken van de velg.

### 4. Mechaniek
- Achteras: carbon Ø3 × 186 mm, door de lagerblokken (683ZZ), de afstandsbussen en de wielkastgaten; het tandwiel op x = 0, y = −8 mm.
- Motoren: 8T-pinion erop drukken, in de wiegen leggen, klem erop (4× M2).
- Voor: de servo omgekeerd in de kooi, as naar beneden. Stuurhoorn erop, stuurstangen (M2) naar de stuurarmen. Fusees op M3-kingpins door de draagarmen. Steekasjes Ø3 staal 16 mm; de voorwielen draaien op 2× 683ZZ.
- Alles wordt van onderen door de vloer vastgeschroefd (M3 verzonken). Van buiten is geen schroef zichtbaar.
- De carrosserie klikt erop met 8 magneten (6 × 3 mm). De koepel lijm je erop.

### 5. Elektronica
Zie het schema. Kort:
- Batterij → zekering 10 A → schakelaar S1 (onder de vloer) → BUS+. Het paneel komt via de diode 1N5819 op BUS+ (verplicht).
- De min loopt via de 2 mΩ-shunt van de INA226 naar GND.
- BUS+ voedt 2× DRV8874 (één per motor) en de Pololu S13V30F5 (5 V 3 A) voor de Pi 4, de servo en de ESP.
- Bedrading:
  - UART: ESP GPIO17 → Pi pin 10, GPIO18 ← Pi pin 8, plus massa.
  - Servo op GPIO9.
  - INA226: SDA GPIO1, SCL GPIO2.
  - Hallsensor op GPIO10, met 2 magneten 2 × 1 mm in het tandwiel.

### 6. Software
```bash
# ESP32-S3
arduino-cli compile -b esp32:esp32:esp32s3:CDCOnBoot=cdc firmware/sc02
arduino-cli upload  -b esp32:esp32:esp32s3:CDCOnBoot=cdc -p /dev/cu.usbmodem* firmware/sc02
# Raspberry Pi 4 (Raspberry Pi OS Lite 64-bit)
sudo raspi-config nonint do_serial_hw 0 && sudo raspi-config nonint do_serial_cons 1     # UART aan, console uit
sudo apt install -y python3-aiohttp python3-serial python3-evdev
sudo nmcli dev wifi hotspot ifname wlan0 ssid SC-02 password <jouw-wachtwoord> && sudo nmcli connection modify Hotspot connection.autoconnect yes
bluetoothctl   # scan on → pair <MAC van de Recon> → trust → connect   (controller in pairing-modus)
sudo mkdir -p /opt/sc02 && sudo cp pi/sc02_pi.py pi/phone.html /opt/sc02/ && sudo cp pi/sc02.service /etc/systemd/system/ && sudo systemctl enable --now sc02
```
Daarna verbind je je gsm met de wifi **SC-02** en ga je naar **http://10.42.0.1**.

### Besturing
| Controller | Gsm | Simulatie |
|---|---|---|
| Rechtertrigger = gas, linkertrigger = rem/achteruit, linkerstick = sturen | linkervlak = sturen, rechterbalk = gas/rem | W/S of ↑/↓, A/D of ←/→, spatie = rem, C = camera, R = reset |
| A = rijden/race, Y = boost 6 V, B = normaal 4,8 V | DRIVE-knop = race-modus | gamepad werkt ook in de browser |

**Race-modus (wedstrijd, zonder Pi):** houd de BOOT-knop van de ESP ingedrukt (gele LED) en laat los: launch control (45 % → 100 % in 350 ms), stop na 14 m.

## Kosten
Zie `docs/BOM_SC02.md`. Pro-versie ± €165, budgetversie ± €95. De Pi 4, de ESP32-S3 en de controller heb je al.
