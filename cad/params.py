"""All dimensions in mm. Coordinate system of the car:
x = forward (rear axle at x=0), y = left, z = up (ground at z=0)."""

# --- rules ---
MAX_WIDTH = 300.0          # Challenger rule 2.2
PANEL = (90.0, 80.0)       # kit solar panel (x, y), not modified (rule 4.5)
PANEL_T = 3.0              # panel thickness (measure yours! frame pocket uses PANEL_T + 0.4)

# --- wheels / tyres (from sim/out/final_design.json) ---
WHEEL_D = 40.0
TYRE_T = 2.5               # tyre thickness (radial)
TYRE_W = 10.0              # tyre width == rim width == mold cavity depth
SEAT_D = WHEEL_D - 2 * TYRE_T
TRACK = 121.0              # wheel centre to wheel centre -> overall width 131 mm (rule: <= 300)
WHEELBASE = 170.0
AXLE_Z = WHEEL_D / 2
AXLE_D = 3.0               # 3 mm carbon rod (pultruded), steel rod also fits
PRESS_BORE = 2.90          # hole in printed hubs for a press fit on the 3 mm rod (tune 2.85..2.95)
FREE_BORE = 3.4            # clearance hole for the axle
MAGNET = (3.1, 2.1)        # pocket for 3x2 mm neodymium magnet (wheel-speed sensor)

# --- bearings 683ZZ ---
BRG_OD, BRG_ID, BRG_W = 7.0, 3.0, 3.0
BRG_FIT = 7.08             # pocket diameter (PLA/PETG on P1S: 7.05..7.12)

# --- gears (module 0.5, 20 deg) ---
MODULE = 0.5
PINION_Z = 8               # brass pinion, 2 mm bore (on each motor)
SPUR_Z = 42                # on rear axle
GEAR_W = 4.0
BACKLASH_CD = 0.08         # extra centre distance
CENTRE_DIST = MODULE * (PINION_Z + SPUR_Z) / 2 + BACKLASH_CD
SPUR_Y = -10.0             # spur gear position along the axle

# --- 130-size motor (Tamiya Mini 4WD / Mabuchi FA-130) ---
MOT_W, MOT_T, MOT_L = 20.1, 15.1, 25.2   # round width, flat thickness, can length
MOT_BOSS_D, MOT_SHAFT_L = 6.2, 8.5       # front boss, shaft length past face
MOT_FIT = 0.3                            # clearance in cradle

# --- chassis ---
PLATE_Z = 5.0              # underside of plate above ground
PLATE_T = 1.6
PLATE_TOP = PLATE_Z + PLATE_T
REAR_OVERHANG = 27.0
FRONT_OVERHANG = 18.0
PLATE_HALF_W = 54.5         # bearing-block outer face; wheel inner face at 55.5 (1 mm spacer)

# --- battery holders: 2x "2xAA side by side" (measure the kit holders!) ---
BATT_HOLDER = (58.0, 32.0, 15.5)         # x, y, z with clearance
BATT_X0 = 26.0                           # rear edge of battery bay

# --- panel frame ---
PANEL_X0 = 12.0                          # rear edge of panel
PANEL_Z = 34.0                           # underside of panel frame

# --- fasteners ---
M2_PILOT = 1.7
M3_PILOT = 2.6
M3_CLEAR = 3.3

# --- mass estimates of bought parts (g) and their centre x (mm), for the CG calculation ---
BOUGHT = {
    "4x AA NiMH 2000 mAh":   (108.0, BATT_X0 + BATT_HOLDER[0] / 2),
    "2x battery holder":     (16.0,  BATT_X0 + BATT_HOLDER[0] / 2),
    "solar panel (kit)":     (25.0,  PANEL_X0 + PANEL[0] / 2),
    "2x 130 motor":          (38.0,  0.0),
    "2x axle, 3 mm carbon rod x 132": (3.0, WHEELBASE / 2),
    "4x 683ZZ bearing":      (2.4,   WHEELBASE / 2),
    "ESP32-S3 + buck-boost": (14.0,  BATT_X0 + 76.0),
    "MOSFET module, fuse, switch, wires": (14.0, BATT_X0 + 98.0),
    "magnets, hall sensor, screws": (5.0, 100.0),
}
