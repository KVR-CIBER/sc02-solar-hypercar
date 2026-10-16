"""Resolve Bambu Studio profile inheritance into one flat JSON (the CLI does not do it)."""
import json, os, sys
BBL = "/Applications/BambuStudio.app/Contents/Resources/profiles/BBL"
def find(name, kind):
    p = os.path.join(BBL, kind, name + ".json")
    if os.path.exists(p): return p
    for root, _, files in os.walk(BBL):
        if name + ".json" in files: return os.path.join(root, name + ".json")
    raise FileNotFoundError(name)
def load(name, kind):
    d = json.load(open(find(name, kind)))
    if d.get("inherits"):
        base = load(d["inherits"], kind); base.update(d); d = base
    return d
def flat(name, kind, out, **over):
    d = load(name, kind); d.pop("inherits", None); d.update(over)
    d["from"] = "system"
    key = {"machine": "printer_settings_id", "process": "print_settings_id", "filament": "filament_settings_id"}[kind]
    d[key] = d["name"] if kind != "filament" else [d["name"]]
    json.dump(d, open(out, "w"), indent=1)
if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    flat("Bambu Lab P1S 0.4 nozzle", "machine", os.path.join(here, "machine.json"), curr_bed_type="Textured PEI Plate")
    flat("0.20mm Standard @BBL X1C", "process", os.path.join(here, "process_std.json"),
         wall_loops="3", sparse_infill_density="20%", curr_bed_type="Textured PEI Plate", compatible_printers=["Bambu Lab P1S 0.4 nozzle"], compatible_printers_condition="")
    flat("0.20mm Standard @BBL X1C", "process", os.path.join(here, "process_support.json"),
         wall_loops="3", sparse_infill_density="12%", curr_bed_type="Textured PEI Plate", enable_support="1", support_type="tree(auto)",
         support_threshold_angle="35", compatible_printers=["Bambu Lab P1S 0.4 nozzle"], compatible_printers_condition="")
    flat("0.12mm Fine @BBL X1C", "process", os.path.join(here, "process_fine.json"),
         wall_loops="3", sparse_infill_density="25%", curr_bed_type="Textured PEI Plate", compatible_printers=["Bambu Lab P1S 0.4 nozzle"], compatible_printers_condition="")
    for n, f in (("asa", "Bambu ASA @BBL X1C"), ("pla", "Bambu PLA Basic @BBL X1C"),
                 ("petg", "Bambu PETG Basic @BBL X1C"), ("tpu", "Bambu TPU 95A @BBL X1C")):
        flat(f, "filament", os.path.join(here, f"filament_{n}.json"), compatible_printers=["Bambu Lab P1S 0.4 nozzle"], compatible_printers_condition="")
    print("ok")
