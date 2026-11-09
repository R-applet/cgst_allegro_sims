"""Choose the Q4 crystallinity criterion (q_rc, q_thr, q_nmin) from reference trajectories (in.calib output).

For each (rc, thr, nmin) on a grid, compute the fraction of Ge/Sb/Te atoms classed crystalline (xfracGST, the
measure the runs use; C atoms are left out, common/in.analysis) in every reference file:
  crystal_min    min over the crystal references    (should be close to 1)
  amorphous_max  max over the amorphous references  (should be close to 0)
and pick the criterion that maximizes the margin crystal_min - amorphous_max over all references and temperatures.
Writes calib_scan.csv (full grid) and calib.png, and prints the best criterion and the per-reference fractions.
calib.png: (a) each reference's crystalline fraction under the chosen criterion (filled) and the default
(3.6, 0.5, 4; open); (b) the per-atom crystal-like bond count, crystal vs amorphous references pooled, at the chosen
q_rc and q_thr, with the q_nmin threshold; (c) the margin over q_thr x q_nmin at the chosen q_rc.
Warns when the best value of any parameter lies on the edge of its grid (the optimum may be outside it). Prints, per
crystal-reference temperature (300, 500, 550, 600, 650, 700 K: the anneal temperatures are sampled directly), the
suggested anneal halt level XSTOP (0.85 x the lowest crystal-reference xfracGST) and the --x-crystal value for
recryst_summary.py.
Nucleation threshold: the glass already holds crystal-like patches of up to a few hundred Ge/Sb/Te atoms
(recryst/README.md, "Crystal-like order already in the glass"), so a fixed small "nucleated" size would mark every anneal as nucleated at t = 0. For the
amorphous references the largest crystalline Ge/Sb/Te cluster (bondorder.cluster_sizes) is found in every frame,
under the chosen and the default criterion, and printed per temperature and composition with the suggested
--nucleated-size for recryst_summary.py: 2 x the largest cluster over all compositions at that T, rounded up to a
multiple of 10 (one value per T, so every composition is held to the same threshold).

Usage: python calibrate.py --crystal crys_*.lammpstrj.gz --amorphous amor_*.lammpstrj.gz
"""
import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "analysis"))
from bondorder import bond_dots, cluster_sizes, crystal_bonds, read_dump  # noqa: E402

RC = [3.4, 3.5, 3.6, 3.7, 3.8]
THR = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
NMIN = [3, 4, 5, 6, 7]


def fractions(path, rc_list):
    """{rc: list over frames of an int8 array (len(THR), n Ge/Sb/Te atoms): each Ge/Sb/Te atom's crystal-like bond
    count at each q_thr (bonds to C neighbours included, as in LAMMPS's c_ncb)}.
    The q4 computation runs once per frame and rc; keeping counts, not bond pairs, keeps memory at ~0.5 MB per frame
    for a 13.8k-atom cell (pairs and dot products for every frame would need several GB for the full reference set)."""
    out = {rc: [] for rc in rc_list}
    for _, L, c in read_dump(path):
        n, gst = len(c["pos"]), c["type"] != 4
        for rc in rc_list:
            p, dot = bond_dots(c["pos"], L, rc)
            out[rc].append(np.array([np.bincount(p[dot > thr].ravel(), minlength=n)[gst] for thr in THR], np.int8))
    return out


def xfrac(frames, thr, nmin):
    k = THR.index(thr)
    return float(np.mean([(ncb[k] >= nmin).mean() for ncb in frames]))


def largest_clusters(path, criteria):
    """{(rc, thr, nmin): array over frames of the largest crystalline Ge/Sb/Te cluster (atoms)} for one dump."""
    out = {k: [] for k in criteria}
    for _, L, c in read_dump(path):
        gst = c["type"] != 4
        for rc, thr, nmin in criteria:
            s = cluster_sizes((crystal_bonds(c["pos"], L, rc, thr) >= nmin) & gst, c["pos"], L, rc)
            out[rc, thr, nmin].append(int(s[0]) if len(s) else 0)
    return {k: np.array(v) for k, v in out.items()}


