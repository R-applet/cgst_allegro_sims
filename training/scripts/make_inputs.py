"""Build VASP inputs for isolated atoms and dimer dissociation curves.

Settings follow /depot/prism/data/rapplet/cgst_ref_structs/*/INCAR (PBE PAW, 600 eV,
DFT-D2 IVDW=10, ISMEAR=0 SIGMA=0.05). Default is non-spin-polarized (ISPIN=1,
ALGO=Fast) to match the MLIP training data; `--spin` writes the ISPIN=2 set instead.
Atoms and dimers share one orthorhombic box so the small periodic D2/image terms
cancel when computing binding energies.

Layout (suffix "_nsp" for the default non-spin-polarized set):
  atoms[_nsp]/<El>/               single atom
  dimers[_nsp]/<A>-<B>/r_<r>/     dimer along x at separation r (Angstrom)
  submit_atoms.sh, submit_dimer.sh  (one job per pair, loops over r, skips finished points)
"""
import itertools
import os
import shutil
import sys

import numpy as np
from ase import Atoms
from ase.io import write

ROOT = os.path.dirname(os.path.abspath(__file__))
SPIN = "--spin" in sys.argv
SUFFIX = "" if SPIN else "_nsp"
REF = "/depot/prism/data/rapplet/cgst_ref_structs"
ELEMENTS = ["Ge", "Sb", "Te", "C"]
MAGMOM = {"Ge": 2.0, "Sb": 3.0, "Te": 2.0, "C": 2.0}  # free-atom ground-state moments
RCORE_A = {"Ge": 2.3, "Sb": 2.3, "Te": 2.3, "C": 1.5}  # POTCAR RCORE (bohr)
BOHR = 0.529177
CELL = [24.0, 20.0, 21.0]  # orthorhombic, breaks spherical symmetry for atoms

INCAR = """SYSTEM = {system}
ENCUT = 600
PREC = Normal
IVDW = 10
ISMEAR = 0
SIGMA = 0.05
{spin}EDIFF = 1e-6
NELM = 500
NELMIN = 5
ALGO = {algo}
ISYM = 0
LREAL = False
NSW = 0
IBRION = -1
LORBIT = 11
LCHARG = False
LWAVE = False
NPAR = 4
"""
KPOINTS = "Gamma only\n0\nGamma\n1 1 1\n0 0 0\n"


def distances(a, b):
    """Grid from moderate PAW-core overlap out to dissociation."""
    r_min = round(0.65 * (RCORE_A[a] + RCORE_A[b]) * BOHR, 2)
    return np.round(np.concatenate([
        np.arange(r_min, 3.0, 0.05),
        np.arange(3.0, 4.0, 0.1),
        np.arange(4.0, 6.51, 0.25),
    ]), 3)


def write_calc(path, atoms, system):
    os.makedirs(path, exist_ok=True)
    species = list(dict.fromkeys(atoms.get_chemical_symbols()))
    write(os.path.join(path, "POSCAR"), atoms, format="vasp", direct=False, sort=False)
    if SPIN:
        magmom = " ".join(str(MAGMOM[s]) for s in atoms.get_chemical_symbols())
        spin, algo = f"ISPIN = 2\nMAGMOM = {magmom}\n", "Normal"
    else:
        spin, algo = "", "Fast"
    with open(os.path.join(path, "INCAR"), "w") as f:
        f.write(INCAR.format(system=system, spin=spin, algo=algo))
    with open(os.path.join(path, "KPOINTS"), "w") as f:
        f.write(KPOINTS)
    with open(os.path.join(path, "POTCAR"), "wb") as out:
        for s in species:
            with open(os.path.join(REF, s, "POTCAR"), "rb") as src:
                shutil.copyfileobj(src, out)


center = np.array(CELL) / 2
for el in ELEMENTS:
    at = Atoms(el, positions=[center], cell=CELL, pbc=True)
    write_calc(os.path.join(ROOT, "atoms" + SUFFIX, el), at, f"{el} atom")

n_total = 0
for a, b in itertools.combinations_with_replacement(ELEMENTS, 2):
    for r in distances(a, b):
        pos = [center - [r / 2, 0, 0], center + [r / 2, 0, 0]]
        at = Atoms([a, b], positions=pos, cell=CELL, pbc=True)
        write_calc(os.path.join(ROOT, "dimers" + SUFFIX, f"{a}-{b}", f"r_{r:.3f}"), at, f"{a}-{b} r={r:.3f}")
        n_total += 1
    print(f"{a}-{b}: {len(distances(a, b))} points, r = {distances(a, b)[0]:.2f}-{distances(a, b)[-1]:.2f} A")
print(f"{n_total} dimer calculations, {len(ELEMENTS)} atoms")
