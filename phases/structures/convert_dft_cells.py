"""Convert the 8 DFT cells of the preliminary phases work into this repo's LAMMPS data format.

    python phases/structures/convert_dft_cells.py      (any python 3 with numpy; reads $DFT_PHASES, common/model.sh)

Source: $DFT_PHASES/<amorph|cubic|hex>/<gst|c1|c5|c10>/lammps/*.data (OVITO 3.4.4, written from the DFT-MD cells).
Output: phases/structures/<phase>.data with the same box (DFT size and density, triclinic tilts kept), the same atom
order (the DFT per-atom DOS is indexed by it: group i = atom i), 4 atom types in the model's order (1 Ge, 2 Sb,
3 Te, 4 C, type 4 present even without C), a Masses section, and every atom wrapped into the box (some OVITO
coordinates sit a few 1e-7 A outside). Fails if the source types are not in Ge, Sb, Te, C blocks.
"""
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
# phase -> source data file, relative to $DFT_PHASES
SRC = {
    "am_gst": "amorph/gst/lammps/a_gst_300.data",
    "am_c1": "amorph/c1/lammps/c1_a_300.data",
    "am_c5": "amorph/c5/lammps/c5_a_300.data",
    "am_c10": "amorph/c10/lammps/c10_a_300.data",
    "cub_gst": "cubic/gst/lammps/c_gst_300.data",
    "cub_c1": "cubic/c1/lammps/c1_c_300.data",
    "hex_gst": "hex/gst/lammps/h_gst_300.data",
    "hex_c1": "hex/c1/lammps/h_c1_300.data",
}
MASS = {1: 72.630, 2: 121.760, 3: 127.600, 4: 12.011}      # Ge Sb Te C (the masses in.phases relies on)
NAME = {1: "Ge", 2: "Sb", 3: "Te", 4: "C"}


def read_data(path):
    lines = path.read_text().splitlines()
    box = {"xy": 0.0, "xz": 0.0, "yz": 0.0}
    for ln in lines:
        w = ln.split()
        if ln.endswith("xlo xhi"):
            box["x"] = (float(w[0]), float(w[1]))
        elif ln.endswith("ylo yhi"):
            box["y"] = (float(w[0]), float(w[1]))
        elif ln.endswith("zlo zhi"):
            box["z"] = (float(w[0]), float(w[1]))
        elif ln.endswith("xy xz yz"):
            box["xy"], box["xz"], box["yz"] = map(float, w[:3])
    i = next(k for k, ln in enumerate(lines) if ln.startswith("Atoms"))
    rows = [ln.split() for ln in lines[i + 1:] if ln.strip()]
    rows = [r for r in rows if len(r) >= 5 and r[0].isdigit()]
    ids = np.array([int(r[0]) for r in rows])
    types = np.array([int(r[1]) for r in rows])
    pos = np.array([[float(x) for x in r[2:5]] for r in rows])
    o = np.argsort(ids)
    return box, ids[o], types[o], pos[o]


def cell(box):
    lx, ly, lz = (box[d][1] - box[d][0] for d in "xyz")
    return np.array([[lx, 0, 0], [box["xy"], ly, 0], [box["xz"], box["yz"], lz]])   # rows a, b, c (A)


def main():
    root = Path(os.environ.get("DFT_PHASES") or sys.exit("DFT_PHASES not set: source common/model.sh"))
    for phase, rel in SRC.items():
        box, ids, types, pos = read_data(root / rel)
        assert (ids == np.arange(1, len(ids) + 1)).all(), f"{phase}: ids not 1..N"
        assert (np.diff(types) >= 0).all() and set(types) <= set(MASS), f"{phase}: types not in Ge, Sb, Te, C blocks"
        h = cell(box)
        origin = np.array([box[d][0] for d in "xyz"])
        frac = np.linalg.solve(h.T, (pos - origin).T).T
        pos = origin + (frac % 1.0) @ h
        counts = {NAME[t]: int((types == t).sum()) for t in MASS}
        out = [f"# {phase}: DFT cell from $DFT_PHASES/{rel} (phases/structures/convert_dft_cells.py); "
               + " ".join(f"{k} {v}" for k, v in counts.items()), "",
               f"{len(ids)} atoms", "4 atom types", ""]
        out += [f"{box['x'][0]:.10f} {box['x'][1]:.10f} xlo xhi", f"{box['y'][0]:.10f} {box['y'][1]:.10f} ylo yhi",
                f"{box['z'][0]:.10f} {box['z'][1]:.10f} zlo zhi"]
        if any(box[t] != 0.0 for t in ("xy", "xz", "yz")):
            out.append(f"{box['xy']:.10f} {box['xz']:.10f} {box['yz']:.10f} xy xz yz")
        out += ["", "Masses", ""] + [f"{t} {m}  # {NAME[t]}" for t, m in MASS.items()]
        out += ["", "Atoms  # atomic", ""]
        out += [f"{i} {t} {x:.10f} {y:.10f} {z:.10f}" for i, t, (x, y, z) in zip(ids, types, pos)]
        (HERE / f"{phase}.data").write_text("\n".join(out) + "\n")
        vol = abs(np.linalg.det(h))
        print(f"{phase:8s} N {len(ids):3d}  {counts}  V {vol:8.2f} A^3  {vol / len(ids):.3f} A^3/atom"
              f"  wrapped {int((np.abs(frac - frac % 1.0) > 0).any(axis=1).sum())}")


if __name__ == "__main__":
    main()