def nucleation_thresholds(amorphous, criteria):
    """Print, per criterion and temperature, the largest glass cluster per composition and the suggested
    --nucleated-size (2 x the largest over compositions, rounded up to a multiple of 10)."""
    big = {Path(f).name: largest_clusters(f, criteria) for f in amorphous}
    for crit in criteria:
        by_T = {}
        for name, b in big.items():
            m = re.search(r"amor_(.+)_(\d+)K", name)
            key = (int(m[2]), m[1]) if m else (0, name)
            by_T.setdefault(key[0], []).append((key[1], int(b[crit].max())))
        print(f"largest crystalline Ge/Sb/Te cluster in the amorphous references, criterion {crit}:")
        for T, cells in sorted(by_T.items()):
            top = max(n for _, n in cells)
            per = ", ".join(f"{cell} {n}" for cell, n in cells)
            print(f"  suggested --nucleated-size at {T} K: {int(np.ceil(2 * max(top, 1) / 10) * 10)}  "
                  f"(2 x the largest glass cluster, {top}; {per})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crystal", nargs="+", required=True)
    ap.add_argument("--amorphous", nargs="+", required=True)
    a = ap.parse_args()
    refs = {Path(f).name: ("crystal", fractions(f, RC)) for f in a.crystal}
    refs |= {Path(f).name: ("amorphous", fractions(f, RC)) for f in a.amorphous}
    rows, best = [], None
    for rc in RC:
        for thr in THR:
            for nmin in NMIN:
                fr = {k: xfrac(v[rc], thr, nmin) for k, (kind, v) in refs.items()}
                cmin = min(fr[k] for k, (kind, _) in refs.items() if kind == "crystal")
                amax = max(fr[k] for k, (kind, _) in refs.items() if kind == "amorphous")
                rows.append({"rc": rc, "thr": thr, "nmin": nmin, "crystal_min": cmin, "amorphous_max": amax,
                             "margin": cmin - amax, **fr})
                if best is None or cmin - amax > best["margin"]:
                    best = rows[-1]
    with open("calib_scan.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"best: q_rc {best['rc']}  q_thr {best['thr']}  q_nmin {best['nmin']}  "
          f"(crystal min {best['crystal_min']:.3f}, amorphous max {best['amorphous_max']:.3f})")
    for k, (kind, _) in refs.items():
        print(f"  {kind:9s} {k:40s} xfracGST {best[k]:.3f}")
    default = next(r for r in rows if (r["rc"], r["thr"], r["nmin"]) == (3.6, 0.5, 4))
    print(f"current default (3.6, 0.5, 4): crystal min {default['crystal_min']:.3f}, "
          f"amorphous max {default['amorphous_max']:.3f}")
    scanned = (("q_rc", "rc", RC), ("q_thr", "thr", THR), ("q_nmin", "nmin", NMIN))
    edges = [f"{name} {best[key]}" for name, key, grid in scanned if best[key] in (grid[0], grid[-1])]
    # fix halt level for the anneals: below what a fully crystallized sample reads at that temperature
    by_T = {}
    for k, (kind, _) in refs.items():
        m = re.search(r"_(\d+)K", k)
        if kind == "crystal" and m:
            by_T.setdefault(int(m[1]), []).append(best[k])
    for T, xs in sorted(by_T.items()):
        print(f"suggested XSTOP at {T} K: {0.85 * min(xs):.2f}  (0.85 x the lowest crystal-reference xfracGST, "
              f"{min(xs):.3f}; pass also --x-crystal {min(xs):.3f} to recryst_summary.py)")
    if edges:
        print("WARNING: the best criterion is at the edge of the scanned grid (" + ", ".join(edges) + "); the optimum "
              "may lie outside it, so extend RC/THR/NMIN in calibrate.py and rerun")
    crits = list(dict.fromkeys([(best["rc"], best["thr"], best["nmin"]), (3.6, 0.5, 4)]))
    nucleation_thresholds(a.amorphous, crits)
    plot(refs, rows, best, default)
    print("wrote calib_scan.csv, calib.png")


# palette: categorical slots 1-2 (crystal, amorphous) and chart ink of the reference palette (dataviz skill)
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
KIND_COLOR = {"crystal": "#2a78d6", "amorphous": "#eb6834"}


