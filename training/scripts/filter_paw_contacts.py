"""Drop frames containing an atom pair closer than 65% of the summed PAW core radii.

Below that distance the PAW spheres overlap too much for the DFT label to be trusted
(the same r_min used for the dimer scans in dft_atoms_dimers/make_inputs.py):
  Ge/Sb/Te pairs 1.58 A, pairs with C 1.31 A, C-C 1.03 A.
Frames are copied as raw text, so kept frames are byte-identical to the input.
Isolated-atom and DFT dimer frames (config_type Atom_*/Dimer_*) are exempt: their shortest
points sit at r_min by construction (rounded to 0.01 A, so a hair below it).
A CSV listing every removed frame and its offending contacts is written next to the output.

usage: python filter_paw_contacts.py in.xyz out.xyz
"""
import csv
import sys

from ase.io import read
from ase.neighborlist import neighbor_list

RCORE_BOHR = {"Ge": 2.3, "Sb": 2.3, "Te": 2.3, "C": 1.5}  # POTCAR RCORE
BOHR = 0.529177
FRACTION = 0.65


def r_min(a, b):
    return FRACTION * (RCORE_BOHR[a] + RCORE_BOHR[b]) * BOHR


def frames_as_text(path):
    with open(path) as f:
        while True:
            line = f.readline()
            if not line:
                return
            n = int(line)
            yield line + "".join(f.readline() for _ in range(n + 1))


src, dst = sys.argv[1], sys.argv[2]
removed = []
kept = 0
with open(dst, "w") as out:
    for i, block in enumerate(frames_as_text(src)):
        atoms = read(__import__("io").StringIO(block), format="extxyz")
        if atoms.info.get("config_type", "").startswith(("Atom_", "Dimer_")):
            out.write(block)
            kept += 1
            continue
        s = atoms.get_chemical_symbols()
        ii, jj, d = neighbor_list("ijd", atoms, 1.6)
        hits = sorted({f"{'-'.join(sorted((s[x], s[y])))} {r:.2f}" for x, y, r in zip(ii, jj, d)
                       if x < y and r < r_min(s[x], s[y])})
        if hits:
            removed.append((i, atoms.info.get("config_type", ""), len(atoms),
                            atoms.get_potential_energy() / len(atoms), "; ".join(hits)))
            continue
        out.write(block)
        kept += 1

with open(dst.rsplit(".", 1)[0] + "_removed.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["frame_index_in_input", "config_type", "n_atoms", "label_E_per_atom", "contacts_below_r_min"])
    w.writerows(removed)
print(f"{src}: kept {kept}, removed {len(removed)} -> {dst}")
