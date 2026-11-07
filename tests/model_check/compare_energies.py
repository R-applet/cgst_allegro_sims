"""Compare the energies in two lammps_energies.txt files (in.model_check; columns 1-2 = frame, PE) frame by frame.

Usage: python compare_energies.py A.txt B.txt [tol_eV_per_atom]   (default tol 1e-6)
Atom counts come from tests/model_check/ref.txt. Fails if either file is missing, unreadable, or lacks a frame.
Always prints a PASS or FAIL line.
"""
import sys
from pathlib import Path

import numpy as np

ref = np.loadtxt(Path(__file__).resolve().parent / "ref.txt", ndmin=2)
natoms = {int(r[0]): r[1] for r in ref}
try:
    a, b = ({int(r[0]): r[1] for r in np.loadtxt(f, ndmin=2, usecols=(0, 1))} for f in sys.argv[1:3])
except (OSError, ValueError) as e:
    print(f"FAIL: cannot read an energy file ({e})")
    sys.exit(1)
tol = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-6
missing = set(natoms) - set(a) | set(natoms) - set(b)
if missing:
    print(f"FAIL: frames missing from an energy file: {sorted(missing)}")
    sys.exit(1)
d = max(abs(a[k] - b[k]) / natoms[k] for k in natoms)
print(f"{len(natoms)} frames, max |dE| = {d:.2e} eV/atom (tol {tol:g}) -> {'PASS' if d < tol else 'FAIL'}")
sys.exit(0 if d < tol else 1)
