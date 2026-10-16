"""SC-02 'Solar F1' – all dimensions in mm.  x = forward (rear axle at x=0), y = left, z = up (ground z=0)."""

# --- floor: laser-cut 2 mm black acrylic ---
FLOOR_Z = 4.0              # ride height (underside of the floor)
FLOOR_T = 2.0
FLOOR_TOP = FLOOR_Z + FLOOR_T

# --- wheels (F1 proportions: wide rears, narrower fronts) ---
WB = 230.0                 # wheelbase
REAR_D, REAR_W = 44.0, 20.0
FRONT_D, FRONT_W = 42.0, 15.0
TRACK_R = 170.0            # wheel centre to wheel centre
TRACK_F = 166.0
AXLE_RZ = REAR_D / 2
AXLE_FZ = FRONT_D / 2
TYRE_T = 4.0               # tyre section height (bike-style tyre with bead)
RIM_R = lambda D: D / 2 - TYRE_T   # rim flange radius

# --- bought parts ---
AXLE_D = 3.0
BRG = (7.0, 3.0, 3.0)      # 683ZZ OD, ID, width
BRG_FIT = 7.08
PRESS_BORE = 2.90
MODULE, PINION_Z, SPUR_Z, GEAR_W = 0.5, 8, 42, 4.0
CD = MODULE * (PINION_Z + SPUR_Z) / 2 + 0.08
SPUR_Y = -8.0
MOT_W, MOT_T, MOT_L, MOT_BOSS, MOT_SHAFT = 20.1, 15.1, 25.2, 6.2, 8.5
PANEL = (90.0, 80.0, 3.0)  # kit panel x, y, thickness
PI4 = (85.0, 56.0, 1.6)    # board; holes 58 x 49, 3.5 mm from the edge
PI4_HOLES = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]
ESP = (69.0, 26.0)         # ESP32-S3 DevKitC-1
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
DECK_Z = 47.5              # top of the solar deck
PANEL_X0 = 34.0            # rear edge of the panel pocket

# --- layout of the inside ---
BAY = (33.0, 111.0, 34.0)  # battery bay x0, x1, half width (4xAA holders OR 3S LiPo 75x35x25)
PI_X0 = 113.0              # Pi 4 rear edge (long side along x)
SERVO_X = 214.0            # servo output shaft (shaft points DOWN, horn just above the floor)
KINGPIN_Y = 64.0
STEER_MAX = 25.0           # deg
