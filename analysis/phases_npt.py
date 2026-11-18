"""Density and cell of the phases NPT runs (phases/in.npt, submit_npt.sh), per potential and across potentials.

For every run phases/runs/<MODEL_ID>/npt/<phase>_r<k>/thermo.dat (time T PE P V/atom rho lx ly lz xy xz yz, every
100 steps): the mean density, PE, T and P after NPT_AVG_PS (default 100 ps); the drift of the density over that
window (linear fit, g/cc per 100 ps); its block error (std of four equal blocks / 2); and for the crystals the mean
cell lengths relative to the starting cell. Per phase: the mean over replicas and its standard error (sample std /
sqrt(n)); the seeds of one amorphous phase settle at different densities (each glass keeps its own structure), so
that error is the one to quote. Then each crystal against the amorphous cell of the same potential.

Writes phases/results/<MODEL_ID>/npt_runs.txt and npt_summary.txt for each model given, and with two or more models
phases/results/npt_compare.txt (one table of every model).

Usage: python analysis/phases_npt.py [--avg-ps 100] MODEL_ID [MODEL_ID ...]
"""
import argparse
from pathlib import Path

import numpy as np

PH = Path(__file__).resolve().parents[1] / "phases"


def run_stats(run, avg_ps):
    d = np.loadtxt(run / "thermo.dat", skiprows=1)
    t, rho = d[:, 0], d[:, 5]
    w = t > avg_ps
    edges = np.linspace(t[w][0], t[w][-1], 5)
    blocks = [rho[w][(t[w] >= a) & (t[w] <= b)].mean() for a, b in zip(edges[:-1], edges[1:])]
    out = {"rho": rho[w].mean(), "rho_err": np.std(blocks, ddof=1) / 2, "drift": np.polyfit(t[w], rho[w], 1)[0] * 100,
           "PE": d[w, 2].mean(), "T": d[w, 1].mean(), "P": d[w, 3].mean(), "t_end": t[-1]}
    if d.shape[1] >= 9:
        out["cell"] = d[w, 6:9].mean(0) / d[0, 6:9] - 1
    return out


def model_stats(model, avg_ps):
    runs = sorted((PH / "runs" / model / "npt").glob("*_r*"))
    if not runs:
        raise SystemExit(f"no runs in phases/runs/{model}/npt/")
    per = {r.name: run_stats(r, avg_ps) for r in runs}
    phases = sorted({n.rsplit("_r", 1)[0] for n in per}, key=lambda p: (not p.startswith("am"), p))
    summ = {}
    for p in phases:
        rs = [per[n] for n in per if n.rsplit("_r", 1)[0] == p]
        v = np.array([r["rho"] for r in rs])
        summ[p] = {"n": len(v), "rho": v.mean(), "se": v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.nan,
                   "PE": np.mean([r["PE"] for r in rs]),
                   "cell": np.mean([r["cell"] for r in rs], 0) if "cell" in rs[0] else None}
    return per, summ


def gaps(summ):
    am = [p for p in summ if p.startswith("am")]
    if len(am) != 1:
        return {}
    a = summ[am[0]]
    return {p: (100 * (s["rho"] / a["rho"] - 1), 100 * np.hypot(s["se"], a["se"]) / a["rho"], 1000 * (s["PE"] - a["PE"]))
            for p, s in summ.items() if p != am[0]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="+")
    ap.add_argument("--avg-ps", type=float, default=100.0)
    a = ap.parse_args()
    head = f"# analysis/phases_npt.py: 300 K, 0 bar NPT (phases/in.npt); averages after {a.avg_ps:g} ps; rho in g/cc\n"
    allsum = {}
    for m in a.models:
        per, summ = model_stats(m, a.avg_ps)
        allsum[m] = summ
        res = PH / "results" / m
        res.mkdir(parents=True, exist_ok=True)
        lines = [head, "# MODEL_ID " + m + "\n",
                 f"{'run':14s} {'t_end':>6s} {'rho':>8s} {'+-blk':>7s} {'drift/100ps':>11s} {'T':>7s} {'P_bar':>7s} {'PE_eV':>8s}  cell lx ly lz vs start\n"]
        for n, r in per.items():
            c = " ".join(f"{100 * x:+.2f}%" for x in r["cell"]) if "cell" in r else ""
            lines.append(f"{n:14s} {r['t_end']:6.0f} {r['rho']:8.4f} {r['rho_err']:7.4f} {r['drift']:+11.4f} "
                         f"{r['T']:7.1f} {r['P']:7.0f} {r['PE']:8.4f}  {c}\n")
        (res / "npt_runs.txt").write_text("".join(lines))
        lines = [head, "# MODEL_ID " + m + "; +- = standard error over the replicas\n"]
        for p, s in summ.items():
            c = "  cell " + " ".join(f"{100 * x:+.2f}%" for x in s["cell"]) if s["cell"] is not None else ""
            lines.append(f"{p:10s} n={s['n']}  rho {s['rho']:.4f} +- {s['se']:.4f}  PE {s['PE']:.4f}{c}\n")
        for p, (g, e, dpe) in gaps(summ).items():
            lines.append(f"{p} - amorphous: {g:+.2f}% +- {e:.2f}% in density, {dpe:+.0f} meV/atom in PE\n")
        (res / "npt_summary.txt").write_text("".join(lines))
        print("".join(lines[2:]), end="")
    if len(a.models) > 1:
        phases = list(next(iter(allsum.values())))
        g = {m: gaps(s) for m, s in allsum.items()}
        cols = [p for p in phases if not p.startswith("am")]
        lines = [head, "# rho +- standard error over the replicas; crystal - amorphous in % of the amorphous density\n",
                 f"{'model':22s}" + "".join(f"{p:>18s}" for p in phases) + "".join(f"{p + ' - am':>18s}" for p in cols) + "\n"]
        for m, s in allsum.items():
            lines.append(f"{m:22s}" + "".join(f"{s[p]['rho']:10.3f} +- {s[p]['se']:.3f}" for p in phases)
                         + "".join(f"{g[m][p][0]:+9.2f}% +- {g[m][p][1]:.2f}" for p in cols) + "\n")
        (PH / "results" / "npt_compare.txt").write_text("".join(lines))
        print("".join(lines), end="")


if __name__ == "__main__":
    main()
