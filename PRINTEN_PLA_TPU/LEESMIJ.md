# SC-02 · printen in PLA + TPU

Elk bestand staat al **in de juiste printstand**. Het getal vooraan (`2x_…`) zegt hoeveel je er moet printen.

## PLA (map `PLA/`)
| Wat | Instellingen |
|---|---|
| `body_main`, `body_nose` | 0,2 mm, **tree supports aan**, 3 wanden, 12 % infill |
| `canopy` | zwart PLA, supports aan |
| `rear_wing` (staat op zijn eindplaat), `splitter`, `diffuser` | supports aan |
| `rim_front`, `rim_rear`, `spur`, `pinion` | **0,12 mm fijn**, 3 wanden, 25 % infill |
| alle kleine delen (modules, fusees, clips, trays …) | 0,2 mm, supports aan |

Let op met PLA:
- `rear_module` + `motor_clamp` houden de motoren vast. Die worden warm: voel na een rit of de wieg niet zacht wordt. Liever 100 % infill voor deze twee.
- Laat de wagen niet in de zon of in een hete auto liggen (PLA wordt zacht vanaf ± 55 °C).
- `pinion` (motortandwiel) is een prototype: later frezen in POM (`cnc_pinion_m0.8_10T.dxf`).

## TPU (map `TPU/`)
`tyre_front`, `tyre_rear`: TPU 95A, 0,2 mm, langzaam (± 25 mm/s), **geen supports**, 100 % infill of 3 wanden + 30 % infill. Rol ze over de velgflens: de randen klikken onder de haken.
