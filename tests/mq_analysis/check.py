"""Independent checks of the melt-quench analysis (analysis/mq_structure.py, analysis/mq_summary.py).

Reference glass: nequip_no_zbl's 10 K/ps x0 melt-quench, replica 1 (meltquench/runs/nequip_no_zbl/x0_q10_r1:
29.5k-atom Ge2Sb2Te5, 4x4x4), as frozen copies in ref/ (sources and sha256s in ref/SHA256SUMS), so the check does not
depend on the run directory:
  - model_glass_300K.npz: the 11 trajectory frames of the final 50 ps at 300 K (tests/dft_glass/make_model_glass.py)
  - rdf_300K.dat: LAMMPS's own partial g(r) (compute rdf, common/in.rdf) over the same 50 ps window, an independent
    implementation of the same quantity, sampled more often than the dumped frames
  - mq_quench.dat: the run's mq.dat rows of the 1500 -> 300 K quench (240-360 ps, one row per step)
  1. pair counting: our partial g(r) from the frames matches LAMMPS's (max |dg| for r > 2 A, first-peak position)
     and tends to 1 at 14-15 A
  2. S_NN(q): first two peaks inside sanity windows around the amorphous-GST peaks (~2.0-2.2 and ~3.1-3.4 1/A)
  3. Tg: the bilinear fit on the 121-point quench lands in 500-900 K
Known answers, independent of any simulation:
  4. perfect rocksalt x0 lattice (structures/111/x0.data, 3.015 A grid, 3.2 A cutoff): every Ge/Sb has Z = 6;
     mean Z_Te = 6 (N_Ge + N_Sb) / N_Te (each cation has six Te neighbours; Te loses one per vacant site); bond
     angles only at 90 and 180 deg, with 3 of a six-fold site's 15 angles at 180 (fraction 0.2)
  5. toy C cell (a linear C3 chain, a C2 dimer, one C bonded to one Ge): C clusters 3/6 in size 3, 2/6 in size
     2, 1/6 in size 1; motifs C1 4/6, C2 1/6, Ge1 1/6; the chain's middle C has one 180 deg angle
  6. replica statistics (runio.mean_std): the std of 1, 2, 3 is 1 (sample std, ddof 1); one value gives NaN
  7. closest approach (mq_summary.closest, rmin_*): on a synthetic RDF file, the lower edge of the first bin with
     g > 0 per pair (Ge-Te 2.30 A, C-C 0.94 A), NaN for a pair that never appears
Check 4 needs structures/111/x0.data (gitignored; python structures/build_supercells.py --nrep 1). The rocksalt
angle check cannot see a reversed bond vector (cubic angles stay at 90/180); the toy cell's 180 deg check can.
Writes RESULT.txt and exits 1 on any failure. Run: ../../env/cgst-ana/bin/python check.py
"""
import sys
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
import mq_structure as ms  # noqa: E402
from mq_summary import bilinear_tg, load_rdf  # noqa: E402

REF = HERE / "ref"
lines, ok = [], True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    lines.append(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


# ---------- 1-2. reference glass: g(r) and S(q) ----------
z = np.load(REF / "model_glass_300K.npz")
frames = list(zip(z["box"], z["pos"].astype(float)))
t = z["types"].astype(int) - 1
N = np.bincount(t, minlength=4).astype(float)
counts, V = 0, 0.0
for L, pos in frames:
    counts = counts + ms.pair_counts(pos, L, t, 15.0)
    V += np.prod(L)
V /= len(frames)
r = (np.arange(counts.shape[2]) + 0.5) * ms.DR
shell = 4 * np.pi * r ** 2 * ms.DR
r_ref, rdf_ref = load_rdf(REF / "rdf_300K.dat")                  # LAMMPS, 0.02 A bins to 6 A
for i, j in [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2)]:
    npairs = N[i] * (N[i] - 1) / 2 if i == j else N[i] * N[j]
    g = counts[i, j] / len(frames) * V / (npairs * shell)
    g_ref = rdf_ref[(i, j)][0]
    gi = np.interp(r_ref, r, g)
    m = r_ref > 2.0
    dg = np.abs(gi[m] - g_ref[m]).max()
    dpk = abs(r[np.argmax(g)] - r_ref[np.argmax(g_ref)])
    tail = g[r > 14].mean()
    name = ms.SPECIES[i] + ms.SPECIES[j]
    # 0.2 allows for the sampling difference (11 dumped frames vs LAMMPS's averaging) at the sharp Ge-Te/Sb-Te peaks
    check(f"g_{name}(r) matches LAMMPS's", dg < 0.2 and dpk < 0.15 and abs(tail - 1) < 0.03,
          f"max|dg| {dg:.3f}, peak shift {dpk:.2f} A, g(14-15 A) {tail:.3f}")
_, snn = ms.structure_factor(counts, len(frames), N, V)
pk, _ = find_peaks(snn, prominence=0.05)
q1, q2 = ms.Q[pk[0]], ms.Q[pk[1]]
check("S_NN(q) first two peaks in the a-GST windows", 2.0 <= q1 <= 2.25 and 3.1 <= q2 <= 3.4,
      f"{q1:.2f}, {q2:.2f} 1/A")

