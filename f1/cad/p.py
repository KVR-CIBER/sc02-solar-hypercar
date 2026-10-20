"""SC-02 'Solar Hypercar' (closed wheels, Le Mans style) – all dimensions in mm.  x = forward (rear axle at x=0), y = left, z = up (ground z=0)."""

# --- floor: laser-cut 2 mm black acrylic ---
FLOOR_Z = 4.0              # ride height (underside of the floor)
FLOOR_T = 2.0
FLOOR_TOP = FLOOR_Z + FLOOR_T

# --- wheels (F1 proportions: wide rears, narrower fronts) ---
WB = 230.0                 # wheelbase
REAR_D, REAR_W = 44.0, 20.0
FRONT_D, FRONT_W = 42.0, 15.0
TRACK_R = 150.0            # wheel centre to wheel centre (wheels sit inside the fenders)
TRACK_F = 146.0
AXLE_RZ = REAR_D / 2
AXLE_FZ = FRONT_D / 2
TYRE_T = 4.0               # tyre section height (bike-style tyre with bead)
RIM_R = lambda D: D / 2 - TYRE_T   # rim flange radius

# --- bought parts ---
AXLE_D = 3.0
BRG = (7.0, 3.0, 3.0)      # 683ZZ OD, ID, width
BRG_FIT = 7.08
PRESS_BORE = 2.90
MODULE, PINION_Z, SPUR_Z, GEAR_W = 0.8, 11, 35, 4.0     # m0.8: CNC-able (0.8 mm cutter); 35:11 = 3.18:1 for the 2435 brushless (sim: ~80 km/h, boost ~120)
CD = MODULE * (PINION_Z + SPUR_Z) / 2 + 0.08
SPUR_Y = -8.0
MOT_D, MOT_L, MOT_BOSS, MOT_SHAFT, MOT_SHAFT_D = 24.0, 35.0, 8.0, 12.0, 3.175   # 2435 sensorless inrunner (4500 kV), shaft 3.175 x 12
MOT_HOLES = 16.0             # 2x M3 in the motor face, 16 mm apart (most 2430/2435 cans; check yours)
ESC = (32.0, 25.0, 15.0)     # 1/16 brushless car ESC (25-35 A class) incl. heatsink, x y z
PANEL = (60.0, 110.0, 3.0)  # AliExpress 1 W 5 V panel 110 x 60, mounted crosswise (x = 60 along the car, y = 110 across); measure thickness!
SERVO = (22.8, 12.2, 22.7, 32.3)   # MG90S body x, y, height to flange top region, flange length

# --- body styling (sections: x, half width, z bottom, z top, top radius) ---
SPINE = [
    (-36, 18, 6, 25, 8),
    (-16, 30, 6, 34, 12),
    (6, 40, 6, 40, 14),
    (30, 50, 6, 47.5, 7),
    (130, 50, 6, 47.5, 7),
    (142, 40, 6, 62, 14),
    (156, 24, 6, 74, 12),
    (168, 28, 6, 54, 14),
    (205, 28, 6, 47, 13),
    (222, 24, 11, 44, 12),
    (262, 16, 12, 33, 9),
    (300, 11, 12.5, 25, 6),
    (336, 5, 13, 18.5, 3),
]
PODS = [                   # both sidepods as one wide loft (merges with the spine)
    (-14, 44, 6, 20, 9),
    (20, 64, 6, 30, 12),
    (52, 74, 6, 36, 14),
    (148, 74, 6, 37, 14),
    (170, 66, 6, 33, 12),
]
WALL = 1.2                 # body wall (3 perimeters)
DECK_Z = 42.0              # top of the solar deck (rear deck, flat between the fenders)
PANEL_X0 = 54.0            # rear edge of the panel pocket (panel centred on the flat deck 36..132)

# --- layout of the inside ---
# drive PCB v3 (f1/pcb, 86 x 90) on 4 mm standoffs; board coordinates (bx, by) of f1/pcb/tools/design.py -> car:
#   x = PCB_X0 + (by - BOARD_Y0), y = bx - PCB_YC   (90 mm side along the car, parts up, XT60 at the rear right)
PCB_X0, PCB_YC, BOARD_Y0 = 38.0, 95.0, -68.0
PCB_Z0, PCB_T = 10.0, 1.6     # underside of the board / thickness
PCB_HOLES_B = [(55.5, 18.5), (77.0, -64.0), (55.5, -30.0), (134.5, -27.0)]   # MOUNT in f1/pcb/tools/design.py
LIPO = (72.0, 35.0, 14.0)     # 2S 1000 mAh (72 x 35 x 14) on the tray above the PCB
TRAY_Z = 19.6                 # underside of the battery tray (8 mm above the board: clears modules + angled servo header)
SERVO_X = 214.0            # servo output shaft (shaft points DOWN, horn just above the floor)
KINGPIN_Y = 64.0
STEER_MAX_HW = 20.0         # mechanical steering limit inside the wheel arch (deg)
STEER_MAX = 25.0           # deg
