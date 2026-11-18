"""Like-for-like comparison of the model's melt-quenched glass with DFT's own melt-quenched glass.

DFT: GST_Melt_Quench_Eform_train.xyz, 200 frames of 144-atom Ge2Sb2Te5 from an NPT melt-quench (every frame has its
own cell volume). The frames span the whole trajectory, from hot liquid to glass, and carry no temperature. Frame
energy is used as the temperature proxy: the coldest frames (lowest energy) are the quenched glass. Reported for the
coldest 10, 20 and 40 frames, so the sensitivity to that choice is visible.
Model: by default nequip_no_zbl's 10 K/ps x0 melt-quench, replica 1 (29.5k atoms, NPT 0 bar), final 11 frames at
300 K (the frozen copy in tests/mq_analysis/ref/); another model's glass with MODEL_GLASS. The DFT file is the project's own training data; its sha256 is in
tests/mq_analysis/ref/SHA256SUMS.
Both are analysed with the same code and bond cutoffs (analysis/mq_structure.frame_stats):
  V/atom, density (Ge2Sb2Te5 mass per atom), DFT static pressure (ASE sign: P > 0 wants to expand; at 300 K and
  zero total pressure the static value is about -1.3 kbar), mean Z per species, and the fraction of Ge bond angles
  above 160 deg.
Verdict CONSISTENT if the model density is within 2% of the coldest-20 DFT density and every mean Z within 0.15.
Writes RESULT.txt. Run: ../../env/cgst-ana/bin/python check.py (~30 s)
"""
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "analysis"))
import mq_structure as ms  # noqa: E402

DFT = Path(os.environ.get("DFT_TRAIN", "/depot/prism/data/rapplet/cgst-vasp-data/xyz_files/train")) / "GST_Melt_Quench_Eform_train.xyz"
MODEL = Path(os.environ.get("MODEL_GLASS", HERE.parent / "mq_analysis/ref/model_glass_300K.npz"))
# default: the frozen nequip_no_zbl glass (source, sha256: ref/SHA256SUMS); for another model, set MODEL_GLASS to its own
# 10 K/ps glass npz (RUNBOOK.md), written from its x0 melt-quench run by make_model_glass.py
AMU_A3_TO_GCC = 1.66053907
MASS_PER_ATOM = (2 * 72.63 + 2 * 121.76 + 5 * 127.6) / 9         # Ge2Sb2Te5, amu
KBAR = 1602.1766
SP = {"Ge": 0, "Sb": 1, "Te": 2}


def read_extxyz(path):
    """[(energy, pos, box lengths, types, static P in kbar)] for an extxyz file with orthogonal cells."""
    lines = path.read_text().splitlines()
    out, k = [], 0
    while k < len(lines):
        n, hdr = int(lines[k]), lines[k + 1]
        lat = np.array(hdr.split('Lattice="')[1].split('"')[0].split(), float).reshape(3, 3)
        if not np.allclose(lat, np.diag(np.diag(lat))):
            raise ValueError(f"{path}: non-orthogonal cell")
        st = np.array(hdr.split('stress="')[1].split('"')[0].split(), float).reshape(3, 3)
        rows = [l.split() for l in lines[k + 2:k + 2 + n]]
        out.append((float(hdr.split("energy=")[1].split()[0]), np.array([[float(x) for x in r[1:4]] for r in rows]),
                    np.diag(lat), np.array([SP[r[0]] for r in rows]), -np.trace(st) / 3 * KBAR))
        k += n + 2
    return out


def stats(frames):
    """frames: [(pos, L, types)] -> V/atom, rho, mean Z per species (Ge, Sb, Te), Ge fraction of angles > 160 deg."""
    rcm = ms.cutoff_matrix({})
    zh, ah, v = 0, 0, []
    for pos, L, t in frames:
        f = ms.frame_stats(pos, L, t, rcm)
        zh, ah = zh + f["zhist"], ah + f["angles"]
        v.append(np.prod(L) / len(t))
    z = [(zh[s] * np.arange(ms.ZMAX + 1)).sum() / zh[s].sum() for s in range(3)]
    c = 0.5 * (ms.ANG[1:] + ms.ANG[:-1])
    V = float(np.mean(v))
    return V, MASS_PER_ATOM * AMU_A3_TO_GCC / V, z, ah[0][c > 160].sum() / ah[0].sum()


def fmt(name, V, rho, z, a160, extra=""):
    return (f"{name:34s} V/atom {V:6.2f}  rho {rho:5.3f}  Z_Ge {z[0]:.2f} Z_Sb {z[1]:.2f} Z_Te {z[2]:.2f}  "
            f"Ge>160deg {a160:.3f}{extra}")


dft = sorted(read_extxyz(DFT), key=lambda f: f[0])
lines = [f"DFT {DFT.name}: {len(dft)} frames, {len(np.unique(np.round([np.prod(f[2]) for f in dft], 3)))} distinct "
         f"volumes; energy {dft[0][0]:.1f} to {dft[-1][0]:.1f} eV/cell"]
res = {}
for n in (10, 20, 40):
    sel = dft[:n]
    res[n] = stats([(f[1], f[2], f[3]) for f in sel])
    P = np.array([f[4] for f in sel])
    lines.append(fmt(f"DFT coldest {n} (E <= {sel[-1][0]:.1f})", *res[n],
                     f"  P_static {P.mean():+.1f} kbar (range {P.min():+.1f}..{P.max():+.1f})"))
lines.append(fmt("DFT all 200 frames", *stats([(f[1], f[2], f[3]) for f in dft])))
z = np.load(MODEL)
model = [(pos.astype(float), L, z["types"].astype(int) - 1) for L, pos in zip(z["box"], z["pos"])]
m = stats(model)
lines.append(fmt("model 10 K/ps glass, 300 K, 0 bar", *m))
d = res[20]
drho = 100 * (m[1] / d[1] - 1)
dz = max(abs(a - b) for a, b in zip(m[2], d[2]))
ok = abs(drho) < 2 and dz < 0.15
lines += [f"model - DFT coldest 20: density {drho:+.2f}%, max |dZ| {dz:.2f}",
          f"VERDICT: {'CONSISTENT' if ok else 'DIFFERENT'} (criterion: |drho| < 2% and every |dZ| < 0.15)"]
(HERE / "RESULT.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