# ---------- 3. Tg on the reference quench ----------
d = np.loadtxt(REF / "mq_quench.dat", skiprows=1)                 # step time_ps T_K P_bar V_A3_per_atom ...
q = np.ones(len(d), bool)
tg = bilinear_tg(d[q, 2], d[q, 4])
check("Tg of the reference 10 K/ps quench in 500-900 K", 500 <= tg <= 900, f"Tg = {tg:.0f} K from {q.sum()} points")

# ---------- 4. perfect rocksalt lattice ----------
txt = (ROOT / "structures/111/x0.data").read_text().splitlines()
L = np.array([float(txt[k].split()[1]) - float(txt[k].split()[0]) for k, l in enumerate(txt) if "lo " in l])
i0 = next(k for k, l in enumerate(txt) if l.startswith("Atoms")) + 2
n = int(txt[2].split()[0])
atoms = np.array([[float(v) for v in l.split()[:5]] for l in txt[i0:i0 + n]])
tt = atoms[:, 1].astype(int) - 1
f = ms.frame_stats(atoms[:, 2:5], L, tt, ms.cutoff_matrix({}))
zh = f["zhist"]
check("rocksalt: every Ge and Sb has Z = 6", zh[0, 6] == (tt == 0).sum() and zh[1, 6] == (tt == 1).sum(),
      f"Z=6 for {zh[0, 6]}/{(tt == 0).sum()} Ge, {zh[1, 6]}/{(tt == 1).sum()} Sb")
zte = (zh[2] * np.arange(len(zh[2]))).sum() / zh[2].sum()
expect = 6 * ((tt == 0).sum() + (tt == 1).sum()) / (tt == 2).sum()
check("rocksalt: mean Z_Te = 6 (N_Ge + N_Sb) / N_Te", abs(zte - expect) < 1e-12, f"{zte:.4f} vs {expect:.4f}")
c = 0.5 * (ms.ANG[1:] + ms.ANG[:-1])
for s, name in ((0, "Ge"), (1, "Sb")):
    h = f["angles"][s]
    at90, at180 = h[abs(c - 90) < 3].sum(), h[c > 176].sum()
    check(f"rocksalt: {name} bond angles only at 90/180 deg, 180 fraction 0.2",
          at90 + at180 == h.sum() and abs(at180 / h.sum() - 0.2) < 1e-12, f"180 fraction {at180 / h.sum():.4f}")

# ---------- 5. toy C cell ----------
pos = np.array([[5.0, 5, 5], [6.4, 5, 5], [7.8, 5, 5],           # C3 chain, C-C 1.4 A
                [15.0, 15, 15], [16.4, 15, 15],                  # C2 dimer
                [25.0, 5, 15],                                   # C bonded to Ge
                [27.0, 5, 15],                                   # Ge, 2.0 A from it
                [15.0, 5, 25]])                                  # Te, isolated
tt = np.array([3, 3, 3, 3, 3, 3, 0, 2])
f = ms.frame_stats(pos, np.array([30.0, 30, 30]), tt, ms.cutoff_matrix({}))
check("toy C cell: cluster sizes", dict(f["cclusters"]) == {3: 3, 2: 2, 1: 1}, str(dict(f["cclusters"])))
check("toy C cell: C motifs", dict(f["cmotifs"]) == {"C1": 4, "C2": 1, "Ge1": 1}, str(dict(f["cmotifs"])))
check("toy C cell: one 180 deg C angle (chain middle)",
      f["angles"][3].sum() == 1 and f["angles"][3][c > 176].sum() == 1)

# ---------- 6. replica statistics ----------
from runio import mean_std  # noqa: E402

m, s = mean_std([[1.0, 5.0], [2.0, np.nan], [3.0, np.nan]])
check("mean_std: sample std (ddof 1), NaN for a single value", m[0] == 2.0 and s[0] == 1.0 and m[1] == 5.0
      and np.isnan(s[1]), f"std {s[0]:g}, single-value std {s[1]}")

# ---------- 7. closest approach (mq_summary.closest, for potentials without ZBL) ----------
import tempfile  # noqa: E402
from mq_summary import closest  # noqa: E402

rr = (np.arange(300) + 0.5) * 0.02                       # bin centres, 0.02 A bins to 6 A, as common/in.rdf
cols = np.zeros((300, 20))                             # 10 pairs x (g, cn) after the total g and cn
cols[np.searchsorted(rr, 2.31):, 2 * 2] = 1.0            # Ge-Te (3rd pair): first g > 0 in the bin [2.30, 2.32)
cols[np.searchsorted(rr, 0.95):, 2 * 9] = 0.5            # C-C (10th pair): first g > 0 in the bin [0.94, 0.96)
with tempfile.TemporaryDirectory() as tmp:
    f = Path(tmp) / "rdf_1500K.dat"
    f.write_text("# fake\n# fake\n# fake\n0 300\n" + "\n".join(
        f"{k + 1} {rr[k]:.2f} 0 0 " + " ".join(f"{v:g}" for v in cols[k]) for k in range(300)) + "\n")
    cm = closest(f)
check("closest(): lower edge of the first bin with g > 0, per pair; NaN for an absent pair",
      abs(cm["Ge-Te"] - 2.30) < 1e-9 and abs(cm["C-C"] - 0.94) < 1e-9 and np.isnan(cm["Ge-Ge"]),
      f"Ge-Te {cm['Ge-Te']:.2f}, C-C {cm['C-C']:.2f}, Ge-Ge {cm['Ge-Ge']}")

lines.append(f"VERDICT: {'PASS' if ok else 'FAIL'}")
(HERE / "RESULT.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0 if ok else 1)
