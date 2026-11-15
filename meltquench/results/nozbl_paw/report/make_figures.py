"""Figures for the melt-quench report and slides of this model (the MODEL_ID is the parent directory's name), from
meltquench/results/<MODEL_ID> and meltquench/runs/<MODEL_ID>; run5_ep301's results are drawn for comparison.

Writes report/figures/<name>.png (200 dpi, slides) and <name>.pdf (vector, LaTeX):
  density_vs_T       rho(T) on the 10 K/ps heating ramp and quench, mean of 3 replicas per composition
  properties_vs_C    rho_glass, rho_liquid, Tm_app, Tg against C content (mean +- sample std, 3 replicas), with
                     run5_ep301 (3x3x3) in gray
  quench_order       xfracGST during the quench at 10, 5 and 1 K/ps, for x0 and x10
  coordination_vs_C  mean coordination of Ge, Sb, Te, C against C content, with run5_ep301 in gray
  ge_angles          Ge bond-angle distribution per composition
  c_angles           C-centred bond-angle distribution per composition (1-10% C), and x10 at 10, 5 and 1 K/ps
  sq_nn              Bhatia-Thornton S_NN(q) per composition
  carbon_clustering  fraction of C bonded to C vs C content (run5_ep301 in gray); C cluster sizes in x10 per rate
  c_cutoffs          x10 partial g(r) for C pairs with the fixed bond cutoffs (checked on production glasses)
Colors (dataviz skill, validated with its validate_palette.js): compositions are ordinal -> one blue ramp,
light -> dark with C (#86b6ef #5598e7 #2a78d6 #1c5cab #104281, --ordinal: all checks pass); the two quench rates
are categorical slots 1-3 (10 K/ps #2a78d6, 1 K/ps #eb6834, 5 K/ps #1baf7a; all-pairs checks pass, worst CVD dE 9.2;
#1baf7a is below 3:1 contrast, so 5 K/ps is also dashed or hatched). run5_ep301 comparison: muted gray, dashed.
Light surface only (print and slides). Single-replica 5 and 1 K/ps values come from mq_summary_rates.txt.

Usage: env/cgst-ana/bin/python meltquench/results/<MODEL_ID>/report/make_figures.py
"""
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
MODEL_ID = Path(__file__).resolve().parents[1].name   # this report lives in meltquench/results/<MODEL_ID>/report
sys.path.insert(0, str(ROOT / "analysis"))
from mq_summary import load_rdf  # noqa: E402
from runio import load_dat  # noqa: E402

RES, RUNS = ROOT / "meltquench/results" / MODEL_ID, ROOT / "meltquench/runs" / MODEL_ID
OUT = Path(__file__).resolve().parent / "figures"
CELLS = ["x0", "x1", "x2p5", "x5", "x10"]
XC = {"x0": 0.0, "x1": 1.07, "x2p5": 2.54, "x5": 5.14, "x10": 9.96}            # actual at.% C (README.md)
LABEL = {c: f"{XC[c]:g}% C" if c != "x0" else "0% C (GST)" for c in CELLS}
RAMP = dict(zip(CELLS, ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]))
RATE = {"10 K/ps": "#2a78d6", "5 K/ps": "#1baf7a", "1 K/ps": "#eb6834"}
RATES = (("10 K/ps", "q10"), ("5 K/ps", "q5"), ("1 K/ps", "q1"))
LS = {"10 K/ps": "-", "5 K/ps": "--", "1 K/ps": "-"}
REF = ROOT / "meltquench/results/run5_ep301"     # comparison model
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "font.size": 10,
    "font.family": "DejaVu Sans", "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left", "xtick.color": MUTED,
    "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-", "axes.spines.top": False,
    "axes.spines.right": False, "axes.axisbelow": True, "lines.linewidth": 1.6, "legend.frameon": False, "legend.labelcolor": INK2,
})


def table(path):
    """Header line (first non-# line) + numeric rows of a results .dat file -> dict of columns (stage kept as str)."""
    lines = [l.split() for l in Path(path).read_text().splitlines() if l.strip() and not l.startswith("#")]
    head, rows = lines[0], lines[1:]
    cols = {}
    for k, h in enumerate(head):
        vals = [r[k] for r in rows]
        try:
            cols[h] = np.array([float(v) for v in vals])
        except ValueError:
            cols[h] = np.array(vals)
    return cols


