"""SC-02 drive board v3: a compact board on M3 standoffs (the battery sits on top of it), no Raspberry Pi, a built-in
ExpressLRS 2.4 GHz receiver and a real solar-panel connector. Single source of truth for parts, nets and placement.

  * top half  : XT60, 10 A fuse, power switch pads, P-MOSFET reverse protection, INA226 current sense, 5 V 5 A buck
                (exactly the proven layout of v2, only the board around it changed);
  * bottom    : brushless ESC signal header (+ NTC), ESP32-S3 (car brain, USB-C), servo / hall / lights / solar panel, and the
                ELRS receiver: ESP32-C3-MINI-1 + Ebyte E28-2G4M12S (SX1280, 12.5 dBm, PCB antenna) wired exactly like
                ExpressLRS' "Generic C3 2400" target, so the official firmware runs on it without a custom layout.
The C3 talks CRSF (420 kbaud) to the S3 on IO15/IO16; the S3 can also reset the C3 / put it in bootloader (IO17/IO18).
Coordinates: X forward, Y = -car y (KiCad y down); same origin as v2 so the power block keeps its layout.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_T = 1.6
CORNER_R = 3.0
BOARD = (52.0, -68.0, 138.0, 22.0)  # x0, y0, x1, y1: 86 x 90 mm
BOARD_W, BOARD_H = BOARD[2] - BOARD[0], BOARD[3] - BOARD[1]
ESP = (93.0, 9.0)               # ESP32-S3 origin, rotated 180: antenna at the bottom edge (y = 22)
ELRS_RF = (120.5, 12.0)         # E28 origin, rotated 90: its PCB antenna at the right edge (x = 138)
ELRS_MCU = (127.0, -10.0)       # ESP32-C3-MINI-1 origin, rotated 270: antenna at the right edge
MOUNT = [(55.5, 18.5), (77.0, -64.0), (55.5, -30.0), (134.5, -27.0)]   # M3 standoff holes
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
G = 'Buck 5 V 5 A (ESP32, servo, lichten)'
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
P('J7', 'Connector_Generic_MountingPin:Conn_01x04_MountingPin', 'Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal',
  'I2C', {1: 'GND', 2: '3V3', 3: 'I2C_SDA', 4: 'I2C_SCL', 'MP': 'GND'}, l(-1.5, -17.0, 0), mpn='JST SM04B-SRSS-TB (Qwiic / STEMMA QT)', group=G)
R('R24', '4k7', 'I2C_SDA', '3V3', l(-8.3, -19.0, 90), G)
R('R25', '4k7', 'I2C_SCL', '3V3', l(-8.3, -15.8, 90), G)

# ---------------------------------------------------------------- brushless ESC (one 2435 4500 KV motor, 40 A ESC)
# The ESC takes its power straight from the battery (Y-cable on the XT60), so its 40 A never flows through this board.
# The board only sends the throttle signal (50 Hz servo PWM, or DShot) on IO4. The ESC's BEC wire is NOT connected.
G = 'ESC (brushless)'
P('J2', 'Connector_Generic:Conn_01x03', HDR3, 'ESC', {1: 'GND', 3: 'ESC_SIG'}, (60.0, -16.0, 0),
  mpn='1x3 pin header 2.54 (ESC signal lead: black GND, red BEC NOT used, white/yellow signal)', group=G)
R('R20', '100', 'ESC_PWM', 'ESC_SIG', (63.5, -16.0, 90), G)
P('J3', 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P5mm_M', 'ESC TEMP', {1: 'GND', 2: 'ESC_NTC'}, (60.0, -6.0, 270),
  mpn='solder pads: 10k NTC glued on the ESC / motor can (temperature for the boost limit)', group=G)
R('R21', '10k', 'ESC_NTC', '3V3', (64.0, -6.0, 90), G, mpn='0603 10k 1% (NTC divider)')

# ---------------------------------------------------------------- ESP32-S3 + 3.3 V
G = '3,3 V (ESP32 + INA226)'
P('D6', 'Diode:SS14', 'Diode_SMD:D_SMA', 'SS14', {1: 'V5_ESP', 2: 'V5'}, (88.0, -22.5, 0), mpn='SS14', group=G)
P('D7', 'Diode:SS14', 'Diode_SMD:D_SMA', 'SS14', {1: 'V5_ESP', 2: 'VBUS_USB'}, (88.0, -18.7, 0), mpn='SS14', group=G)
P('U2', 'Regulator_Linear:AMS1117-3.3', 'Package_TO_SOT_SMD:SOT-223-3_TabPin2', 'AMS1117-3.3',
  {1: 'GND', 2: '3V3', 3: 'V5_ESP'}, (99.0, -20.0, 0), mpn='AMS1117-3.3', group=G)
C('C14', '10u', 'V5_ESP', 'GND', (93.0, -24.0, 90), G, fp=C0805)
C('C15', '22u', '3V3', 'GND', (99.0, -13.6, 0), G, fp=C0805)
C('C16', '100n', '3V3', 'GND', (95.6, -13.6, 0), G)

G = 'ESP32-S3'
P('U3', 'RF_Module:ESP32-S3-WROOM-1', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8',
  {1: 'GND', 40: 'GND', 41: 'GND', 2: '3V3', 3: 'ESP_EN',
   4: 'ESC_PWM', 5: 'ESC_NTC',                              # IO4 = ESC throttle signal, IO5 = NTC (ADC1)
   17: 'SERVO_PWM', 31: 'HALL', 19: 'LIGHT_G',              # IO9 IO38 IO11
   12: 'PANEL_ADC', 20: 'LED_ESP',                          # IO8 IO12
   39: 'I2C_SDA', 38: 'I2C_SCL',                            # IO1 IO2
   8: 'ELRS_TX', 9: 'ELRS_RX',                              # IO15 = ESP TX -> receiver RX, IO16 = ESP RX <- receiver TX (CRSF)
   10: 'RX_EN_CTL', 11: 'RX_BOOT_CTL',                      # IO17 / IO18: reset + bootloader of the ELRS C3
   13: 'ESP_DM', 14: 'ESP_DP', 27: 'ESP_IO0'},
  (ESP[0], ESP[1], 180), mpn='ESP32-S3-WROOM-1-N16R8', group=G)
C('C17', '22u', '3V3', 'GND', (82.0, -6.0, 90), G, fp=C0805)
C('C18', '100n', '3V3', 'GND', (80.2, -6.0, 90), G)
R('R11', '10k', '3V3', 'ESP_EN', (104.0, 0.0, 90), G)
C('C19', '1u', 'ESP_EN', 'GND', (105.8, 0.0, 90), G)
R('R12', '10k', '3V3', 'ESP_IO0', (107.6, 0.0, 90), G)
P('SW1', 'Switch:SW_Push', 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2', 'RESET', {1: 'ESP_EN', 2: 'GND'}, (107.6, 19.4, 0),
  mpn='CK KMR221G (4.2x2.8 tact)', group=G)
P('SW2', 'Switch:SW_Push', 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2', 'BOOT', {1: 'ESP_IO0', 2: 'GND'}, (107.6, 14.8, 0),
  mpn='CK KMR221G (4.2x2.8 tact) - also the race-mode button', group=G)
P('D8', 'Device:LED', LED0603, 'geel ESP', {1: 'GND', 2: 'LED_ESP_A'}, (104.0, 5.0, 90), mpn='LED 0603 yellow', group=G)
R('R13', '1k', 'LED_ESP', 'LED_ESP_A', (105.8, 5.0, 90), G)

# ---------------------------------------------------------------- USB-C: ESP32 native USB -> Raspberry Pi 4 (C to A cable)
G = 'USB-C (flashen / debug van buitenaf)'
P('J8', 'Connector:USB_C_Receptacle_USB2.0_16P', USBC, 'USB-C',
  {'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'SH': 'GND', 'A4': 'VBUS_USB', 'A9': 'VBUS_USB',
   'B4': 'VBUS_USB', 'B9': 'VBUS_USB', 'A5': 'CC1', 'B5': 'CC2', 'A6': 'ESP_DP', 'B6': 'ESP_DP',
   'A7': 'ESP_DM', 'B7': 'ESP_DM'}, (73.0, 18.2, 0), mpn='HRO TYPE-C-31-M-12 (board edge)', group=G)
R('R27', '5k1', 'CC1', 'GND', (68.5, 10.5, 90), G)
R('R28', '5k1', 'CC2', 'GND', (77.5, 10.5, 90), G)
P('U10', 'Power_Protection:USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6', 'USBLC6-2SC6',
  {1: 'ESP_DP', 6: 'ESP_DP', 3: 'ESP_DM', 4: 'ESP_DM', 2: 'GND', 5: 'VBUS_USB'}, (73.0, 9.5, 0), mpn='USBLC6-2SC6', group=G)
C('C29', '1u', 'VBUS_USB', 'GND', (73.0, 6.5, 0), G)

# ---------------------------------------------------------------- connectors: servo, hall, panel, lights
G = 'Aansluitingen'
P('J4', 'Connector_Generic:Conn_01x03', HDR3, 'SERVO', {1: 'GND', 2: 'V5', 3: 'SERVO_SIG'}, (110.0, -22.5, 90),
  mpn='NOT FITTED: solder the MG90S lead straight into the holes, flat (battery tray sits 8 mm above). Brown GND, red 5 V, orange signal',
  dnp=True, group=G)
R('R18', '100', 'SERVO_PWM', 'SERVO_SIG', (112.0, -18.6, 0), G)
P('J5', 'Connector_Generic:Conn_01x03', HDR3, 'HALL', {1: 'GND', 2: 'V5', 3: 'HALL'}, (57.0, 7.5, 0),
  mpn='1x3 pin header 2.54 (A3144: GND, 5 V, out)', group=G)
R('R19', '10k', 'HALL', '3V3', (60.8, 3.0, 0), G)
P('J6', 'Connector_Generic:Conn_01x02', 'Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical', 'ZONNEPANEEL',
  {1: 'GND', 2: 'PANEL'}, (70.0, -33.0, 0), mpn='JST XH 2-pin (B2B-XH-A): plug the solar panel in (5 V 1 W)', group=G)
R('R22', '100k', 'PANEL', 'PANEL_ADC', (77.0, -35.0, 90), G)
R('R23', '33k', 'PANEL_ADC', 'GND', (78.8, -35.0, 90), G)
# optional: let the panel help the 5 V rail (close JP1). Only with a panel whose open-circuit voltage is <= 6 V!
P('D9', 'Diode:SS14', 'Diode_SMD:D_SMA', 'SS14', {1: 'PANEL_D', 2: 'PANEL'}, (73.0, -26.2, 0), mpn='SS14 (solar -> 5 V)', group=G)
P('JP1', 'Jumper:SolderJumper_2_Open', 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm', 'ZON>5V',
  {1: 'PANEL_D', 2: 'V5'}, (79.0, -26.2, 0), mpn='solder jumper (open): solar panel feeds the 5 V rail', group=G)
P('J10', 'Connector_Generic:Conn_01x02', 'sc02:SolderWire_2pad_P4mm_S', 'LICHTEN', {1: 'LIGHT_D', 2: 'V5'}, (60.5, 18.8, 0),
  mpn='solder pads, LED lights 5 V (with their own resistors), low-side switched', group=G)
P('Q4', 'Transistor_FET:AO3400A', SOT23, 'AO3400A', {1: 'LIGHT_G', 2: 'GND', 3: 'LIGHT_D'}, (63.5, 12.5, 0), mpn='AO3400A', group=G)
R('R26', '100k', 'LIGHT_G', 'GND', (63.5, 9.4, 0), G)

# ---------------------------------------------------------------- built-in ExpressLRS 2.4 GHz receiver ("Generic C3 2400")
G = 'ELRS-ontvanger (ESP32-C3 + SX1280)'
rx, ry = ELRS_MCU
P('U11', 'sc02:ESP32-C3-MINI-1', 'sc02:WIFIM-SMD_ESP32-C3-MINI-1', 'ESP32-C3-MINI-1-N4',
  {1: 'GND', 2: 'GND', 11: 'GND', 14: 'GND', **{n: 'GND' for n in range(36, 54)}, 3: '3V3_RX', 8: 'RX_EN',
   13: 'RF_DIO1', 5: 'RF_RST', 6: 'RF_BUSY', 18: 'RF_MOSI', 19: 'RF_MISO', 20: 'RF_SCK', 21: 'RF_NSS',
   22: 'RX_LED', 23: 'RX_BOOT', 26: 'RX_USB_DM', 27: 'RX_USB_DP', 30: 'RX_SERIAL_IN', 31: 'RX_SERIAL_OUT'},
  (rx, ry, 270), mpn='ESP32-C3-MINI-1-N4 (ELRS receiver MCU, flash "Generic C3 2400")', group=G)
P('U12', 'sc02:E28-2G4M12S', 'sc02:WIRELM-SMD_E28-2G4M12S', 'E28-2G4M12S',
  {1: '3V3_RX', 2: 'GND', 7: 'GND', 8: 'GND', 14: 'GND', 3: 'RF_MISO', 4: 'RF_MOSI', 5: 'RF_SCK', 6: 'RF_NSS',
   9: 'RF_RST', 10: 'RF_BUSY', 11: 'RF_DIO1'},
  (ELRS_RF[0], ELRS_RF[1], 90), mpn='Ebyte E28-2G4M12S (SX1280 2.4 GHz, 12.5 dBm, PCB antenna)', group=G)
P('U13', 'Regulator_Linear:AMS1117-3.3', 'Package_TO_SOT_SMD:SOT-223-3_TabPin2', 'AMS1117-3.3',
  {1: 'GND', 2: '3V3_RX', 3: 'V5'}, (125.0, -24.0, 0), mpn='AMS1117-3.3 (receiver supply)', group=G)
C('C30', '10u', 'V5', 'GND', (119.0, -26.5, 90), G, fp=C0805)
C('C31', '22u', '3V3_RX', 'GND', (131.0, -24.0, 90), G, fp=C0805)
C('C32', '100n', '3V3_RX', 'GND', (rx - 7.5, ry - 7.0, 90), G)
C('C33', '10u', '3V3_RX', 'GND', (113.6, 2.6, 0), G, fp=C0805)
C('C34', '100n', '3V3_RX', 'GND', (113.6, 0.6, 0), G)
R('R31', '10k', '3V3_RX', 'RX_EN', (rx - 7.5, ry + 1.0, 90), G)
C('C35', '1u', 'RX_EN', 'GND', (rx - 9.3, ry + 1.0, 90), G)
R('R32', '10k', '3V3_RX', 'RX_BOOT', (rx - 7.5, ry + 4.6, 90), G)
R('R33', '10k', '3V3_RX', 'RX_LED', (rx - 9.3, ry + 4.6, 90), G, mpn='0603 10k (IO8 strapping pin high at boot)')
R('R34', '1k', 'RX_EN_CTL', 'RX_EN', (rx - 11.1, ry + 1.0, 90), G, mpn='0603 1k (S3 can reset the receiver)')
R('R35', '1k', 'RX_BOOT_CTL', 'RX_BOOT', (rx - 11.1, ry + 4.6, 90), G, mpn='0603 1k (S3 can start the receiver bootloader)')
R('R29', '100', 'RX_SERIAL_OUT', 'ELRS_RX', (rx - 12.9, ry + 1.0, 90), G)      # C3 TX -> S3 RX (IO16), CRSF
R('R30', '100', 'ELRS_TX', 'RX_SERIAL_IN', (rx - 12.9, ry + 4.6, 90), G)      # S3 TX (IO15) -> C3 RX
P('SW3', 'Switch:SW_Push', 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2', 'BIND', {1: 'RX_BOOT', 2: 'GND'}, (108.6, -5.6, 0),
  mpn='CK KMR221G: ELRS bind / bootloader button', group=G)
P('D10', 'sc02:SK6812MINI-E', 'sc02:LED-SMD_4P-L3.2-W2.8-LS5.9_SK6812MINI-E', 'SK6812MINI-E',
  {1: 'GND', 2: 'RX_LED', 3: '3V3_RX'}, (110.8, 9.4, 0), mpn='SK6812MINI-E (ELRS status LED, RGB)', group=G)
P('J12', 'Connector_Generic:Conn_01x03', 'sc02:Pads_RX_USB', 'RX USB', {1: 'RX_USB_DM', 2: 'RX_USB_DP', 3: 'GND'},
  (112.0, -31.5, 0), mpn='test pads: USB D-/D+/GND of the receiver C3 (first flash)', group=G)

# ---------------------------------------------------------------- mounting: 4x M3 on standoffs (battery on top of the board)
for i, (x, y) in enumerate(MOUNT, 1):
    P(f'H{i}', 'Mechanical:MountingHole', 'sc02:Hole_3.2mm', 'M3', {}, (x, y, 0), group='Bevestiging')
HOLE_SIZES = [3.2]

NETCLASS = {
    'POWER12': (['BAT_IN', 'BAT_F', 'VBAT_RAW', 'VBAT_P', 'VBUS'], 1.0, 0.2),
    'POWER5': (['V5', 'SW'], 0.6, 0.2),
    'PWR': (['3V3', '3V3_RX', 'V5_ESP', 'VBUS_USB', 'GND', 'LIGHT_D', 'PANEL', 'PANEL_D'], 0.35, 0.15),
    'USB': (['ESP_DP', 'ESP_DM'], 0.25, 0.15),
}
DNP = set()


def nets():
    s = set()
    for p in parts:
        s |= set(p['pins'].values())
    return sorted(s)


def outline(inset=0.0, n=8):
    """rounded rectangle (closed)"""
    import math
    x0, y0, x1, y1 = BOARD[0] + inset, BOARD[1] + inset, BOARD[2] - inset, BOARD[3] - inset
    r = CORNER_R - inset; pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((round(cx + r * math.cos(a), 4), round(cy + r * math.sin(a), 4)))
    return pts + pts[:1]


if __name__ == '__main__':
    json.dump({'edge': outline(), 'inner': outline(0.3)}, open(os.path.join(HERE, 'outline.json'), 'w'))
    print('outline.json written')
