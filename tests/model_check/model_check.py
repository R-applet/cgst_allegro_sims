"""Test 1b: the compiled LAMMPS model reproduces the training checkpoint.

  prepare  pick test-set frames (one per size/C-content class, CGST/cgst_test_paw.xyz), write them as LAMMPS
           data files, and evaluate the checkpoint ($CKPT, common/model.sh; eager, float64 on CUDA) on the frames as
           read back from those files, so the reference forces are in LAMMPS's rotated frame.
  compare  read LAMMPS's energies, forces and pressure tensor (in.model_check) and report |dE|/atom, max |dF| and
           max |dP| against the checkpoint, plus model-vs-DFT energy errors for context.
Pass: |dE| < 1e-4 eV/atom, max |dF| < 1e-3 eV/A and max |dP| < 1 bar for every frame.
Pressure: LAMMPS P = -stress (ASE sign convention), 1 eV/A^3 = 1602176.6 bar; zero velocities, so virial only.

prepare must run inside the LAMMPS container with the modified nequip/allegro on PYTHONPATH (see submit.sh).
"""
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from ase.io import iread, read, write

HERE = Path(__file__).resolve().parent
TESTSET = os.environ.get("TESTSET") or sys.exit("set TESTSET and CKPT (source common/model.sh)")
CKPT = os.environ.get("CKPT") or sys.exit("set CKPT (source common/model.sh)")
SPECORDER = ["Ge", "Sb", "Te", "C"]
Z_OF_TYPE = {1: 32, 2: 51, 3: 52, 4: 6}
EV_A3_TO_BAR = 1602176.6
VOIGT = [(0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)]   # LAMMPS pxx pyy pzz pyz pxz pxy


def prepare():
    import torch
    from nequip.integrations.ase import NequIPCalculator

    picked, seen = [], set()
    for i, a in enumerate(iread(TESTSET)):
        key = (len(a), "C" in a.get_chemical_symbols())
        if key not in seen:
            seen.add(key)
            picked.append((i, a))
    calc = NequIPCalculator._from_saved_model(CKPT, device="cuda" if torch.cuda.is_available() else "cpu")
    rows = []
    for i, a in picked:
        f = HERE / f"frame_{i}.data"
        write(f, a, format="lammps-data", specorder=SPECORDER, masses=True, atom_style="atomic")
        b = read(f, format="lammps-data", Z_of_type=Z_OF_TYPE, atom_style="atomic")
        b.calc = calc
        e_ref, f_ref = b.get_potential_energy(), b.get_forces()
        s = b.get_stress(voigt=False)                          # eV/A^3, ASE sign (positive = tensile)
        np.save(HERE / f"ref_forces_{i}.npy", f_ref)
        np.save(HERE / f"ref_pressure_{i}.npy", np.array([-s[r, c] for r, c in VOIGT]) * EV_A3_TO_BAR)
        rows.append((i, len(a), dict(Counter(a.get_chemical_symbols())).get("C", 0), e_ref, a.get_potential_energy()))
        print(f"frame {i}: {len(a)} atoms, {rows[-1][2]} C, E_ckpt = {e_ref:.6f} eV")
    np.savetxt(HERE / "ref.txt", np.array(rows), header="frame natoms nC E_ckpt_eV E_dft_eV", fmt="%.10g")
    (HERE / "frames.txt").write_text(" ".join(str(r[0]) for r in rows) + "\n")


def compare():
    ref = np.loadtxt(HERE / "ref.txt", ndmin=2)
    rows = np.loadtxt(HERE / "lammps_energies.txt", ndmin=2)
    lmp = {int(r[0]): r[1] for r in rows}
    p_lmp = {int(r[0]): r[2:8] for r in rows}
    ok = True
    print(f"{'frame':>6s} {'N':>5s} {'nC':>4s} {'dE_meV/at':>10s} {'max|dF|':>10s} {'max|dP|_bar':>12s} "
          f"{'E-EDFT_meV/at':>14s}")
    for i, n, nc, e_ref, e_dft in ref:
        i, n = int(i), int(n)
        dump = np.loadtxt(HERE / f"forces_{i}.dump", skiprows=9)
        f_lmp = dump[np.argsort(dump[:, 0]), 1:4]
        dE = 1e3 * (lmp[i] - e_ref) / n
        dF = np.abs(f_lmp - np.load(HERE / f"ref_forces_{i}.npy")).max()
        dP = np.abs(p_lmp[i] - np.load(HERE / f"ref_pressure_{i}.npy")).max()
        good = abs(dE) < 0.1 and dF < 1e-3 and dP < 1.0
        ok &= good
        print(f"{i:6d} {n:5d} {int(nc):4d} {dE:10.4f} {dF:10.2e} {dP:12.2e} {1e3 * (e_ref - e_dft) / n:14.2f} "
              f"{'' if good else 'FAIL'}")
    print("PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    {"prepare": prepare, "compare": compare}[sys.argv[1]]()