def groups(res=RES):
    """mq_summary.txt group lines -> {group: {key: (mean, std)}}."""
    txt = (res / "mq_summary.txt").read_text().splitlines()
    keys = txt[0].split()[1:]
    out = {}
    for i, l in enumerate(txt):
        m = re.match(r"(x\w+_q\d+)\s+n=\d+\s+(.*)", l)
        if m:
            means = [float(v) for v in m[2].split()]
            stds = [float(v) for v in txt[i + 1].split()]
            out[m[1]] = {k: (a, b) for k, a, b in zip(keys, means, stds)}
    return out


def runs_table():
    """mq_summary_rates.txt per-run rows (x0 and x10 at every rate) -> {run: {key: value}}."""
    txt = (RES / "mq_summary_rates.txt").read_text().splitlines()
    keys = txt[0].split()[1:]
    out = {}
    for l in txt[1:]:
        f = l.split()
        if f and re.match(r"x\w+_q\d+_r\d+$", f[0]):
            out[f[0]] = dict(zip(keys, [float(v) for v in f[1:]]))
    return out


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote figures/{name}.png/.pdf")


def comp_legend(ax, **kw):
    ax.legend(title="composition", title_fontsize=9, fontsize=9, **kw)


def density_vs_T():
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, stage, title in zip(axs, ("heat", "quench"), ("Heating, 300 → 1500 K at 10 K/ps", "Quench, 1500 → 300 K at 10 K/ps")):
        for c in CELLS:
            d = table(RES / f"{c}_q10_curves.dat")
            m = d["stage"] == stage
            ax.plot(d["T_K"][m], d["rho_mean"][m], color=RAMP[c], label=LABEL[c])
        ax.set_title(title)
        ax.set_xlabel("temperature (K)")
    axs[0].set_ylabel("density (g/cm³)")
    comp_legend(axs[1], loc="upper right")
    axs[0].annotate("melting: density drops", xy=(1110, 5.75), xytext=(560, 5.62), color=INK2, fontsize=9,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    save(fig, "density_vs_T")


def properties_vs_C():
    g, g5 = groups(), groups(REF)
    x = np.array([XC[c] for c in CELLS])
    specs = [("rho_a", "Glass density at 300 K", "g/cm³"), ("rho_l", "Liquid density at 1500 K", "g/cm³"),
             ("Tm_app", "Apparent melting point (10 K/ps)", "K"),
             ("Tg", "Glass transition (bilinear fit)\nreplica scatter exceeds any C trend", "K")]
    fig, axs = plt.subplots(1, 4, figsize=(12, 3.0))
    for ax, (k, title, unit) in zip(axs, specs):
        m = np.array([g[f"{c}_q10"][k][0] for c in CELLS]); s = np.array([g[f"{c}_q10"][k][1] for c in CELLS])
        m5 = np.array([g5[f"{c}_q10"][k][0] for c in CELLS]); s5 = np.array([g5[f"{c}_q10"][k][1] for c in CELLS])
        ax.errorbar(x, m5, yerr=s5, color=MUTED, ls="--", marker="o", mfc=SURF, ms=4.5, capsize=3, lw=1.2,
                    elinewidth=0.8, label="run5_ep301 (3×3×3)")
        ax.errorbar(x, m, yerr=s, color=RAMP["x2p5"], marker="o", ms=5, capsize=3, lw=1.6, elinewidth=1.0,
                    label=f"{MODEL_ID} (4×4×4)")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("C content (at.%)"); ax.set_ylabel(unit)
    axs[0].legend(fontsize=8.5, loc="lower left")
    fig.tight_layout(w_pad=2.0)
    save(fig, "properties_vs_C")


def quench_xfrac(run):
    d = load_dat(RUNS / run / "mq.dat")
    st = dict(l.split()[:2] for l in open(RUNS / run / "stages.txt") if len(l.split()) >= 2)
    m = (d["time_ps"] >= float(st["quench_start_ps"])) & (d["time_ps"] <= float(st["quench_end_ps"]))
    T, x = d["T_K"][m], d["xfracGST"][m]
    bins = np.arange(300, 1501, 20)
    idx = np.digitize(T, bins)
    tc = np.array([T[idx == i].mean() for i in range(1, len(bins)) if (idx == i).any()])
    xc = np.array([x[idx == i].mean() for i in range(1, len(bins)) if (idx == i).any()])
    return tc, xc


def quench_order():
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, c in zip(axs, ("x0", "x10")):
        for rate, q in RATES:
            T, x = quench_xfrac(f"{c}_{q}_r1")
            ax.plot(T, x, color=RATE[rate], ls=LS[rate], label=f"quench {rate}")
            ax.text(T[0] - 12, x[0], rate, color=INK2, fontsize=8.5, va="center", ha="left")
        ax.set_title(f"{LABEL[c]}: crystal-like order on cooling")
        ax.set_xlim(1540, 200); ax.set_xlabel("temperature (K)")
    axs[0].set_ylabel("xfracGST (crystal-like Ge/Sb/Te)")
    axs[1].legend(loc="upper left", fontsize=9)
    save(fig, "quench_order")


def coordination_vs_C():
    g, g5 = groups(), groups(REF)
    fig, axs = plt.subplots(1, 4, figsize=(12, 2.8))
    for ax, sp in zip(axs, ("Ge", "Sb", "Te", "C")):
        cells = [c for c in CELLS if not (sp == "C" and c == "x0")]
        x = np.array([XC[c] for c in cells])
        m = np.array([g[f"{c}_q10"][f"Z_{sp}"][0] for c in cells]); s = np.array([g[f"{c}_q10"][f"Z_{sp}"][1] for c in cells])
        m5 = np.array([g5[f"{c}_q10"][f"Z_{sp}"][0] for c in cells])
        ax.plot(x, m5, color=MUTED, ls="--", marker="o", mfc=SURF, ms=4.5, lw=1.2, label="run5_ep301")
        ax.errorbar(x, m, yerr=s, color=RAMP["x5"], marker="o", ms=5, capsize=3, lw=1.6, elinewidth=1.0, label=MODEL_ID)
        ax.set_title(f"{sp}", fontsize=10); ax.set_xlabel("C content (at.%)")
    axs[0].set_ylabel("mean coordination Z")
    axs[3].legend(fontsize=8.5, loc="upper right")
    fig.suptitle("Coordination at 300 K (fixed bond cutoffs), 10 K/ps glasses", x=0.01, ha="left", fontsize=11,
                 fontweight="bold", color=INK)
    fig.tight_layout(w_pad=2.0)
    save(fig, "coordination_vs_C")


def ge_angles():
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    for c in CELLS:
        d = table(RES / f"{c}_q10_angles.dat")
        ax.plot(d["angle_deg"], d["Ge_mean"], color=RAMP[c], label=LABEL[c])
    for a, t, ha, dx in ((90, "90° octahedral", "right", -1.5), (109.5, "109.5° tetrahedral", "left", 1.5)):
        ax.axvline(a, color=MUTED, lw=0.8)
        ax.text(a + dx, ax.get_ylim()[1] * 0.97, t, color=INK2, fontsize=8.5, va="top", ha=ha)
    ax.set_xlim(40, 180); ax.set_xlabel("bond angle at Ge (deg)"); ax.set_ylabel("distribution (1/deg)")
    ax.set_title("Ge bond angles: octahedral-like, tetrahedral share grows with C")
    comp_legend(ax, loc="center right")
    save(fig, "ge_angles")


def c_angles():
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True, gridspec_kw={"width_ratios": [1.25, 1]})
    for c in ("x1", "x2p5", "x5", "x10"):
        d = table(RES / f"{c}_q10_angles.dat")
        axs[0].plot(d["angle_deg"], d["C_mean"], color=RAMP[c], label=LABEL[c])
    for rate, q in RATES:
        d = table(RES / f"x10_{q}_angles.dat")
        axs[1].plot(d["angle_deg"], d["C_mean"], color=RATE[rate], ls=LS[rate], label=f"quench {rate}")
    ymax = max(l.get_ydata().max() for ax in axs for l in ax.get_lines()) * 1.12
    for ax in axs:
        for a in (109.5, 120, 180):
            ax.axvline(a, color=MUTED, lw=0.8)
        ax.set_xlim(40, 182); ax.set_ylim(0, ymax); ax.set_xlabel("bond angle at C (deg)")
        ax.text(108, ymax * 0.98, "109.5° sp³", color=INK2, fontsize=8.5, va="top", ha="right")
        ax.text(121.5, ymax * 0.98, "120° sp²", color=INK2, fontsize=8.5, va="top", ha="left")
        ax.text(178.5, ymax * 0.98, "180° sp", color=INK2, fontsize=8.5, va="top", ha="right")
    axs[0].set_ylabel("distribution (1/deg)")
    axs[0].set_title("Bond angles at C, 10 K/ps glasses")
    axs[1].set_title("10% C: 10, 5 and 1 K/ps")
    comp_legend(axs[0], loc="center left")
    axs[1].legend(fontsize=9, loc="center left")
    fig.tight_layout(w_pad=1.5)
    save(fig, "c_angles")


