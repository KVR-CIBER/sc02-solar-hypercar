"""Print plates for the Bambu P1S: name -> (filament, process, [(part, rot_x, rot_y), ...]). Shared by slicer + STEP export."""
ASA_SMALL = ["rear_module", "motor_clamp", "front_module", "front_upright_L", "front_upright_R", "tie_rod_L", "tie_rod_R",
             "steering_horn", "rear_bearing_L", "rear_bearing_R", "bearing_cap_L", "bearing_cap_R", "wheel_spacer", "wheel_spacer",
             "pcb_posts", "battery_tray", "esc_tray"] + [f"clip_{i}{s}" for i in range(4) for s in "LR"] + ["diffuser"]
PLATES = {
    "1_body_main_ASA": ("asa", "support", [("body_main", 0, 0)]),
    "2_body_nose_ASA": ("asa", "support", [("body_nose", 0, 0)]),
    "3_canopy_smoke_PETG": ("petg", "support", [("canopy", 0, 0)]),
    "4_chassis_parts_ASA": ("asa", "support", [(n, 0, 0) for n in ASA_SMALL]),
    "5_aero_black_ASA": ("asa", "support", [("rear_wing", 90, 0), ("splitter", 0, 0)]),
    "6_wheels_PLA": ("pla", "fine", [("rim_rear", 180, 0)] * 2 + [("rim_front", 180, 0)] * 2 + [("spur", 90, 0)] * 2 + [("pinion", 0, 0)] * 4),
    "7a_tyre_mold_bottom_cores_PLA": ("pla", "std", [("mold_bottom", 0, 0), ("mold_core_rear", 0, 0), ("mold_core_rear", 0, 0),
                                                      ("mold_core_front", 0, 0), ("mold_core_front", 0, 0)]),
    "7b_tyre_mold_top_PLA": ("pla", "std", [("mold_top", 0, 0)]),
    "8_option_TPU_tyres": ("tpu", "std", [("tyre_rear", 0, 0)] * 2 + [("tyre_front", 0, 0)] * 2),
}
