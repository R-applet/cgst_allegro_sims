"""Phase C of the anneal grid (recryst/README.md, RUNBOOK.md recryst step 6): growth kinetics vs anneal temperature Ta
per composition, from recryst/results/<MODEL_ID>/growth_table.csv and grid_verdict.txt (scripts/analyze_grid.sh verdict).

v_growth here is the largest Q4 cluster's radius slope (recryst_summary.py). In multi-grain runs it is a coalescence
rate, 3-20x the interface velocity (recryst/results/nequip_no_zbl/RESULTS.md section 2); the interface velocity is
v_flux from analysis/plot_grains.py (figures/grains_v). The figures below label it "largest-cluster growth rate".
Per run, v_growth is used when it is finite and > 0. A run with single_grain < 0.8 had a second grain for over 20% of
its v_growth window, so its v_growth is an upper bound: drawn hollow, counted in the mean, and counted in n_upper.
t50 is measured toward each composition's X_END (params X_END / X_END_CELL); a composition with its own X_END
(x10: 0.40) has a t50 at a lower xfracGST, not comparable with the others (drawn hollow and labelled).

Writes recryst/results/<MODEL_ID>/growth_summary.csv (per composition and Ta: nucleated k of n, v_growth mean, sample
std, n used, n_upper, n excluded, t_nuc and t50 mean +- std with their n) and figures/<name>.png (200 dpi) + .pdf:
  growth_v_vs_T     v_growth vs Ta per composition (log scale): replicates, mean line, n where below the replicas
  growth_v_rel_x0   v_growth / v_growth(x0) at the same Ta vs carbon content, one line per Ta (how C slows growth)
  growth_times      t_nuc (first nucleus) and t50 vs Ta per composition, side by side (one y-scale each)
Colors (dataviz skill, validated with its validate_palette.py --ordinal on the #fcfcfb surface, all checks pass):
composition = blue ordinal ramp (light = no C, dark = 10% C), plus a marker per composition and direct labels;
Ta = orange ordinal ramp. Ta with no nucleation in MAX_NS (TOO COLD) have no points; the figures say which.

Usage (from the repository root, light; the login node is fine):
  MODEL_ID=nequip_no_zbl env/cgst-ana/bin/python analysis/plot_growth.py
"""
import csv
import math
import os
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = os.environ.get("MODEL_ID", "nequip_no_zbl")
RES = ROOT / "recryst" / "results" / MODEL_ID
FIG = RES / "figures"
CELLS = ["x0", "x1", "x2p5", "x5", "x10"]
C_AT = {"x0": 0.0, "x1": 1.07, "x2p5": 2.54, "x5": 5.14, "x10": 9.96}      # actual at.% C (README.md)
LABEL = {"x0": "GST", "x1": "+1% C", "x2p5": "+2.5% C", "x5": "+5% C", "x10": "+10% C"}
COLOR = dict(zip(CELLS, ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]))   # blue ramp 250/350/450/550/700
MARK = dict(zip(CELLS, ["o", "s", "D", "^", "v"]))
TA_COLORS = ["#f29a6e", "#eb6834", "#b84a1c", "#7a2e0e"]                         # orange ramp, light -> dark
SG_MIN = 0.8
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "font.size": 9,
    "font.family": "DejaVu Sans", "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left", "xtick.color": MUTED,
    "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "lines.linewidth": 1.4, "legend.frameon": False, "legend.labelcolor": INK2})


def num(s):
    try:
        return float(s)
    except ValueError:
        return math.nan


def load():
    """growth_table.csv rows by (cell, Ta), the '#' header, and grid_verdict.txt as {(cell, Ta): (verdict, k, n)}."""
    lines = (RES / "growth_table.csv").read_text().splitlines()
    header = lines[0]
    if f"MODEL_ID {MODEL_ID}" not in header:
        raise SystemExit(f"growth_table.csv is not {MODEL_ID}'s: {header}")
    runs = {}
    for r in csv.DictReader(lines[1:]):
        runs.setdefault((r["cell"], int(r["Ta"])), []).append({k: num(v) for k, v in r.items() if k != "cell"})
    verdict = {}
    for line in (RES / "grid_verdict.txt").read_text().splitlines():
        m = re.match(r"(\S+)\s+T(\d+): (TOO HOT|TOO COLD|USABLE)\s+nucleated (\d+) of (\d+)", line)
        if m:
            verdict[(m[1], int(m[2]))] = (m[3], int(m[4]), int(m[5]))
    x_end = dict(re.findall(r"\((\w+) ([0-9.]+)\)", header))              # per-cell X_END overrides in the header
    return header, runs, verdict, x_end


def stats(vals):
    v = np.array([x for x in vals if np.isfinite(x)])
    return (v.mean() if len(v) else math.nan, v.std(ddof=1) if len(v) > 1 else math.nan, len(v))