def sq_nn():
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    for c in CELLS:
        d = table(RES / f"{c}_q10_sq.dat")
        ax.plot(d["q_invA"], d["SNN_mean"], color=RAMP[c], label=LABEL[c])
    ax.set_xlim(0.5, 12); ax.set_xlabel("q (Å⁻¹)"); ax.set_ylabel("S$_{NN}$(q)")
    ax.set_title("Bhatia–Thornton number–number structure factor, 300 K")
    comp_legend(ax, loc="upper right")
    save(fig, "sq_nn")


def cclusters(group):
    d = table(RES / f"{group}_cclusters.dat")
    return d["cluster_size"], d["mean"]


def carbon_clustering():
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.4))
    cells = ["x1", "x2p5", "x5", "x10"]
    frac = []
    for c in cells:
        s, f = cclusters(f"{c}_q10")
        frac.append(f[s > 1].sum())
    frac5 = []
    for c in cells:
        d = table(REF / f"{c}_q10_cclusters.dat")
        frac5.append(d["mean"][d["cluster_size"] > 1].sum())
    axs[0].plot([XC[c] for c in cells], frac5, color=MUTED, ls="--", marker="o", mfc=SURF, ms=5, lw=1.2, label="run5_ep301")
    axs[0].plot([XC[c] for c in cells], frac, color=RAMP["x5"], marker="o", ms=6, label=MODEL_ID)
    axs[0].legend(fontsize=8.5, loc="lower right")
    for c, v in zip(cells, frac):
        axs[0].text(XC[c] + 0.25, v - 0.035, f"{v:.2f}", color=INK2, fontsize=8.5)
    axs[0].set_ylim(0, 1); axs[0].set_xlabel("C content (at.%)"); axs[0].set_ylabel("fraction of C bonded to C")
    axs[0].set_title("C clusters as C content rises")
    edges = np.array([1, 2, 5, 10, 20, 50, 100, 300])
    labels = ["1", "2–4", "5–9", "10–19", "20–49", "50–99", "100+"]
    w = 0.27
    for k, (rate, q) in enumerate(RATES):
        s, f = cclusters(f"x10_{q}")
        h = [f[(s >= lo) & (s < hi)].sum() for lo, hi in zip(edges[:-1], edges[1:])]
        axs[1].bar(np.arange(len(h)) + (k - 1) * w, h, width=w - 0.03, color=RATE[rate], label=f"quench {rate}",
                   hatch="///" if rate == "5 K/ps" else None, edgecolor=SURF, linewidth=0)
    axs[1].set_xticks(np.arange(len(labels)), labels); axs[1].set_xlabel("C cluster size (C atoms)")
    axs[1].set_ylabel("fraction of C atoms"); axs[1].set_title("x10: C cluster sizes per quench rate")
    axs[1].legend(fontsize=9, loc="upper left")
    fig.tight_layout(w_pad=2.5)
    save(fig, "carbon_clustering")


def c_cutoffs():
    r, d = load_rdf(RUNS / "x10_q10_r1/rdf_300K.dat")
    fig, axs = plt.subplots(1, 3, figsize=(10, 2.9), sharey=False)
    for ax, (pair, nm, rc) in zip(axs, (((0, 3), "Ge–C", 2.5), ((1, 3), "Sb–C", 2.5), ((3, 3), "C–C", 1.9))):
        ax.plot(r, d[pair][0], color=RAMP["x10"])
        ax.axvline(rc, color=MUTED, lw=0.9)
        ax.text(rc + 0.08, ax.get_ylim()[1] * 0.9, f"cutoff {rc} Å", color=INK2, fontsize=8.5, va="top")
        ax.set_xlim(1.0, 4.5); ax.set_title(nm, fontsize=10); ax.set_xlabel("r (Å)")
    axs[0].set_ylabel("g(r), x10 glass at 300 K")
    fig.tight_layout(w_pad=2.0)
    save(fig, "c_cutoffs")


if __name__ == "__main__":
    for f in (density_vs_T, properties_vs_C, quench_order, coordination_vs_C, ge_angles, c_angles, sq_nn,
              carbon_clustering, c_cutoffs):
        f()
