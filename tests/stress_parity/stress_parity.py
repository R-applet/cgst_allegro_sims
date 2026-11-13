"""Model vs DFT pressure on identical structures, by config type: is the dense model glass (tests/RESULTS.md, 1g)
a fitting error or a property of the reference DFT?

For every frame of the held-out test set (CGST/cgst_test_paw.xyz), evaluate the checkpoint ($CKPT, common/model.sh; eager,
float64) and compare P = -trace(stress)/3 with the DFT value stored in the frame. Both are static (virial-only)
stresses, ASE sign convention (P > 0 means the cell wants to expand), so the comparison is like for like.
  model P < DFT P on amorphous frames  -> the model under-predicts the glass's outward pressure, so at 0 bar its glass
                                          shrinks below the DFT density: a fitting error
  model P ~ DFT P                      -> the model reproduces DFT; the dense glass comes from the DFT (or from
                                          states outside this test set)
Writes frames.csv (one row per frame) and RESULT.txt (per config type: n, mean V/atom, mean P_DFT, mean P_model,
mean bias, RMSE of P, energy MAE). Pressures in kbar (1 eV/A^3 = 1602.1766 kbar).
Run inside the LAMMPS container with the modified nequip/allegro on PYTHONPATH (submit.sh).
"""
import csv
import os
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
TESTSET = os.environ.get("TESTSET") or sys.exit("set TESTSET and CKPT (source common/model.sh)")
CKPT = os.environ.get("CKPT") or sys.exit("set CKPT (source common/model.sh)")
KBAR = 1602.1766


def main():
    import torch
    from ase.io import iread
    from nequip.integrations.ase import NequIPCalculator

    calc = NequIPCalculator._from_saved_model(CKPT, device="cuda" if torch.cuda.is_available() else "cpu")
    rows = []
    for i, a in enumerate(iread(TESTSET)):
        # ASE puts the stored DFT energy and stress in a SinglePointCalculator; read them before attaching the model
        s_dft = a.get_stress(voigt=False)
        e_dft = a.get_potential_energy()
        b = a.copy()
        b.calc = calc
        s_mod = b.get_stress(voigt=False)
        n = len(a)
        rows.append({"frame": i, "config_type": a.info.get("config_type", "None"), "natoms": n,
                     "nC": int(sum(z == 6 for z in a.numbers)), "V_A3_per_atom": a.get_volume() / n,
                     "P_dft_kbar": -np.trace(s_dft) / 3 * KBAR, "P_model_kbar": -np.trace(s_mod) / 3 * KBAR,
                     "dE_meV_per_atom": 1e3 * (b.get_potential_energy() - e_dft) / n})
        if i % 200 == 0:
            print(i, rows[-1], flush=True)
    with open(HERE / "frames.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    groups = defaultdict(list)
    for r in rows:
        groups[r["config_type"]].append(r)
    lines = [f"{'config_type':20s} {'n':>4s} {'V/atom':>7s} {'P_DFT':>8s} {'P_model':>8s} {'bias':>7s} {'RMSE_P':>7s} "
             f"{'MAE_E':>6s}", f"{'':20s} {'':>4s} {'(A^3)':>7s} {'(kbar)':>8s} {'(kbar)':>8s} {'(kbar)':>7s} "
             f"{'(kbar)':>7s} {'meV/at':>6s}"]
    for ct, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        V = np.array([r["V_A3_per_atom"] for r in rs])
        pd = np.array([r["P_dft_kbar"] for r in rs])
        pm = np.array([r["P_model_kbar"] for r in rs])
        de = np.array([r["dE_meV_per_atom"] for r in rs])
        lines.append(f"{ct:20s} {len(rs):4d} {V.mean():7.2f} {pd.mean():8.2f} {pm.mean():8.2f} {(pm - pd).mean():7.2f} "
                     f"{np.sqrt(((pm - pd) ** 2).mean()):7.2f} {np.abs(de).mean():6.2f}")
    txt = "\n".join(lines)
    print(txt)
    (HERE / "RESULT.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
