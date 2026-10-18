"""SC-02 floor board: the whole floor of the car is the PCB. Single source of truth for parts, nets and placement.

The 2 mm laser-cut acrylic floor is replaced by a 2 mm 4-layer PCB with exactly the same outline, the same countersunk
M3 holes (all printed parts screw on from below, as before) and the Pi cooling slots. The electronics sit in the two
sidepods, where the separate boards used to be:
  * left pod  (car +y): XT60, fuse, power switch pads, reverse protection, INA226 current sense, 5 V 5 A buck, I2C;
  * right pod (car -y): ESP32-S3, 2x DRV8871, USB-C to the Raspberry Pi 4, servo / hall / lights / solar panel.
A copper strip under the battery tray joins both pods. The rest of the floor is bare (black solder mask, no copper).

PCB coordinates = car coordinates with y flipped: X = car x (forward, rear axle at 0), Y = -car y (KiCad y points down),
so in the PCB view the front is to the right and the car's left side is at the top.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
FLOOR = json.load(open(os.path.join(HERE, 'floor.json')))      # from f1/cad (car.py): outline, holes, part boxes
BOARD_T = 2.0
CORNER_R = 0.0
BOARD_W, BOARD_H = 362.0, 158.6       # bounding box of the floor (informational)
# electronics region: left pod + bridge under the battery tray + right pod (PCB coordinates)
REGION = [(54.0, -66.0), (136.0, -66.0), (136.0, -36.5), (66.0, -36.5), (66.0, 36.5), (136.0, 36.5), (136.0, 66.0), (131.0, 66.0),
          (131.0, 68.2), (119.0, 68.2), (119.0, 66.0), (54.0, 66.0)]     # (notch to the floor edge for the USB-C)
ESP = (92.5, 50.5)              # ESP32-S3 module origin, rotated 180: antenna towards the car's right side wall
L = (104.0, -36.0)              # offset of the power block (same relative layout as the HAT version)

parts = []


def P(ref, sym, fp, value, pins, at, mpn='', lcsc='', group='', dnp=False, side='F'):
    parts.append(dict(ref=ref, sym=sym, fp=fp, value=value, pins={str(k): v for k, v in pins.items()},
                      at=at, mpn=mpn, lcsc=lcsc, group=group, dnp=dnp, side=side))


def l(x, y, rot=0):
    return (x + L[0], y + L[1], rot)


R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
C1210 = 'Capacitor_SMD:C_1210_3225Metric'
LED0603 = 'LED_SMD:LED_0603_1608Metric'
SOT23 = 'Package_TO_SOT_SMD:SOT-23'
USBC = 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12'
HDR3 = 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical'


def R(ref, val, a, b, at, g, mpn='', fp=R0603):
    P(ref, 'Device:R', fp, val, {1: a, 2: b}, at, mpn=mpn or f'0603 {val} 1%', group=g)


def C(ref, val, a, b, at, g, fp=C0603, mpn=''):
    size = fp.split(':')[1].split('_')[1]
    kind = 'X7R' if val.endswith(('n', 'p')) or val == '100n' else 'X5R'
    P(ref, 'Device:C', fp, val, {1: a, 2: b}, at, mpn=mpn or f'{size} {val} {kind} ceramic', group=g)


# ---------------------------------------------------------------- battery: XT60 -> fuse -> switch -> reverse protection -> shunt
G = 'Batterij 3S: XT60, zekering, schakelaar, stroommeting'
P('J1', 'Connector_Generic:Conn_01x02', 'Connector_AMASS:AMASS_XT60-M_1x02_P7.20mm_Vertical', 'XT60',
  {1: 'GND', 2: 'BAT_IN'}, (58.5, -63.0, 270), mpn='AMASS XT60-M (male, vertical): the LiPo plugs in from above', group=G)
P('F1', 'Device:Fuse', 'Resistor_SMD:R_2512_6332Metric', '10A', {1: 'BAT_IN', 2: 'BAT_F'}, (66.5, -53.0, 90),
  mpn='2410FA-10A (fast 10 A, 2410 body on 2512 pads)', group=G)
P('J11', 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P5mm_SW', 'SCHAKELAAR', {1: 'BAT_F', 2: 'VBAT_RAW'},
  (66.5, -61.5, 0), mpn='solder pads for the power switch (mounted from below in the 6.2 mm hole)', group=G)
P('Q1', 'sc02:Q_PMOS_GDS', 'Package_TO_SOT_SMD:TO-252-2', 'AOD4185',
  {1: 'Q1_G', 2: 'VBAT_RAW', 3: 'VBAT_P'}, l(-19.0, -21.5, 90), mpn='AOD4185 (P-MOSFET 40 V 40 A, reverse polarity)', group=G)
R('R1', '10k', 'Q1_G', 'GND', l(-13.2, -26.0, 90), G)
P('D2', 'Device:D_Zener', 'Diode_SMD:D_SOD-123', 'BZT52C15', {1: 'VBAT_P', 2: 'Q1_G'}, l(-14.0, -22.0, 90),
  mpn='BZT52C15 (gate clamp)', group=G)
P('RS1', 'Device:R', 'Resistor_SMD:R_2512_6332Metric', '2m', {1: 'VBAT_P', 2: 'VBUS'}, l(-19.0, -12.5, 180),
  mpn='2512 2 mOhm 2 W current shunt', group=G)
P('D1', 'Device:D_TVS', 'Diode_SMD:D_SMB', 'SMBJ15CA', {1: 'VBUS', 2: 'GND'}, l(-27.5, -8.5, 90), mpn='SMBJ15CA', group=G)
P('C1', 'Device:C_Polarized', 'Capacitor_SMD:CP_Elec_6.3x7.7', '100u 25V', {1: 'VBUS', 2: 'GND'}, l(-7.5, -9.0, 0),
  mpn='100uF 25V 6.3x7.7 alu', group=G)
P('U6', 'Sensor_Energy:INA226', 'Package_SO:TSSOP-10_3x3mm_P0.5mm', 'INA226',
  {1: 'GND', 2: 'GND', 4: 'I2C_SDA', 5: 'I2C_SCL', 6: '3V3', 7: 'GND', 8: 'VBUS', 9: 'VBUS', 10: 'VBAT_P'},
  l(-19.0, -7.0, 0), mpn='INA226AIDGSR (0x40)', group=G)
C('C2', '100n', '3V3', 'GND', l(-14.0, -11.0, 90), G)

# ---------------------------------------------------------------- 5 V / 5 A buck (TI TPS54560B, same design as ARACHNE)
G = 'Buck 5 V 5 A (Pi 4 + servo)'
BX, BY = 12.5, -16.5
P('U1', 'Regulator_Switching:TPS54560BDDA', 'Package_SO:Texas_R-PDSO-G8_EP2.95x4.9mm_Mask2.4x3.1mm_ThermalVias',
  'TPS54560B', {1: 'BOOT', 2: 'VBUS', 3: 'BUCK_EN', 4: 'BUCK_RT', 5: 'BUCK_FB', 6: 'BUCK_COMP', 7: 'GND', 8: 'SW', 9: 'GND'},
  l(BX, BY, 0), mpn='TPS54560BDDAR', group=G)
C('C5', '10u 25V', 'VBUS', 'GND', l(BX - 7.3, BY - 0.6, 180), G, fp=C1206)
C('C6', '10u 25V', 'VBUS', 'GND', l(BX - 7.3, BY + 2.6, 180), G, fp=C1206)
C('C7', '100n', 'VBUS', 'GND', l(BX - 6.7, BY - 3.0, 180), G)
R('R4', '442k', 'VBUS', 'BUCK_EN', l(BX - 3.0, BY + 5.0, 90), G)
R('R5', '90.9k', 'BUCK_EN', 'GND', l(BX - 1.4, BY + 5.0, 90), G)
R('R6', '243k', 'BUCK_RT', 'GND', l(BX + 0.2, BY + 5.0, 90), G)
C('C8', '100n', 'BOOT', 'SW', l(17.6, -18.5, 90), G)
P('L1', 'Device:L', 'Inductor_SMD:L_Bourns_SRP1038C_10.0x10.0mm', '6.8u', {1: 'SW', 2: 'V5'},
  l(25.5, -21.5, 270), mpn='Bourns SRP1038C-6R8M (6.8 uH, >= 8 A)', group=G)
P('D4', 'Device:D_Schottky', 'Diode_SMD:D_SMC', 'B560C', {1: 'SW', 2: 'GND'}, l(BX, -25.0, 180),
  mpn='B560C (5 A 60 V Schottky)', group=G)
for ref, x in (('C9', 20.3), ('C10', 23.65), ('C11', 27.0)):
    C(ref, '47u 10V', 'V5', 'GND', l(x, -12.4, 270), G, fp=C1210)
R('R7', '53.6k', 'V5', 'BUCK_FB', l(BX + 5.1, BY + 2.0, 90), G)
R('R8', '10.2k', 'BUCK_FB', 'GND', l(BX + 5.1, BY + 5.4, 90), G)
R('R9', '16.9k', 'BUCK_COMP', 'COMP_RC', l(BX + 1.8, BY + 5.0, 90), G)
C('C12', '4n7', 'COMP_RC', 'GND', l(BX + 1.8, BY + 8.2, 90), G)
C('C13', '47p', 'BUCK_COMP', 'GND', l(BX + 0.2, BY + 8.2, 90), G)
P('D5', 'Device:LED', LED0603, 'groen 5V', {1: 'GND', 2: 'LED5_A'}, l(BX - 3.0, BY + 8.6, 90), mpn='LED 0603 green', group=G)
R('R10', '2k2', 'V5', 'LED5_A', l(BX - 1.4, BY + 8.6, 90), G)
P('J13', 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P5mm_5V', '5V PI', {1: 'GND', 2: 'V5'}, (126.0, -39.0, 0),
  mpn='solder pads: 5 V 3 A to the Pi 4 (GPIO pin 2/4 + 6)', group=G)
P('J7', 'Connector_Generic_MountingPin:Conn_01x04_MountingPin', 'Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal',
  'I2C', {1: 'GND', 2: '3V3', 3: 'I2C_SDA', 4: 'I2C_SCL', 'MP': 'GND'}, l(-1.5, -17.0, 0), mpn='JST SM04B-SRSS-TB (Qwiic / STEMMA QT)', group=G)
R('R24', '4k7', 'I2C_SDA', '3V3', l(-8.3, -19.0, 90), G)
R('R25', '4k7', 'I2C_SCL', '3V3', l(-8.3, -15.8, 90), G)

# ---------------------------------------------------------------- motor drivers (right pod, rear end: short leads to the motors)
for i, (u, rc, rc2, rl, j, y, in1, in2) in enumerate((('U4', 'C20', 'C21', 'R20', 'J2', 42.0, 4, 5),
                                                       ('U5', 'C22', 'C23', 'R21', 'J3', 54.0, 6, 7)), 1):
    G = f'Motor {i} (DRV8871)'
    P(u, 'Driver_Motor:DRV8871DDA', 'Package_SO:Texas_HTSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.95x4.9mm_Mask2.4x3.1mm_ThermalVias',
      'DRV8871', {1: 'GND', 2: f'M{i}_IN2', 3: f'M{i}_IN1', 4: f'M{i}_ILIM', 5: 'VBUS', 6: f'M{i}_A', 7: 'GND', 8: f'M{i}_B', 9: 'GND'},
      (68.0, y, 0), mpn='DRV8871DDAR (3.6 A H-bridge)', group=G)
    C(rc, '10u 25V', 'VBUS', 'GND', (74.0, y - 1.0, 90), G, fp=C1206)
    C(rc2, '100n', 'VBUS', 'GND', (76.2, y - 1.0, 90), G)
    R(rl, '18k', f'M{i}_ILIM', 'GND', (68.0, y + 3.8, 0), G)
    P(j, 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P5mm_M', f'MOTOR {i}', {1: f'M{i}_A', 2: f'M{i}_B'},
      (57.0, y - 2.5, 270), mpn='solder pads, motor leads', group=G)

# ---------------------------------------------------------------- ESP32-S3 + 3.3 V
G = '3,3 V (ESP32 + INA226)'
P('D6', 'Diode:SS14', 'Diode_SMD:D_SMA', 'SS14', {1: 'V5_ESP', 2: 'V5'}, (108.5, 39.5, 0), mpn='SS14', group=G)
P('D7', 'Diode:SS14', 'Diode_SMD:D_SMA', 'SS14', {1: 'V5_ESP', 2: 'VBUS_USB'}, (108.5, 43.3, 0), mpn='SS14', group=G)
P('U2', 'Regulator_Linear:AMS1117-3.3', 'Package_TO_SOT_SMD:SOT-223-3_TabPin2', 'AMS1117-3.3',
  {1: 'GND', 2: '3V3', 3: 'V5_ESP'}, (107.5, 53.0, 90), mpn='AMS1117-3.3', group=G)
C('C14', '10u', 'V5_ESP', 'GND', (105.0, 47.0, 0), G, fp=C0805)
C('C15', '22u', '3V3', 'GND', (109.0, 60.0, 0), G, fp=C0805)
C('C16', '100n', '3V3', 'GND', (105.5, 60.0, 0), G)

G = 'ESP32-S3'
P('U3', 'RF_Module:ESP32-S3-WROOM-1', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8',
  {1: 'GND', 40: 'GND', 41: 'GND', 2: '3V3', 3: 'ESP_EN',
   4: 'M1_IN1', 5: 'M1_IN2', 6: 'M2_IN1', 7: 'M2_IN2',      # IO4 IO5 IO6 IO7
   17: 'SERVO_PWM', 31: 'HALL', 19: 'LIGHT_G',              # IO9 IO38 IO11
   12: 'PANEL_ADC', 20: 'LED_ESP',                          # IO8 IO12
   39: 'I2C_SDA', 38: 'I2C_SCL',                            # IO1 IO2
   8: 'ELRS_TX', 9: 'ELRS_RX',                              # IO15 = ESP TX -> receiver RX, IO16 = ESP RX <- receiver TX (CRSF)
   10: 'ESP_TX', 11: 'ESP_RX',                              # IO17 / IO18: UART to the Pi
   13: 'ESP_DM', 14: 'ESP_DP', 27: 'ESP_IO0'},
  (ESP[0], ESP[1], 180), mpn='ESP32-S3-WROOM-1-N16R8', group=G)
C('C17', '22u', '3V3', 'GND', (79.2, 41.0, 0), G, fp=C0805)
C('C18', '100n', '3V3', 'GND', (79.2, 44.5, 0), G)
R('R11', '10k', '3V3', 'ESP_EN', (104.0, 64.0, 90), G)
C('C19', '1u', 'ESP_EN', 'GND', (105.8, 64.0, 90), G)
R('R12', '10k', '3V3', 'ESP_IO0', (107.6, 64.0, 90), G)
P('SW1', 'Switch:SW_Push', 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2', 'RESET', {1: 'ESP_EN', 2: 'GND'}, (78.6, 63.6, 0),
  mpn='CK KMR221G (4.2x2.8 tact)', group=G)
P('SW2', 'Switch:SW_Push', 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2', 'BOOT', {1: 'ESP_IO0', 2: 'GND'}, (78.6, 59.6, 0),
  mpn='CK KMR221G (4.2x2.8 tact) - also the race-mode button', group=G)
P('D8', 'Device:LED', LED0603, 'geel ESP', {1: 'GND', 2: 'LED_ESP_A'}, (113.5, 49.0, 90), mpn='LED 0603 yellow', group=G)
R('R13', '1k', 'LED_ESP', 'LED_ESP_A', (113.5, 52.2, 90), G)

# ---------------------------------------------------------------- USB-C: ESP32 native USB -> Raspberry Pi 4 (C to A cable)
G = 'USB-C (flashen / debug van buitenaf)'
P('J8', 'Connector:USB_C_Receptacle_USB2.0_16P', USBC, 'USB-C',
  {'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'SH': 'GND', 'A4': 'VBUS_USB', 'A9': 'VBUS_USB',
   'B4': 'VBUS_USB', 'B9': 'VBUS_USB', 'A5': 'CC1', 'B5': 'CC2', 'A6': 'ESP_DP', 'B6': 'ESP_DP',
   'A7': 'ESP_DM', 'B7': 'ESP_DM'}, (125.0, 64.6, 0), mpn='HRO TYPE-C-31-M-12 (at the floor edge: reachable through the body side)', group=G)
R('R27', '5k1', 'CC1', 'GND', (118.0, 56.5, 90), G)
R('R28', '5k1', 'CC2', 'GND', (132.0, 56.5, 90), G)
P('U10', 'Power_Protection:USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6', 'USBLC6-2SC6',
  {1: 'ESP_DP', 6: 'ESP_DP', 3: 'ESP_DM', 4: 'ESP_DM', 2: 'GND', 5: 'VBUS_USB'}, (125.0, 55.5, 0), mpn='USBLC6-2SC6', group=G)
C('C29', '1u', 'VBUS_USB', 'GND', (121.5, 52.0, 0), G)

# ---------------------------------------------------------------- connectors: servo, hall, panel, lights
G = 'Aansluitingen'
P('J4', 'Connector_Generic:Conn_01x03', HDR3, 'SERVO', {1: 'GND', 2: 'V5', 3: 'SERVO_SIG'}, (133.0, 39.0, 0),
  mpn='1x3 pin header 2.54 (MG90S: brown GND, red 5 V, orange signal)', group=G)
R('R18', '100', 'SERVO_PWM', 'SERVO_SIG', (130.0, 47.5, 90), G)
P('J5', 'Connector_Generic:Conn_01x03', HDR3, 'HALL', {1: 'GND', 2: 'V5', 3: 'HALL'}, (55.5, 63.5, 90),
  mpn='1x3 pin header 2.54 (A3144: GND, 5 V, out)', group=G)
R('R19', '10k', 'HALL', '3V3', (64.0, 61.5, 90), G)
P('J6', 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P4mm_S', 'ZONNEPANEEL', {1: 'GND', 2: 'PANEL'}, (116.0, 38.5, 0),
  mpn='solder pads, solar panel 5 V (measured only)', group=G)
R('R22', '100k', 'PANEL', 'PANEL_ADC', (116.5, 44.5, 90), G)
R('R23', '33k', 'PANEL_ADC', 'GND', (118.3, 44.5, 90), G)
P('J10', 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P4mm_S', 'LICHTEN', {1: 'LIGHT_D', 2: 'V5'}, (124.0, 38.5, 0),
  mpn='solder pads, LED lights 5 V (with their own resistors), low-side switched', group=G)
P('Q4', 'Transistor_FET:AO3400A', SOT23, 'AO3400A', {1: 'LIGHT_G', 2: 'GND', 3: 'LIGHT_D'}, (124.0, 45.5, 0), mpn='AO3400A', group=G)
R('R26', '100k', 'LIGHT_G', 'GND', (124.0, 48.5, 0), G)

# ---------------------------------------------------------------- RadioMaster ELRS receiver (RP2) + UART to the Pi 4
G = 'ELRS-ontvanger + Pi UART'
P('J12', 'Connector_Generic:Conn_01x04', 'sc02:Pads_ELRS_RX', 'ELRS RP2', {1: 'GND', 2: 'V5', 3: 'ELRS_RX_IN', 4: 'ELRS_TX_OUT'},
  (102.5, -39.0, 0), mpn='solder pads for a RadioMaster RP2 ELRS receiver (stick it on the marked spot)', group=G)
R('R29', '100', 'ELRS_RX_IN', 'ELRS_RX', (102.4, -43.5, 90), G)     # receiver TX -> ESP RX (IO16)
R('R30', '100', 'ELRS_TX', 'ELRS_TX_OUT', (104.2, -43.5, 90), G)    # ESP TX (IO15) -> receiver RX
P('J9', 'Connector_Generic:Conn_01x03', 'sc02:Pads_PI_UART', 'PI UART', {1: 'GND', 2: 'PI_TXD', 3: 'PI_RXD'},
  (115.5, -39.0, 0), mpn='solder pads: wires to the Pi 4 header (pin 6 GND, pin 8 TXD, pin 10 RXD)', group=G)
R('R16', '1k', 'ESP_TX', 'PI_RXD', (106.0, -43.5, 90), G)    # series resistors: no back-powering of an unpowered Pi
R('R17', '1k', 'PI_TXD', 'ESP_RX', (107.8, -43.5, 90), G)

# ---------------------------------------------------------------- mounting: every floor hole of the car (+ the power switch)
seen = set(); holes = []
for x, y, d in FLOOR['holes']:
    if (x, y) not in seen:
        seen.add((x, y)); holes.append((x, -y, d))
holes.append((77.5, -63.5, 6.2))                   # power switch from below (was at car (70, -46) on the acrylic floor)
for i, (x, y, d) in enumerate(holes, 1):
    P(f'H{i}', 'Mechanical:MountingHole', f'sc02:Hole_{d:.1f}mm', f'{d:.1f}', {}, (x, y, 0), group='Bevestiging (vloergaten)')
HOLE_SIZES = sorted({d for _, _, d in holes})

NETCLASS = {
    'POWER12': (['BAT_IN', 'BAT_F', 'VBAT_RAW', 'VBAT_P', 'VBUS', 'M1_A', 'M1_B', 'M2_A', 'M2_B'], 1.0, 0.2),
    'POWER5': (['V5', 'SW'], 0.6, 0.2),
    'PWR': (['3V3', 'V5_ESP', 'VBUS_USB', 'GND', 'LIGHT_D'], 0.35, 0.15),
    'USB': (['ESP_DP', 'ESP_DM'], 0.25, 0.15),
}
DNP = set()


def nets():
    s = set()
    for p in parts:
        s |= set(p['pins'].values())
    return sorted(s)


def outline():
    """floor outline from the CAD (car.floor_outline, cut at the diffuser), y flipped"""
    from shapely.geometry import Polygon, box
    poly = Polygon([(x, -y) for x, y in FLOOR['outline']]).buffer(0).intersection(box(FLOOR['diff_x0'], -200, 400, 200))
    poly = poly.simplify(0.02)
    return [tuple(map(lambda v: round(v, 4), p)) for p in poly.exterior.coords]


def slots():
    """Pi cooling slots (rounded 4 x 40 mm), same as the acrylic floor"""
    return [(x0, -20.0, x1, 20.0) for x0, x1 in FLOOR['slots']]


if __name__ == '__main__':
    reg = REGION + REGION[:1]
    json.dump({'edge': outline(), 'inner': [list(p) for p in reg]}, open(os.path.join(HERE, 'outline.json'), 'w'))
    print('outline.json written')