def plot(refs, rows, best, default):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": AXIS,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURFACE,
                         "figure.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False})
    names = sorted(refs, key=lambda k: (refs[k][0] != "crystal", k))
    fig, ax = plt.subplots(1, 3, figsize=(13, 0.28 * len(names) + 2.2), gridspec_kw={"width_ratios": [1.3, 1, 1]})
    # (a) per-reference crystalline fraction
    y = np.arange(len(names))
    for yi, k in zip(y, names):
        c = KIND_COLOR[refs[k][0]]
        ax[0].plot([default[k], best[k]], [yi, yi], color=GRID, lw=1.5, zorder=1)
        ax[0].plot(default[k], yi, "o", ms=6, mfc=SURFACE, mec=c, mew=1.5, zorder=2)
        ax[0].plot(best[k], yi, "o", ms=6, color=c, zorder=3)
    ax[0].set_yticks(y, [k.replace(".lammpstrj.gz", "") for k in names])
    ax[0].invert_yaxis()
    ax[0].set_xlim(-0.02, 1.02)
    ax[0].set_xlabel("crystalline fraction of Ge/Sb/Te")
    ax[0].grid(axis="x", color=GRID, lw=0.6)
    ax[0].set_title(f"(a) chosen ({best['rc']}, {best['thr']}, {best['nmin']}) filled, default (3.6, 0.5, 4) open",
                    loc="left", fontsize=9)
    handles = [plt.Line2D([], [], marker="o", ls="", color=KIND_COLOR[kd], ms=6, label=f"{kd} references")
               for kd in ("crystal", "amorphous")]
    ax[0].legend(handles=handles, frameon=False, loc="lower right")
    # (b) crystal-like bond count distributions at the chosen rc, thr
    for kd in ("crystal", "amorphous"):
        k = THR.index(best["thr"])
        counts = np.concatenate([ncb[k] for _, (kind, fr) in refs.items() if kind == kd for ncb in fr[best["rc"]]])
        h = np.bincount(np.minimum(counts, 12), minlength=13) / len(counts)
        ax[1].step(np.arange(13), h, where="mid", color=KIND_COLOR[kd], lw=1.5, label=kd)
    ax[1].axvline(best["nmin"] - 0.5, color=INK2, lw=1, ls="--")
    ax[1].text(best["nmin"] - 0.4, ax[1].get_ylim()[1] * 0.95, f"crystalline: >= {best['nmin']}", color=INK2,
               va="top", fontsize=8)
    ax[1].set_xlabel("crystal-like bonds per atom (12 = 12 or more)")
    ax[1].set_ylabel("fraction of Ge/Sb/Te atoms")
    ax[1].grid(axis="y", color=GRID, lw=0.6)
    ax[1].legend(frameon=False)
    ax[1].set_title(f"(b) q_rc {best['rc']} A, q_thr {best['thr']}", loc="left", fontsize=9)
    # (c) margin over thr x nmin at the chosen rc
    grid = np.array([[next(r["margin"] for r in rows if (r["rc"], r["thr"], r["nmin"]) == (best["rc"], th, nm))
                      for nm in NMIN] for th in THR])
    im = ax[2].imshow(grid, cmap="Blues", vmin=min(0, grid.min()), vmax=1, origin="lower", aspect="auto")
    ax[2].set_xticks(range(len(NMIN)), NMIN)
    ax[2].set_yticks(range(len(THR)), THR)
    ax[2].set_xlabel("q_nmin")
    ax[2].set_ylabel("q_thr")
    bi, bj = THR.index(best["thr"]), NMIN.index(best["nmin"])
    ax[2].plot(bj, bi, "s", ms=14, mfc="none", mec=INK, mew=1.5)
    for i in range(len(THR)):
        for j in range(len(NMIN)):
            ax[2].text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=7,
                       color="#ffffff" if grid[i, j] > 0.6 else INK)
    ax[2].set_title(f"(c) margin at q_rc {best['rc']} A (box: chosen)", loc="left", fontsize=9)
    fig.colorbar(im, ax=ax[2], shrink=0.8).outline.set_visible(False)
    fig.tight_layout()
    fig.savefig("calib.png", dpi=150)


if __name__ == "__main__":
    main()
