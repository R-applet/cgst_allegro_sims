"""Collect the non-spin-polarized (nsp) isolated atoms and dimers into an extxyz in the
same label convention as cgst_train.xyz:

  energy       = E_free - sum_i n_i * mu_i   (formation energy w.r.t. elemental ground states)
  free_energy  = raw VASP free energy TOTEN
  stress       = VASP stress, ASE convention, eV/A^3

mu_i were recovered exactly (residual 5e-12 eV) from rapplet/cgst-vasp-data/xyz_files/all/{Etot,Eform}.

Dimer points kept: r <= R_KEEP, plus any farther point within TAIL_TOL of the isolated-atom
limit. The nsp tails are still 0.05-0.3 eV bound at 6 A, which a 6 A-cutoff model cannot
represent, so those points are dropped.
"""
import glob
import os

import numpy as np
from ase.io import read, write

ROOT = os.path.dirname(os.path.abspath(__file__))
MU = {"Ge": -4.783860, "Sb": -4.571496, "Te": -3.136069, "C": -9.298617}
R_KEEP = 5.0
TAIL_TOL = 0.05
OUT = os.path.join(ROOT, "dimers_atoms_nsp_Eform.xyz")


def load(d, config_type):
    a = read(os.path.join(d, "OUTCAR"), index=-1)
    F = a.get_potential_energy(force_consistent=True)
    e_form = F - sum(MU[s] for s in a.get_chemical_symbols())
    stress = a.get_stress(voigt=False)
    forces = a.get_forces()
    a.calc = None
    a.info = {"config_type": config_type, "system": config_type, "run": os.path.basename(d.rstrip("/")),
              "energy": e_form, "free_energy": F, "volume": a.get_volume(),
              "stress": " ".join(f"{x:.12g}" for x in stress.ravel())}
    a.arrays["forces"] = forces
    return a, F


frames, atom_F = [], {}
for d in sorted(glob.glob(os.path.join(ROOT, "atoms_nsp", "*/"))):
    el = os.path.basename(d.rstrip("/"))
    a, F = load(d, f"Atom_{el}_nsp")
    atom_F[el] = F
    frames.append(a)

summary = []
for pdir in sorted(glob.glob(os.path.join(ROOT, "dimers_nsp", "*/"))):
    pair = os.path.basename(pdir.rstrip("/"))
    A, B = pair.split("-")
    kept = dropped = 0
    for d in sorted(glob.glob(os.path.join(pdir, "r_*/")), key=lambda x: float(x.rstrip("/").split("r_")[1])):
        r = float(d.rstrip("/").split("r_")[1])
        a, F = load(d, f"Dimer_{pair}_nsp")
        if r <= R_KEEP or abs(F - atom_F[A] - atom_F[B]) <= TAIL_TOL:
            frames.append(a)
            kept += 1
        else:
            dropped += 1
    summary.append(f"{pair}: kept {kept}, dropped {dropped}")

# extxyz writer needs stress as a proper array to emit stress="..." like the training file
for a in frames:
    a.info["stress"] = np.array([float(x) for x in a.info["stress"].split()])
write(OUT, frames, format="extxyz", columns=["symbols", "positions", "forces"], write_info=True)
print("\n".join(summary))
print(f"{len(frames)} frames ({len(atom_F)} atoms) -> {OUT}")
