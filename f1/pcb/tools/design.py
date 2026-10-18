"""SC-02 drive board: single source of truth for parts, nets and placement.

A 4-layer board that sits on top of the Raspberry Pi 4 like a HAT (40-pin socket underneath, Pi 4 holes),
65 x 70 mm: the Pi's 65 x 56 HAT area plus a 14 mm strip past the Pi's HDMI edge for the ESP32-S3 antenna.
It replaces the ESP32 DevKit bridge, both DRV8871 modules, the LM2596 and the INA226 module.

Board coordinates in mm, origin = board centre, +x = towards the Pi's USB end (front of the car),
+y = towards the Pi's HDMI edge. Pi 4 header row at y = -31.5, Pi 4 holes at (+-29, -31.5) and (+-29, 17.5).
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_W, BOARD_H, CORNER_R = 65.0, 70.0, 3.0
PI_HOLES = [(-29.0, -31.5), (29.0, -31.5), (29.0, 17.5), (-29.0, 17.5)]
HDR1 = (-24.13, -30.23)         # Pi header pin 1 (odd row = inner row, even row = outer row at y -32.77)
CAM_SLOT = (3.0, 8.0, 22.0, 11.5)   # camera flex slot above the Pi 4 CSI connector (x0, y0, x1, y1)
ESP = (-7.0, 28.25)             # ESP32-S3 module origin, rotated 180: antenna overhangs the bottom edge

parts = []


def P(ref, sym, fp, value, pins, at, mpn='', lcsc='', group='', dnp=False, side='F'):
    parts.append(dict(ref=ref, sym=sym, fp=fp, value=value, pins={str(k): v for k, v in pins.items()},
                      at=at, mpn=mpn, lcsc=lcsc, group=group, dnp=dnp, side=side))


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


# ---------------------------------------------------------------- battery entry: reverse protection + current sense
G = 'Batterij 3S + stroommeting'
P('J1', 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P7mm_D2.2mm_BAT', 'BAT 3S',
  {1: 'GND', 2: 'VBAT_RAW'}, (-28.0, -24.5, 270), mpn='solder pads for the XT60 lead (14-16 AWG)', group=G)
P('Q1', 'sc02:Q_PMOS_GDS', 'Package_TO_SOT_SMD:TO-252-2', 'AOD4185',
  {1: 'Q1_G', 2: 'VBAT_RAW', 3: 'VBAT_P'}, (-19.0, -21.5, 90), mpn='AOD4185 (P-MOSFET 40 V 40 A, reverse polarity)', group=G)
R('R1', '10k', 'Q1_G', 'GND', (-13.2, -26.0, 90), G)
P('D2', 'Device:D_Zener', 'Diode_SMD:D_SOD-123', 'BZT52C15', {1: 'VBAT_P', 2: 'Q1_G'}, (-14.0, -22.0, 90),
  mpn='BZT52C15 (gate clamp)', group=G)
P('RS1', 'Device:R', 'Resistor_SMD:R_2512_6332Metric', '2m', {1: 'VBAT_P', 2: 'VBUS'}, (-19.0, -12.5, 180),
  mpn='2512 2 mOhm 2 W current shunt', group=G)
P('D1', 'Device:D_TVS', 'Diode_SMD:D_SMB', 'SMBJ15CA', {1: 'VBUS', 2: 'GND'}, (-27.5, -10.0, 90), mpn='SMBJ15CA', group=G)
P('C1', 'Device:C_Polarized', 'Capacitor_SMD:CP_Elec_6.3x7.7', '100u 25V', {1: 'VBUS', 2: 'GND'}, (-7.5, -9.0, 0),
  mpn='100uF 25V 6.3x7.7 alu', group=G)
P('U6', 'Sensor_Energy:INA226', 'Package_SO:TSSOP-10_3x3mm_P0.5mm', 'INA226',
  {1: 'GND', 2: 'GND', 4: 'I2C_SDA', 5: 'I2C_SCL', 6: '3V3', 7: 'GND', 8: 'VBUS', 9: 'VBUS', 10: 'VBAT_P'},
  (-19.0, -7.0, 0), mpn='INA226AIDGSR (0x40)', group=G)
C('C2', '100n', '3V3', 'GND', (-14.0, -11.0, 90), G)

# ---------------------------------------------------------------- 5 V / 5 A buck (TI TPS54560B, same design as ARACHNE)
G = 'Buck 5 V 5 A (Pi 4 + servo)'
BX, BY = 12.5, -16.5          # U1 position
P('U1', 'Regulator_Switching:TPS54560BDDA', 'Package_SO:Texas_R-PDSO-G8_EP2.95x4.9mm_Mask2.4x3.1mm_ThermalVias',
  'TPS54560B', {1: 'BOOT', 2: 'VBUS', 3: 'BUCK_EN', 4: 'BUCK_RT', 5: 'BUCK_FB', 6: 'BUCK_COMP', 7: 'GND', 8: 'SW', 9: 'GND'},
  (BX, BY, 0), mpn='TPS54560BDDAR', group=G)
C('C5', '10u 25V', 'VBUS', 'GND', (BX - 7.3, BY - 0.6, 180), G, fp=C1206)
C('C6', '10u 25V', 'VBUS', 'GND', (BX - 7.3, BY + 2.6, 180), G, fp=C1206)
C('C7', '100n', 'VBUS', 'GND', (BX - 6.7, BY - 3.0, 180), G)
R('R4', '442k', 'VBUS', 'BUCK_EN', (BX - 3.0, BY + 5.0, 90), G)
R('R5', '90.9k', 'BUCK_EN', 'GND', (BX - 1.4, BY + 5.0, 90), G)
R('R6', '243k', 'BUCK_RT', 'GND', (BX + 0.2, BY + 5.0, 90), G)
C('C8', '100n', 'BOOT', 'SW', (17.6, -18.5, 90), G)
P('L1', 'Device:L', 'Inductor_SMD:L_Bourns_SRP1038C_10.0x10.0mm', '6.8u', {1: 'SW', 2: 'V5'},
  (25.5, -21.5, 270), mpn='Bourns SRP1038C-6R8M (6.8 uH, >= 8 A)', group=G)
P('D4', 'Device:D_Schottky', 'Diode_SMD:D_SMC', 'B560C', {1: 'SW', 2: 'GND'}, (BX, -25.0, 180),
  mpn='B560C (5 A 60 V Schottky)', group=G)
C('C9', '47u 10V', 'V5', 'GND', (20.3, -12.4, 270), G, fp=C1210)
C('C10', '47u 10V', 'V5', 'GND', (23.65, -12.4, 270), G, fp=C1210)
C('C11', '47u 10V', 'V5', 'GND', (27.0, -12.4, 270), G, fp=C1210)
R('R7', '53.6k', 'V5', 'BUCK_FB', (BX + 5.1, BY + 2.0, 90), G)
R('R8', '10.2k', 'BUCK_FB', 'GND', (BX + 5.1, BY + 5.4, 90), G)
R('R9', '16.9k', 'BUCK_COMP', 'COMP_RC', (BX + 1.8, BY + 5.0, 90), G)
C('C12', '4n7', 'COMP_RC', 'GND', (BX + 1.8, BY + 8.2, 90), G)
C('C13', '47p', 'BUCK_COMP', 'GND', (BX + 0.2, BY + 8.2, 90), G)
P('D5', 'Device:LED', LED0603, 'groen 5V', {1: 'GND', 2: 'LED5_A'}, (BX - 3.0, BY + 8.6, 90), mpn='LED 0603 green', group=G)
R('R10', '2k2', 'V5', 'LED5_A', (BX - 1.4, BY + 8.6, 90), G)

# ---------------------------------------------------------------- motor drivers (DRV8871: IN1/IN2, current limit 64/R_ILIM = 3.55 A)
for i, (u, ref_c, ref_c2, rl, j, y, in1, in2) in enumerate((('U4', 'C20', 'C21', 'R20', 'J2', -1.5, 4, 5),
                                                          ('U5', 'C22', 'C23', 'R21', 'J3', 8.0, 6, 7)), 1):
    G = f'Motor {i} (DRV8871)'
    P(u, 'Driver_Motor:DRV8871DDA', 'Package_SO:Texas_HTSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.95x4.9mm_Mask2.4x3.1mm_ThermalVias',
      'DRV8871', {1: 'GND', 2: f'M{i}_IN2', 3: f'M{i}_IN1', 4: f'M{i}_ILIM', 5: 'VBUS', 6: f'M{i}_A', 7: 'GND', 8: f'M{i}_B', 9: 'GND'},
      (-18.7, y, 0), mpn='DRV8871DDAR (3.6 A H-bridge)', group=G)
    C(ref_c, '10u 25V', 'VBUS', 'GND', (-12.2, y - 1.0, 90), G, fp=C1206)
    C(ref_c2, '100n', 'VBUS', 'GND', (-10.2, y - 1.0, 90), G)
    R(rl, '18k', f'M{i}_ILIM', 'GND', (-18.7, y + 3.8, 0), G)
    P(j, 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P5mm_M', f'MOTOR {i}', {1: f'M{i}_A', 2: f'M{i}_B'},
      (-30.0, y, 0), mpn='solder pads, motor leads', group=G)

# ---------------------------------------------------------------- 3.3 V
G = '3,3 V (ESP32 + INA226)'
P('D6', 'Diode:SS14', 'Diode_SMD:D_SMA', 'SS14', {1: 'V5_ESP', 2: 'V5'}, (14.0, 15.0, 0), mpn='SS14', group=G)
P('D7', 'Diode:SS14', 'Diode_SMD:D_SMA', 'SS14', {1: 'V5_ESP', 2: 'VBUS_USB'}, (14.0, 18.6, 0), mpn='SS14', group=G)
P('U2', 'Regulator_Linear:AMS1117-3.3', 'Package_TO_SOT_SMD:SOT-223-3_TabPin2', 'AMS1117-3.3',
  {1: 'GND', 2: '3V3', 3: 'V5_ESP'}, (6.5, 2.5, 0), mpn='AMS1117-3.3', group=G)
C('C14', '10u', 'V5_ESP', 'GND', (0.8, 2.0, 90), G, fp=C0805)
C('C15', '22u', '3V3', 'GND', (8.0, -2.4, 0), G, fp=C0805)
C('C16', '100n', '3V3', 'GND', (4.4, -2.4, 0), G)

# ---------------------------------------------------------------- ESP32-S3
G = 'ESP32-S3'
P('U3', 'RF_Module:ESP32-S3-WROOM-1', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8',
  {1: 'GND', 40: 'GND', 41: 'GND', 2: '3V3', 3: 'ESP_EN',
   4: 'M1_IN1', 5: 'M1_IN2', 6: 'M2_IN1', 7: 'M2_IN2',      # IO4 IO5 IO6 IO7
   17: 'SERVO_PWM', 18: 'HALL', 19: 'LIGHT_G',              # IO9 IO10 IO11
   12: 'PANEL_ADC', 20: 'LED_ESP',                          # IO8 IO12
   39: 'I2C_SDA', 38: 'I2C_SCL',                            # IO1 IO2
   10: 'ESP_TX', 11: 'ESP_RX',                              # IO17 IO18
   13: 'ESP_DM', 14: 'ESP_DP', 27: 'ESP_IO0'},
  (ESP[0], ESP[1], 180), mpn='ESP32-S3-WROOM-1-N16R8', group=G)
C('C17', '22u', '3V3', 'GND', (4.6, 14.0, 90), G, fp=C0805)
C('C18', '100n', '3V3', 'GND', (6.4, 14.0, 90), G)
R('R11', '10k', '3V3', 'ESP_EN', (-20.0, 14.2, 90), G)
C('C19', '1u', 'ESP_EN', 'GND', (-21.8, 14.2, 90), G)
R('R12', '10k', '3V3', 'ESP_IO0', (-23.6, 14.2, 90), G)
P('SW1', 'Switch:SW_Push', 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2', 'RESET', {1: 'ESP_EN', 2: 'GND'}, (-23.5, 21.5, 90),
  mpn='CK KMR221G (4.2x2.8 tact)', group=G)
P('SW2', 'Switch:SW_Push', 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2', 'BOOT', {1: 'ESP_IO0', 2: 'GND'}, (-19.5, 21.5, 90),
  mpn='CK KMR221G (4.2x2.8 tact) - also race-mode button', group=G)
P('D8', 'Device:LED', LED0603, 'geel ESP', {1: 'GND', 2: 'LED_ESP_A'}, (17.5, 5.5, 0), mpn='LED 0603 yellow', group=G)
R('R13', '1k', 'LED_ESP', 'LED_ESP_A', (14.2, 5.5, 0), G)
# Pi can reset the ESP32 / put it in download mode (flash over the UART from the Pi with esptool)
P('Q2', 'Transistor_FET:2N7002', SOT23, '2N7002', {1: 'PI_ESP_EN', 2: 'GND', 3: 'ESP_EN'}, (-9.5, -25.8, 0), mpn='2N7002', group=G)
R('R14', '100k', 'PI_ESP_EN', 'GND', (-9.5, -22.8, 0), G)
P('Q3', 'Transistor_FET:2N7002', SOT23, '2N7002', {1: 'PI_ESP_BOOT', 2: 'GND', 3: 'ESP_IO0'}, (-5.5, -25.8, 0), mpn='2N7002', group=G)
R('R15', '100k', 'PI_ESP_BOOT', 'GND', (-5.5, -22.8, 0), G)

# ---------------------------------------------------------------- USB-C (flash/debug from the Mac)
G = 'USB-C ESP32'
P('J8', 'Connector:USB_C_Receptacle_USB2.0_16P', USBC, 'USB-C',
  {'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'SH': 'GND', 'A4': 'VBUS_USB', 'A9': 'VBUS_USB',
   'B4': 'VBUS_USB', 'B9': 'VBUS_USB', 'A5': 'CC1', 'B5': 'CC2', 'A6': 'ESP_DP', 'B6': 'ESP_DP',
   'A7': 'ESP_DM', 'B7': 'ESP_DM'}, (22.5, 31.2, 0), mpn='HRO TYPE-C-31-M-12', group=G)
R('R27', '5k1', 'CC1', 'GND', (18.6, 23.6, 90), G)
R('R28', '5k1', 'CC2', 'GND', (26.4, 23.6, 90), G)
P('U10', 'Power_Protection:USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6', 'USBLC6-2SC6',
  {1: 'ESP_DP', 6: 'ESP_DP', 3: 'ESP_DM', 4: 'ESP_DM', 2: 'GND', 5: 'VBUS_USB'}, (22.5, 23.0, 0), mpn='USBLC6-2SC6', group=G)
C('C29', '1u', 'VBUS_USB', 'GND', (18.6, 19.6, 90), G)

# ---------------------------------------------------------------- Raspberry Pi 4 header (socket underneath the board)
G = 'Raspberry Pi 4 (40-pin)'
pi = {2: 'V5', 4: 'V5', 7: 'PI_ESP_EN', 8: 'PI_TXD', 10: 'PI_RXD', 11: 'PI_ESP_BOOT'}
for n in (6, 9, 14, 20, 25, 30, 34, 39):
    pi[n] = 'GND'
P('J9', 'Connector_Generic:Conn_02x20_Odd_Even', 'Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical', 'PI 4',
  pi, (HDR1[0], HDR1[1], 270), mpn='2x20 socket 2.54 mm, 8.5 mm (on the bottom side, onto the Pi 4 header)', group=G, side='B')
R('R16', '1k', 'ESP_TX', 'PI_RXD', (-1.0, -25.8, 0), G)    # series resistors: no back-powering of an unpowered Pi
R('R17', '1k', 'PI_TXD', 'ESP_RX', (-1.0, -23.9, 0), G)

# ---------------------------------------------------------------- connectors: servo, hall, I2C, panel, lights
G = 'Aansluitingen'
P('J4', 'Connector_Generic:Conn_01x03', HDR3, 'SERVO', {1: 'GND', 2: 'V5', 3: 'SERVO_SIG'}, (29.5, -6.0, 0),
  mpn='1x3 pin header 2.54 (MG90S: brown GND, red 5 V, orange signal)', group=G)
R('R18', '100', 'SERVO_PWM', 'SERVO_SIG', (25.5, -4.0, 90), G)
P('J5', 'Connector_Generic:Conn_01x03', HDR3, 'HALL', {1: 'GND', 2: 'V5', 3: 'HALL'}, (-29.5, 23.5, 0),
  mpn='1x3 pin header 2.54 (A3144: GND, 5 V, out)', group=G)
R('R19', '10k', 'HALL', '3V3', (-26.5, 23.5, 90), G)
P('J7', 'Connector_Generic_MountingPin:Conn_01x04_MountingPin', 'Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal',
  'I2C', {1: 'GND', 2: '3V3', 3: 'I2C_SDA', 4: 'I2C_SCL', 'MP': 'GND'}, (-1.5, -17.0, 0), mpn='JST SM04B-SRSS-TB (Qwiic / STEMMA QT)', group=G)
R('R24', '4k7', 'I2C_SDA', '3V3', (-8.3, -19.0, 90), G)
R('R25', '4k7', 'I2C_SCL', '3V3', (-8.3, -15.8, 90), G)
P('J6', 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P4mm_S', 'ZONNEPANEEL', {1: 'GND', 2: 'PANEL'}, (19.6, 13.6, 0),
  mpn='solder pads, solar panel 5 V (measured only)', group=G)
R('R22', '100k', 'PANEL', 'PANEL_ADC', (15.5, 22.4, 90), G)
R('R23', '33k', 'PANEL_ADC', 'GND', (15.5, 25.6, 90), G)
P('J10', 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P4mm_S', 'LICHTEN', {1: 'LIGHT_D', 2: 'V5'}, (29.5, 4.0, 270),
  mpn='solder pads, LED lights 5 V (with their own resistors), low-side switched', group=G)
P('Q4', 'Transistor_FET:AO3400A', SOT23, 'AO3400A', {1: 'LIGHT_G', 2: 'GND', 3: 'LIGHT_D'}, (22.5, 1.5, 0), mpn='AO3400A', group=G)
R('R26', '100k', 'LIGHT_G', 'GND', (22.5, -1.6, 0), G)

# ---------------------------------------------------------------- mounting (Pi 4 pattern)
for i, (x, y) in enumerate(PI_HOLES, 1):
    P(f'H{i}', 'Mechanical:MountingHole', 'sc02:MountingHole_2.75mm_M2.5_Pi', 'M2.5', {}, (x, y, 0), group='Bevestiging')

NETCLASS = {
    'POWER12': (['VBAT_RAW', 'VBAT_P', 'VBUS', 'M1_A', 'M1_B', 'M2_A', 'M2_B'], 1.0, 0.2),
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


def outline(inset=0.0, n=8):
    import math
    x0, y0, x1, y1 = -BOARD_W / 2 + inset, -BOARD_H / 2 + inset, BOARD_W / 2 - inset, BOARD_H / 2 - inset
    r = CORNER_R - inset; pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((round(cx + r * math.cos(a), 4), round(cy + r * math.sin(a), 4)))
    return pts + pts[:1]


if __name__ == '__main__':
    json.dump({'edge': outline(), 'inner': outline(0.3)}, open(os.path.join(HERE, 'outline.json'), 'w'))
    print('outline.json written')
