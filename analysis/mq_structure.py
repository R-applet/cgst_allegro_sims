"""Structure of the 300 K glasses from melt-quench trajectories (meltquench/in.meltquench outputs).

Per run directory, uses the traj.lammpstrj.gz frames of the final 50 ps (the RDF window of stage 4; mq.dat gives
the timestep) and the bond cutoffs runio.BOND_RC (overridable with --rc):
  coordination   distribution of each atom's total coordination Z (bonded neighbours of any species), per species
  bond angles    distribution of the angle between two bonds of the same centre atom, per centre species, 2 deg bins
  C motifs       each C atom's bonded neighbours as a formula (e.g. Ge2Te1C1), as a fraction of all C atoms
  C clusters     sizes of C-C bonded clusters (1 = isolated C), as the fraction of C atoms in clusters of each size
  S(q)           Faber-Ziman partials S_ij(q) and the Bhatia-Thornton number-number S_NN(q) = sum_ij c_i c_j S_ij,
                 from partial g_ij(r) out to rmax (default 15 A, at most L/2) with a Lorch window; the --sq-frames
                 last frames are used (pair counting to 15 A is the slow part)
Runs named <cell>_q<qrate>_r<rep> are grouped (runio.group_of). Per group, --out DIR receives <group>_zdist.dat,
_angles.dat, _sq.dat, _cmotifs.dat and _cclusters.dat with the mean and sample std over replicas (NaN for a single
replica; the header lists them). Stdout: per run, the frames used, mean Z per species, and the C clustering.

Usage: python mq_structure.py [--tscale S] [--rc GeTe=3.3 ...] [--rmax 15] [--sq-frames 5] --out DIR <run_dir> ...
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bondorder import read_dump  # noqa: E402
from runio import BOND_RC, SPECIES, complete_runs, group_of, load_dat, mean_std, parse_rc  # noqa: E402

ZMAX = 12
ANG = np.arange(0.0, 182.0, 2.0)                    # bond-angle bin edges (deg)
DR = 0.02                                           # g(r) bin width for S(q) (A)
Q = np.arange(0.5, 12.0 + 1e-9, 0.02)               # q grid (1/A)


def cutoff_matrix(rc):
    m = np.zeros((4, 4))
    for i in range(4):
        for j in range(4):
            key = frozenset([SPECIES[i], SPECIES[j]])
            m[i, j] = rc.get(key, BOND_RC[key])
    return m


def bonds(pos, L, t, rcm):
    """Bonded pairs (i, j), their vectors j - i (minimum image) under the per-pair cutoffs."""
    tree = cKDTree(np.mod(pos, L), boxsize=L)
    p = tree.query_pairs(rcm.max(), output_type="ndarray")
    d = np.mod(pos, L)[p[:, 1]] - np.mod(pos, L)[p[:, 0]]
    d -= L * np.round(d / L)
    keep = np.linalg.norm(d, axis=1) < rcm[t[p[:, 0]], t[p[:, 1]]]
    return p[keep], d[keep]


def angle_hist(p, d, t, n):
    """Per centre species, histogram of bond angles (counts) over all pairs of bonds sharing a centre."""
    centre = np.concatenate([p[:, 0], p[:, 1]])
    vec = np.concatenate([d, -d])
    order = np.argsort(centre, kind="stable")
    centre, vec = centre[order], vec[order]
    vec /= np.linalg.norm(vec, axis=1)[:, None]
    deg = np.bincount(centre, minlength=n)
    start = np.concatenate([[0], np.cumsum(deg)[:-1]])
    h = np.zeros((4, len(ANG) - 1))
    for k in range(2, deg.max() + 1):                # atoms with k bonds: all k(k-1)/2 angles at once
        atoms = np.flatnonzero(deg == k)
        if len(atoms) == 0:
            continue
        v = vec[start[atoms, None] + np.arange(k)]   # (n_k, k, 3)
        cos = np.einsum("aid,ajd->aij", v, v)
        iu = np.triu_indices(k, 1)
        a = np.degrees(np.arccos(np.clip(cos[:, iu[0], iu[1]], -1, 1)))
        for s in range(4):
            m = t[atoms] == s
            if m.any():
                h[s] += np.histogram(a[m].ravel(), ANG)[0]
    return h


def pair_counts(pos, L, t, rmax):
    """Unordered pair counts per (i, j) type pair in DR shells up to rmax."""
    tree = cKDTree(np.mod(pos, L), boxsize=L)
    p = tree.query_pairs(rmax, output_type="ndarray")
    d = np.mod(pos, L)[p[:, 1]] - np.mod(pos, L)[p[:, 0]]
    d -= L * np.round(d / L)
    r = np.linalg.norm(d, axis=1)
    a, b = np.minimum(t[p[:, 0]], t[p[:, 1]]), np.maximum(t[p[:, 0]], t[p[:, 1]])
    nb = int(round(rmax / DR))
    k = np.minimum((r / DR).astype(int), nb - 1)
    return np.bincount((a * 4 + b) * nb + k, minlength=16 * nb).reshape(4, 4, nb)


def structure_factor(counts, nframes, N, V):
    """Faber-Ziman S_ij(q) (4 x 4 x nq; NaN for absent species) and S_NN(q), Lorch-windowed."""
    nb = counts.shape[2]
    r = (np.arange(nb) + 0.5) * DR
    rmax = nb * DR
    shell = 4 * np.pi * r ** 2 * DR
    c = N / N.sum()
    rho = N.sum() / V
    W = np.sinc(r / rmax)                                       # np.sinc(x) = sin(pi x) / (pi x): the Lorch window
    kern = np.sin(np.outer(Q, r)) / np.outer(Q, r) * (r ** 2 * W * 4 * np.pi * DR)[None, :]
    S = np.full((4, 4, len(Q)), np.nan)
    for i in range(4):
        for j in range(i, 4):
            if N[i] == 0 or N[j] == 0:
                continue
            npairs = N[i] * (N[i] - 1) / 2 if i == j else N[i] * N[j]
            g = counts[i, j] / nframes * V / (npairs * shell)
            S[i, j] = S[j, i] = 1 + rho * kern @ (g - 1)
    present = N > 0
    snn = sum(c[i] * c[j] * S[i, j] for i in range(4) for j in range(4) if present[i] and present[j])
    return S, snn


def frame_stats(pos, L, t, rcm):
    """One frame: per-species Z histograms (4 x ZMAX+1 counts), bond-angle histograms (4 x bins), and Counters of C
    bonded-neighbour formulas (per C atom) and of C-C cluster sizes (weighted by atoms). t = LAMMPS type - 1."""
    n = len(t)
    p, dv = bonds(pos, L, t, rcm)
    z = np.bincount(p.ravel(), minlength=n)
    zh = np.array([np.bincount(np.minimum(z[t == s], ZMAX), minlength=ZMAX + 1) for s in range(4)])
    motifs, csizes = Counter(), Counter()
    ci = np.flatnonzero(t == 3)
    if len(ci):
        nb = np.zeros((n, 4), int)                                # bonded neighbours of each species, per atom
        np.add.at(nb, (p[:, 0], t[p[:, 1]]), 1)
        np.add.at(nb, (p[:, 1], t[p[:, 0]]), 1)
        for row in nb[ci]:
            motifs["".join(f"{SPECIES[s]}{row[s]}" for s in range(4) if row[s]) or "none"] += 1
        cc = p[(t[p[:, 0]] == 3) & (t[p[:, 1]] == 3)]
        idx = np.full(n, -1)
        idx[ci] = np.arange(len(ci))
        g = coo_matrix((np.ones(len(cc)), (idx[cc[:, 0]], idx[cc[:, 1]])), shape=(len(ci), len(ci)))
        _, lab = connected_components(g, directed=False)
        for size in np.bincount(lab):
            csizes[int(size)] += int(size)                        # weight by atoms: fraction of C in each size
    return {"zhist": zh, "angles": angle_hist(p, dv, t, n), "cmotifs": motifs, "cclusters": csizes}


def analyze(run, tscale, rcm, rmax, sq_frames):
    run = Path(run)
    d = load_dat(run / "mq.dat")
    dt = d["time_ps"][-1] / d["step"][-1]
    t_end = d["time_ps"].max()
    frames = [(s, L, c) for s, L, c in read_dump(run / "traj.lammpstrj.gz") if s * dt >= t_end - 50 * tscale - 1e-9]
    if not frames:
        raise SystemExit(f"{run}: no trajectory frames in the final 50 ps")
    t = frames[0][2]["type"].astype(int) - 1
    N = np.bincount(t, minlength=4).astype(float)
    zh = np.zeros((4, ZMAX + 1))
    ah = np.zeros((4, len(ANG) - 1))
    motifs, csizes = Counter(), Counter()
    rm = min(rmax, min(frames[0][1]) / 2)
    counts, V = 0, 0.0
    for k, (step, L, c) in enumerate(frames):
        f = frame_stats(c["pos"], L, t, rcm)
        zh += f["zhist"]
        ah += f["angles"]
        motifs.update(f["cmotifs"])
        csizes.update(f["cclusters"])
        if k >= len(frames) - sq_frames:
            counts = counts + pair_counts(c["pos"], L, t, rm)
            V += np.prod(L)
    nsq = min(sq_frames, len(frames))
    S, snn = structure_factor(counts, nsq, N, V / nsq)
    with np.errstate(invalid="ignore"):
        res = {"run": run.name, "nframes": len(frames), "N": N,
               "zdist": zh / zh.sum(1, keepdims=True), "angles": ah / ah.sum(1, keepdims=True) / np.diff(ANG),
               "S": S, "snn": snn, "rmax_sq": rm}
    nc = sum(motifs.values())
    res["cmotifs"] = {m: v / nc for m, v in motifs.items()} if nc else {}
    tot = sum(csizes.values())
    res["cclusters"] = {s: v / tot for s, v in csizes.items()} if tot else {}
    return res


def write_group(out, g, rs):
    hdr = f"# {len(rs)} replica(s): " + " ".join(r["run"] for r in rs)
    present = [s for s in range(4) if rs[0]["N"][s] > 0]
    m, e = mean_std([r["zdist"] for r in rs])
    lines = [hdr, "# fraction of atoms of each species with total coordination Z", "Z " + " ".join(
        f"{SPECIES[s]}_mean {SPECIES[s]}_std" for s in present)]
    lines += [f"{z} " + " ".join(f"{m[s, z]:.5f} {e[s, z]:.5f}" for s in present) for z in range(ZMAX + 1)]
    (out / f"{g}_zdist.dat").write_text("\n".join(lines) + "\n")
    m, e = mean_std([r["angles"] for r in rs])
    c = 0.5 * (ANG[1:] + ANG[:-1])
    lines = [hdr, "# bond-angle distribution per centre species (normalized to unit area, 1/deg)",
             "angle_deg " + " ".join(f"{SPECIES[s]}_mean {SPECIES[s]}_std" for s in present)]
    lines += [f"{c[k]:.0f} " + " ".join(f"{m[s, k]:.6f} {e[s, k]:.6f}" for s in present) for k in range(len(c))]
    (out / f"{g}_angles.dat").write_text("\n".join(lines) + "\n")
    sm, se = mean_std([r["snn"] for r in rs])
    Sm, Se = mean_std([r["S"] for r in rs])
    pairs = [(i, j) for i in present for j in present if j >= i]
    lines = [hdr, f"# Faber-Ziman partials and Bhatia-Thornton S_NN; g(r) to {rs[0]['rmax_sq']:.1f} A, Lorch window",
             "q_invA SNN_mean SNN_std " + " ".join(f"S_{SPECIES[i]}{SPECIES[j]}_mean S_{SPECIES[i]}{SPECIES[j]}_std"
                                                    for i, j in pairs)]
    for k in range(len(Q)):
        lines.append(f"{Q[k]:.2f} {sm[k]:.5f} {se[k]:.5f} " + " ".join(f"{Sm[i, j, k]:.5f} {Se[i, j, k]:.5f}"
                                                                       for i, j in pairs))
    (out / f"{g}_sq.dat").write_text("\n".join(lines) + "\n")
    if any(r["cmotifs"] for r in rs):
        for key, name in (("cmotifs", "motif"), ("cclusters", "cluster_size")):
            keys = {k for r in rs for k in r[key]}
            if key == "cclusters":                                 # by size; motifs by mean frequency
                keys = sorted(keys)
            else:
                keys = sorted(keys, key=lambda k: -np.mean([r[key].get(k, 0) for r in rs]))
            vals = [[r[key].get(k, 0.0) for k in keys] for r in rs]
            m, e = mean_std(vals)
            what = ("C atoms with this bonded-neighbour formula" if key == "cmotifs"
                    else "C atoms in C-C clusters of this size")
            lines = [hdr, f"# fraction of {what}", f"{name} mean std"]
            lines += [f"{k} {m[i]:.5f} {e[i]:.5f}" for i, k in enumerate(keys)]
            (out / f"{g}_{key}.dat").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", required=True, help="directory for the per-group output files")
    ap.add_argument("--tscale", type=float, default=1.0, help="tscale the runs used (tests only)")
    ap.add_argument("--rc", action="append", default=[], metavar="PAIR=R", help="bond cutoff override (A)")
    ap.add_argument("--rmax", type=float, default=15.0, help="g(r) range for S(q) (A; capped at L/2)")
    ap.add_argument("--sq-frames", type=int, default=5, help="number of final frames used for S(q)")
    a = ap.parse_args()
    rcm = cutoff_matrix(parse_rc(a.rc))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    groups = {}
    runs = complete_runs(a.runs)
    if not runs:
        raise SystemExit("no complete runs")
    for run in runs:
        r = analyze(run, a.tscale, rcm, a.rmax, a.sq_frames)
        zmean = [(r["zdist"][s] * np.arange(ZMAX + 1)).sum() for s in range(4)]
        line = f"{r['run']:18s} frames {r['nframes']:3d}  " + "  ".join(
            f"Z_{SPECIES[s]} {zmean[s]:.3f}" for s in range(4) if r["N"][s])
        if r["cclusters"]:
            line += f"  C in C-C clusters (size > 1) {1 - r['cclusters'].get(1, 0):.3f}"
        print(line, flush=True)
        groups.setdefault(group_of(r["run"]), []).append(r)
    for g, rs in groups.items():
        write_group(out, g, rs)


if __name__ == "__main__":
    main()