def summarize(runs, verdict):
    rows = []
    for c in CELLS:
        for T in sorted(t for cc, t in runs if cc == c):
            rr = runs[(c, T)]
            good = [r for r in rr if np.isfinite(r["v_growth_m_s"]) and r["v_growth_m_s"] > 0]
            vm, vs, n = stats([r["v_growth_m_s"] for r in good])
            tn = stats([r["t_nuc_ps"] for r in rr])
            t5 = stats([r["t50_ps"] for r in rr])
            vd, k, nn = verdict.get((c, T), ("?", 0, len(rr)))
            rows.append(dict(cell=c, C_at=C_AT[c], Ta=T, verdict=vd, nucleated=k, runs=nn, v_mean=vm, v_std=vs,
                             v_n=n, v_n_upper=sum(not r["single_grain"] >= SG_MIN for r in good),
                             v_n_excluded=sum(np.isfinite(r["t_nuc_ps"]) for r in rr) - n,
                             t_nuc_mean=tn[0], t_nuc_std=tn[1], t_nuc_n=tn[2],
                             t50_mean=t5[0], t50_std=t5[1], t50_n=t5[2]))
    return rows


def write_summary(rows, header):
    keys = list(rows[0])
    with open(RES / "growth_summary.csv", "w") as f:
        f.write(header + f"; v_growth used if finite and > 0; upper bound if single_grain < {SG_MIN}\n")
        f.write(",".join(keys) + "\n")
        for r in rows:
            f.write(",".join(f"{r[k]:.4g}" if isinstance(r[k], float) else str(r[k]) for k in keys) + "\n")


