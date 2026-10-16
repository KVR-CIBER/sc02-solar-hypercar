# SC-02 · Printbestanden voor de Bambu P1S

| Map | Wat erin zit |
|---|---|
| `platen/` | **1 STEP per printplaat.** Alles staat al in printpositie en past samen op de plaat van 256 × 256 mm. Sleep het bestand in Bambu Studio en druk op *Slice*. |
| `onderdelen/` | Elk onderdeel apart als STEP, ook in printpositie. Handig als je één stuk opnieuw wilt printen of wilt aanpassen in Fusion/Onshape. |
| `bambu_3mf/` | Dezelfde platen, al gesliced met instellingen (supports, filament). Openen en printen. |

## De platen

| Plaat | Wat | Prototype in PLA? | Echte versie | ± gewicht / tijd |
|---|---|---|---|---|
| 1 | body achter (hoofddeel) | ✅ ja | ASA | 123 g · 9u20 |
| 2 | body neus | ✅ ja | ASA | 112 g · 8u40 |
| 3 | koepel | ✅ ja (zwart PLA) | smoke PETG | 22 g · 1u10 |
| 4 | chassisdelen (27 stuks) | ⚠️ ja, behalve `rear_module` + `motor_clamp` (zie onder) | ASA | 42 g · 2u40 |
| 5 | achtervleugel, splitter, diffuser | ✅ ja | ASA | 58 g · 3u40 |
| 6 | 4 velgen + 2 tandwielen | ✅ ja (is al PLA) | PLA | 33 g · 1u50 |
| 7a | bandenmal onderkant + 4 kernen | ✅ ja (is al PLA) | PLA | 122 g · 2u40 |
| 7b | bandenmal bovenkant | ✅ ja (is al PLA) | PLA | 90 g · 2u00 |
| 8 | optie: banden printen i.p.v. gieten | ❌ moet TPU zijn | TPU 95A | 34 g · 2u30 |

## Moet het echt ASA zijn?
**Nee, voor een prototype is PLA prima.** Het past even goed, print makkelijker en ruikt niet. Zet in Bambu Studio dan wel het filament op PLA, want de 3mf's staan op ASA.

Waar PLA zwakker is:
- **Warmte.** PLA wordt zacht vanaf ± 55–60 °C. De 130-motortjes kunnen bij hard rijden zo warm worden.
  - Print `rear_module` en `motor_clamp` daarom liefst in **PETG** of ASA.
  - In PLA gaat het voor korte testritjes, maar voel na een rit of de motorwieg niet zacht wordt.
- **Zon.** Een rode PLA-body die in de zon of in een hete auto ligt, kan kromtrekken. Voor de wedstrijd buiten dus liefst ASA.
- **Brosser.** De kleine clipjes, de stuurstangen en de stuurhoorn kunnen bij een crash sneller breken. Print er een paar reserve.

Wil je PLA in de plaats van ASA? Kies in Bambu Studio *Bambu PLA Basic* en laat de supports (tree) aan.
Voor ASA: deur van de P1S dicht, en zorg voor ventilatie in de kamer.

Let op: de 2 bodydelen zijn sinds deze versie **volledig dicht** (achterpaneel en neus). Daardoor zijn ze ± 50 g zwaarder dan in de vorige versie.
