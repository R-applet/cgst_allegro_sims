"""Model vs DFT equations of state on the training-set EOS frames: where does each put the zero-pressure density of
amorphous, cubic and hexagonal (C-)GST, and does the model reproduce the DFT curve?

Each *_EOS_Eform_train.xyz file is one structure rescaled homogeneously to ~24 volumes (fractional coordinates
identical, ions not relaxed). For every frame, evaluate the checkpoint ($CKPT, common/model.sh; eager, float64) and compare
static pressures P = -tr(stress)/3 (ASE sign: P > 0 means the cell wants to expand) and energies with the DFT values.
Per file: V0 and rho0 where P(V) crosses zero (cubic fit of P vs V), for DFT and model, plus the pressure RMSE and
the energy-shape error (E - E at the frame nearest V0, per atom). These frames are in the training set, so this
tests the fit on these structures, not transfer to the model's own glasses.
Writes frames.csv and RESULT.txt. Run inside the LAMMPS container (submit.sh).
"""
import csv
import os
import sys
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
TRAIN = Path(os.environ.get("DFT_TRAIN") or sys.exit("set DFT_TRAIN and CKPT (source common/model.sh)"))
CKPT = os.environ.get("CKPT") or sys.exit("set CKPT (source common/model.sh)")
SETS = ["GST_AM_EOS", "GST_CUB_EOS", "GST_HEX_EOS"] + [f"C{c}_{p}_EOS" for c in (1, 5, 10) for p in ("AM", "CUB", "HEX")] \
    + ["C14_AM_EOS", "C18_AM_EOS"]
KBAR = 1602.1766
AMU_G = 1.66053907  # amu/A^3 -> g/cc


def zero_crossing(V, P):
    c = np.polyfit(V, P, 3)
    r = [x.real for x in np.roots(c) if abs(x.imag) < 1e-9 and V.min() - 1 <= x.real <= V.max() + 1]
    return min(r, key=lambda x: abs(x - V[np.argmin(abs(P))])) if r else np.nan


def main():
    import torch
    from ase.io import read
    from nequip.integrations.ase import NequIPCalculator

    calc = NequIPCalculator._from_saved_model(CKPT, device="cuda" if torch.cuda.is_available() else "cpu")
    rows, lines = [], [f"{'set':12s} {'formula':16s} {'n':>3s} {'V0_DFT':>7s} {'V0_mod':>7s} {'rho0_DFT':>8s} "
                       f"{'rho0_mod':>8s} {'drho%':>6s} {'RMSE_P':>7s} {'bias_P':>7s} {'RMSE_Eshape':>11s}",
                       f"{'':12s} {'':16s} {'':>3s} {'A3/at':>7s} {'A3/at':>7s} {'g/cc':>8s} {'g/cc':>8s} {'':>6s} "
                       f"{'kbar':>7s} {'kbar':>7s} {'meV/at':>11s}"]
    for name in SETS:
        path = TRAIN / f"{name}_Eform_train.xyz"
        if not path.exists():
            lines.append(f"{name:12s} (missing)")
            continue
        fr = read(path, ":")
        V, Pd, Pm, Ed, Em = [], [], [], [], []
        for i, a in enumerate(fr):
            n = len(a)
            sd, ed = a.get_stress(voigt=False), a.get_potential_energy()
            b = a.copy()
            b.calc = calc
            sm, em = b.get_stress(voigt=False), b.get_potential_energy()
            V.append(a.get_volume() / n)
            Pd.append(-np.trace(sd) / 3 * KBAR)
            Pm.append(-np.trace(sm) / 3 * KBAR)
            Ed.append(ed / n)
            Em.append(em / n)
            rows.append({"set": name, "frame": i, "natoms": n, "V_A3_per_atom": V[-1], "P_dft_kbar": Pd[-1],
                         "P_model_kbar": Pm[-1], "E_dft_eV_per_atom": Ed[-1], "E_model_eV_per_atom": Em[-1]})
        V, Pd, Pm, Ed, Em = map(np.array, (V, Pd, Pm, Ed, Em))
        m_per_atom = fr[0].get_masses().sum() / len(fr[0]) * AMU_G
        v0d, v0m = zero_crossing(V, Pd), zero_crossing(V, Pm)
        k = np.argmin(abs(V - v0d))
        eshape = 1e3 * np.sqrt((((Em - Em[k]) - (Ed - Ed[k])) ** 2).mean())
        lines.append(f"{name:12s} {fr[0].get_chemical_formula():16s} {len(fr):3d} {v0d:7.3f} {v0m:7.3f} "
                     f"{m_per_atom / v0d:8.4f} {m_per_atom / v0m:8.4f} {100 * (v0d / v0m - 1):6.2f} "
                     f"{np.sqrt(((Pm - Pd) ** 2).mean()):7.2f} {(Pm - Pd).mean():7.2f} {eshape:11.2f}")
        print(lines[-1], flush=True)
    with open(HERE / "frames.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    lines.append("drho% = 100 (rho0_model / rho0_DFT - 1). Static (virial-only) pressures; frames are training data.")
    (HERE / "RESULT.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