def save(fig, name):
    FIG.mkdir(exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def cold_note(verdict):
    cold = {}
    for (c, T), (vd, _, _) in verdict.items():
        if vd == "TOO COLD":
            cold.setdefault(T, []).append(LABEL[c])
    return "; ".join(f"No nucleation within 2 ns at {T} K: {', '.join(cs)}" for T, cs in sorted(cold.items()))


def plain_log(ax):
    """Log y-axis with plain-number labels on major and minor ticks (no 2x10^3)."""
    ax.set_yscale("log")
    f = matplotlib.ticker.FuncFormatter(lambda y, _: f"{y:g}")
    ax.yaxis.set_major_formatter(f)
    ax.yaxis.set_minor_formatter(matplotlib.ticker.FuncFormatter(
        lambda y, _: f"{y:g}" if f"{y:.1g}"[0] in "25" else ""))


def offset(c, width=6.0):
    return (CELLS.index(c) - 2) * width / 4                              # K, keeps replicas of one Ta apart


def fig_v_vs_T(runs, rows, verdict):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for c in CELLS:
        col, mk = COLOR[c], MARK[c]
        for (cc, T), rr in runs.items():
            if cc != c:
                continue
            for r in rr:
                v = r["v_growth_m_s"]
                if not (np.isfinite(v) and v > 0):
                    continue
                up = not r["single_grain"] >= SG_MIN
                ax.scatter(T + offset(c), v, s=16, marker=mk, lw=0.9, zorder=3, alpha=0.55,
                           facecolor="none" if up else col, edgecolor=col)
        pts = [(r["Ta"], r["v_mean"], r["v_n"]) for r in rows if r["cell"] == c and r["v_n"] > 0]
        if not pts:
            continue
        T, v, n = map(np.array, zip(*pts))
        ax.plot(T + offset(c), v, color=col, marker=mk, ms=7, mec=SURF, mew=1.2, zorder=4)
        for t, vv, nn in pts:
            if nn < 3:
                ax.annotate(f"n={nn}", (t + offset(c), vv), xytext=(5, -9), textcoords="offset points",
                            fontsize=7, color=INK2)
        ax.annotate(LABEL[c], (T[-1] + offset(c), v[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK)
    plain_log(ax)
    ax.set_xlabel("anneal temperature Ta (K)")
    ax.set_ylabel("largest-cluster growth rate (m/s)")
    ax.set_xticks(sorted({T for _, T in runs}))
    ax.set_xlim(right=max(T for _, T in runs) + 45)
    ax.set_title(f"Largest-cluster growth rate vs Ta ({MODEL_ID}; coalescence, not interface v)", fontsize=9)
    h = [plt.Line2D([], [], color=COLOR[c], marker=MARK[c], ms=6, label=LABEL[c]) for c in CELLS]
    h += [plt.Line2D([], [], ls="", marker="o", ms=4, color=MUTED, alpha=0.7, label="replica"),
          plt.Line2D([], [], ls="", marker="o", ms=4, mfc="none", color=MUTED, label=f"replica, upper bound "
                     f"(single_grain < {SG_MIN})")]
    ax.legend(handles=h, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=7.5)
    fig.text(0.01, -0.02, "Lines: mean of the replicas with v_growth > 0 (n shown where fewer than 3). "
             + cold_note(verdict) + ".", fontsize=7, color=INK2, wrap=True)
    save(fig, "growth_v_vs_T")


def fig_v_rel(rows):
    ref = {r["Ta"]: r["v_mean"] for r in rows if r["cell"] == "x0" and r["v_n"] > 0}
    tas = [T for T in sorted(ref) if sum(r["Ta"] == T and r["v_n"] > 0 for r in rows) > 1]
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    if len(tas) > len(TA_COLORS):
        raise SystemExit(f"{len(tas)} Ta to compare, TA_COLORS has {len(TA_COLORS)}: add a validated step")
    for T, col in zip(tas, TA_COLORS[-len(tas):]):                     # darkest = hottest
        pts = [(r["C_at"], r["v_mean"] / ref[T], r["cell"]) for r in rows if r["Ta"] == T and r["v_n"] > 0]
        x, y, _ = zip(*pts)
        for r in rows:
            if r["Ta"] == T and 0 < r["v_n"] < 3:
                ax.annotate(f"n={r['v_n']}", (r["C_at"], r["v_mean"] / ref[T]), xytext=(5, -10),
                            textcoords="offset points", fontsize=7, color=INK2)
        ax.plot(x, y, color=col, marker="o", ms=6, mec=SURF, mew=1.2, label=f"{T} K")
        ax.annotate(f"{T} K", (x[-1], y[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=8, color=INK)
    ax.axhline(1, color=AXIS, lw=1, zorder=0)
    plain_log(ax)
    ax.set_xticks(list(C_AT.values()), [f"{v:g}" for v in C_AT.values()])
    ax.set_xlim(-0.5, 11.8)
    ax.set_xlabel("carbon content (at.%)")
    ax.set_ylabel("v_growth / v_growth of GST at the same Ta")
    ax.set_title("Largest-cluster growth rate relative to GST")
    ax.legend(loc="lower left", fontsize=8)
    save(fig, "growth_v_rel_x0")


def fig_times(runs, rows, verdict, x_end):
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 3.8))
    for ax, key, title in ((axs[0], "t_nuc_ps", "First nucleus, t_nuc"), (axs[1], "t50_ps", "Half-crystallized, t50")):
        for c in CELLS:
            col, mk = COLOR[c], MARK[c]
            own = key == "t50_ps" and c in x_end                         # its own X_END: not comparable
            for (cc, T), rr in runs.items():
                if cc == c:
                    for r in rr:
                        if np.isfinite(r[key]):
                            ax.scatter(T + offset(c), r[key], s=14, marker=mk, alpha=0.5, lw=0.9, zorder=3,
                                       facecolor="none" if own else col, edgecolor=col)
            mean = "t_nuc_mean" if key == "t_nuc_ps" else "t50_mean"
            nk = "t_nuc_n" if key == "t_nuc_ps" else "t50_n"
            pts = [(r["Ta"], r[mean], r[nk]) for r in rows if r["cell"] == c and r[nk] > 0]
            if not pts:
                continue
            T, y, n = map(np.array, zip(*pts))
            ax.plot(T + offset(c), y, color=col, marker=mk, ms=6, mec=SURF if not own else col, mew=1.2,
                    mfc="none" if own else col, ls="--" if own else "-", zorder=4,
                    label=LABEL[c] + (f" (X_END {x_end[c]}: not comparable)" if own else ""))
            for t, yy, nn in pts:
                if nn < 3:
                    ax.annotate(f"n={nn}", (t + offset(c), yy), xytext=(5, -9), textcoords="offset points",
                                fontsize=7, color=INK2)
        plain_log(ax)
        ax.set_xticks(sorted({T for _, T in runs}))
        ax.set_xlabel("anneal temperature Ta (K)")
        ax.set_ylabel("time in the hold (ps)")
        ax.set_title(title)
        ax.axhline(2000, color=AXIS, lw=1, ls=":", zorder=0)
        ax.annotate("end of hold (2 ns)", (ax.get_xlim()[1], 2000), xytext=(-2, 3), textcoords="offset points",
                    fontsize=7, color=MUTED, ha="right")
    fig.legend(*axs[1].get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=5,
               fontsize=7.5)
    fig.text(0.01, -0.12, "Lines: mean of the replicas that reached the point (n shown where fewer than 3); t50 at "
             "half of each composition's X_END. " + cold_note(verdict) + ".", fontsize=7, color=INK2, wrap=True)
    fig.tight_layout()
    save(fig, "growth_times")


def main():
    header, runs, verdict, x_end = load()
    rows = summarize(runs, verdict)
    write_summary(rows, header)
    fig_v_vs_T(runs, rows, verdict)
    fig_v_rel(rows)
    fig_times(runs, rows, verdict, x_end)
    print(f"wrote {RES / 'growth_summary.csv'} and {FIG}/growth_{{v_vs_T,v_rel_x0,times}}.{{png,pdf}}")


if __name__ == "__main__":
    main()
