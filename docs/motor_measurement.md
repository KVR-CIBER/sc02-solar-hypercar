# Measure your motors (makes the simulation honest)

The motor values in `sim/motors.json` are estimates. Three measurements per motor (15 min, with a multimeter + phone) fix that. Then run `sim/sim.py` and `sim/plots.py` again.

| Value | How | Formula |
|---|---|---|
| **R** (ohm) | Hold the shaft still (pliers on the pinion) and give **1.0 V** from a lab supply, or one AA cell with the multimeter in series on the 10 A range. Read the current **I_stall** immediately (< 2 s, it gets hot). Do it at 3 rotor positions and average. | R = V / I_stall − 0.05 (meter + wires) |
| **I0** (A) | Run the motor free at 3.0 V and read the current. | I0 = I_free |
| **ke** (V·s/rad) | Run free at 3.0 V. Measure the speed: phone app "Strobe/Tachometer", or put a piece of tape on the shaft and record a 240 fps slow-motion video and count turns. | ke = (V − I0·R) / (rpm · π/30) |

Example: 3.0 V, 21 000 rpm, 0.55 A free, 6.2 A stalled at 3.0 V → R = 0.43 Ω, ke = (3.0 − 0.24)/2199 = 0.00126.

Then add the motor to `sim/motors.json`:
```json
"my_hd3": {"name": "My Hyper-Dash 3 (measured)", "ke": 0.00126, "R": 0.43, "I0": 0.55, "J": 1.1e-7, "m": 0.019, "price": 8.5, "pinion_bore": 2.0}
```
For two motors in parallel, `plots.py` builds the pair from `tamiya_hd3` (R/2, 2·I0, 2·J, 2·m). Point that line at your measured key (e.g. `motors["my_hd3"]`) and run `plots.py` again.

## Battery resistance (Rb)

This is the second big unknown (0.25 Ω → 2.21 s, 0.50 Ω → 2.57 s).
Measure the pack in its holders: open-circuit voltage **V0**, then load it with the motors stalled for 1 s (car held still, full throttle) and read **V1** and **I** (clamp meter, or calculate it from R).
**Rb = (V0 − V1) / I**. With the car's logger: hold the car still, `g`, release after 1 s. `vbat` in the log shows V1.

Lowering Rb is free speed: clean the holder contacts, solder the wires to the holder tabs (not the cells), use short thick wires, and use a good switch.
