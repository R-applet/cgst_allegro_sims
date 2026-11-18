"""Figures and the number table of the phases comparison report (phases/report/): every potential in MODELS against
DFT-MD in the 8 DFT cells (NVT, 300 K) and against each other at 0 bar (NPT).

Reads, for each model, the per-run analysis of phases/runs/<MODEL_ID>/nvt/<phase>[_eq25]_r<k>/analysis/ (written by
analysis/phases_compare.py analyze) and phases/runs/<MODEL_ID>/npt/<phase>_r<k>/thermo.dat (phases/in.npt), and the
DFT references in phases/dft/. Every metric is computed with analysis/phases_compare.py's own functions (metrics,
sbte_of, unit, ...), so the numbers equal phases/results/<MODEL_ID>/phases_summary.txt; the NPT averages use
analysis/phases_npt.py. The run directories are not tracked: rebuilding needs this checkout's runs.

Writes phases/report/figures/<name>.png (200 dpi, slides) and .pdf (LaTeX):
  metrics_summary  per phase: RDF misfit R, ADF overlap, total VDOS overlap, <nu_total> vs DFT (seeds and mean)
  rdf_all          total g(r) of the 8 cells, each potential's mean over seeds, DFT dashed
  adf_all          bond-angle distributions of the 8 cells
  vdos_all         total VDOS of the 8 cells, 0-10 THz
  nu_species       mean frequency of Ge, Sb, Te and C vs DFT (%), per phase
  c_vdos           VDOS of C in the 5 C-containing cells, 0-50 THz
  am_c10_detail    amorphous GST + 10% C, the largest RDF misfit: g(r) and g(r) - g_DFT(r) of every potential
  relaxation       the amorphous cells 20 ps later (_eq25 minus standard, paired by seed)
  npt_density      density at 300 K, 0 bar of amorphous, rocksalt and trigonal GST, with the DFT-cell density
and phases/report/metrics_compare.txt (every number the report and the slides quote).
Colors (dataviz skill, categorical slots 1-3 in order, validated with its validate_palette.py on the #fcfcfb surface:
all checks pass, worst CVD dE 9.2; #1baf7a is below 3:1 contrast, so rushik_zbl_pairwise is also dash-dot and a
triangle); DFT black dashed.

Usage (from the repository root): env/cgst-ana/bin/python phases/report/make_figures.py
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
import phases_compare as pc  # noqa: E402
import phases_npt as pn  # noqa: E402

OUT = Path(__file__).resolve().parent
FIG = OUT / "figures"
MODELS = ["nequip_no_zbl", "nequip_zbl", "rushik_zbl_pairwise"]
COLOR = dict(zip(MODELS, ["#2a78d6", "#eb6834", "#1baf7a"]))
LS = dict(zip(MODELS, ["-", "-", "-."]))
MARK = dict(zip(MODELS, ["o", "s", "^"]))
LABEL = {"nequip_no_zbl": "nequip_no_zbl (no ZBL)", "nequip_zbl": "nequip_zbl (ZBL, all pairs)",
         "rushik_zbl_pairwise": "rushik_zbl_pairwise (per-pair ZBL)"}
SURF, INK, INK2, MUTED, GRID, AXIS = pc.SURF, pc.INK, pc.INK2, pc.MUTED, pc.GRID, pc.AXIS
SHORT = {"am_gst": "a-GST", "am_c1": "a-GST+1.4% C", "am_c5": "a-GST+5.3% C", "am_c10": "a-GST+10% C",
         "cub_gst": "rocksalt", "cub_c1": "rocksalt+1.4% C", "hex_gst": "trigonal", "hex_c1": "trigonal+1.4% C"}
DFT_CELL_RHO = {"am_gst": 6.193, "cub_gst": 6.311, "hex_gst": 6.412}      # g/cc, phases/structures (144-atom cells)

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "font.size": 9,
    "font.family": "DejaVu Sans", "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left", "xtick.color": MUTED,
    "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "lines.linewidth": 1.4, "legend.frameon": False, "legend.labelcolor": INK2})


def load_model(model):
    """{group: [(run name, metrics, (rdf, adf, vdos))]} for every analysed NVT run, as phases_compare.compare."""
    out = {}
    for run in sorted((pc.PH / "runs" / model / "nvt").glob("*_r*")):
        a = run / "analysis"
        if not (a / "vdos_species.txt").exists():
            continue
        group, phase, _ = pc.split_name(run.name)
        adfs = {3.2: pc.load_adf(a / "adf.txt"), pc.SBTE_ALT: pc.load_adf(a / "adf_sbte34.txt")}
        sbte = pc.sbte_of(phase, model)
        data = (np.loadtxt(a / "rdf.txt"), adfs[sbte], np.loadtxt(a / "vdos_species.txt"))
        m = {"dPE_prod": pc.pe_drift(run, pc.PROD_PS), **pc.metrics(phase, *data, pc.load_dft(phase))}
        out.setdefault(group, []).append((run.name, m, data))
    if not out:
        sys.exit(f"no analysed runs in phases/runs/{model}/nvt/")
    return out


def save(fig, name):
    FIG.mkdir(exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote figures/{name}.png/.pdf")


def legend_below(fig, ncol=3, dft=True, dft_label="DFT-MD"):
    h = [plt.Line2D([], [], color=COLOR[m], ls=LS[m], marker=MARK[m], ms=5, label=LABEL[m]) for m in MODELS]
    if dft:
        h.append(plt.Line2D([], [], color=INK, ls="--", label=dft_label))
    fig.legend(handles=h, loc="lower center", ncol=len(h) if len(h) <= 4 else ncol, bbox_to_anchor=(0.5, -0.02))


def mean_curve(runs, k, col, f=None):
    L = min(len(x[2][k]) for x in runs)
    x = runs[0][2][k][:L, 0]
    ys = [x_[2][k][:L, col] for x_ in runs]
    if f:
        ys = [f(x, y) for y in ys]
    return x, np.mean(ys, axis=0)


def grid8(title):
    fig, ax = plt.subplots(2, 4, figsize=(12, 5.4), sharex=True)
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold")
    return fig, ax.ravel()


def metrics_summary(D):
    keys = [("R_rdf", "RDF misfit R (0 = DFT)", None), ("adf_overlap", "ADF overlap (1 = DFT)", None),
            ("S_total", "VDOS overlap (1 = DFT)", None), ("nu_total", "⟨ν⟩ vs DFT (%)", 0.0)]
    y = np.arange(len(pc.PHASES))[::-1]
    fig, ax = plt.subplots(1, 4, figsize=(12, 4.0), sharey=True)
    for a, (k, title, ref) in zip(ax, keys):
        for j, m in enumerate(MODELS):
            off = (j - 1) * 0.22
            for yi, p in zip(y, pc.PHASES):
                v = np.array([mm[k] for _, mm, _ in D[m][p]])
                if ref is not None:
                    v = 100 * (v / pc.dft_metrics(p, pc.load_dft(p))[k] - 1)
                a.scatter(v, np.full(len(v), yi + off), s=8, color=COLOR[m], alpha=0.4, lw=0, marker=MARK[m])
                a.scatter([v.mean()], [yi + off], s=34, color=COLOR[m], edgecolor=SURF, lw=0.8, marker=MARK[m])
        if ref is not None:
            a.axvline(ref, color=AXIS, lw=1.0, zorder=0)
        a.set_title(title)
        a.grid(axis="y", visible=False)
    ax[0].set_yticks(y, [SHORT[p] for p in pc.PHASES])
    fig.suptitle("Allegro vs DFT-MD at 300 K in the 8 DFT cells (small: seeds; large: mean of 3)", x=0.01, ha="left",
                 fontweight="bold")
    legend_below(fig, dft=False)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    save(fig, "metrics_summary")


def curves(D, name, title, k, col, xlim, xlabel, ylabel, dft_key, f=None, dft_col=1, phases=pc.PHASES):
    fig, ax = (plt.subplots(1, len(phases), figsize=(2.6 * len(phases), 2.9), sharex=True) if len(phases) < 8
               else grid8(title))
    ax = np.atleast_1d(ax).ravel()
    if len(phases) < 8:
        fig.suptitle(title, x=0.01, ha="left", fontweight="bold")
    for a, p in zip(ax, phases):
        dft = pc.load_dft(p)
        for m in MODELS:
            x, yv = mean_curve(D[m][p], k, col, f)
            a.plot(x, yv, color=COLOR[m], ls=LS[m], lw=1.2)
        dx, dy = dft[dft_key][:, 0], dft[dft_key][:, dft_col]
        if dft_key == "adf":
            dy = dy / (dy.sum() * 180.0 / len(dy))
        if f:
            dy = f(dx, dy)
        a.plot(dx, dy, "--", color=INK, lw=1.1)
        a.set_xlim(*xlim)
        a.set_title(SHORT[p], fontsize=9)
        a.set_xlabel(xlabel)
    ax[0].set_ylabel(ylabel)
    if len(phases) == 8:
        ax[4].set_ylabel(ylabel)
    legend_below(fig)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    save(fig, name)


def nu_species(D):
    fig, ax = plt.subplots(1, 4, figsize=(12, 3.8), sharey=True)
    y = np.arange(len(pc.PHASES))[::-1]
    for a, s in zip(ax, pc.SPECIES):
        for j, m in enumerate(MODELS):
            off = (j - 1) * 0.22
            for yi, p in zip(y, pc.PHASES):
                v = [mm.get(f"nu_{s}") for _, mm, _ in D[m][p]]
                if v[0] is None:
                    continue
                v = 100 * (np.array(v) / pc.dft_metrics(p, pc.load_dft(p))[f"nu_{s}"] - 1)
                a.errorbar(v.mean(), yi + off, xerr=v.std(ddof=1), color=COLOR[m], marker=MARK[m], ms=5, lw=1,
                           capsize=2, mec=SURF)
        a.axvline(0, color=AXIS, lw=1, zorder=0)
        a.set_title(f"⟨ν_{s}⟩ vs DFT (%)")
        a.grid(axis="y", visible=False)
    ax[0].set_yticks(y, [SHORT[p] for p in pc.PHASES])
    fig.suptitle("Mean vibrational frequency per species against DFT-MD (mean ± seed std)", x=0.01, ha="left",
                 fontweight="bold")
    legend_below(fig, dft=False)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    save(fig, "nu_species")


def am_c10_detail(D):
    p = "am_c10"
    dft = pc.load_dft(p)
    r, gD = dft["rdf"][:, 0], dft["rdf"][:, 1]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
    for m in MODELS:
        x, g = mean_curve(D[m][p], 0, 1)
        ax[0].plot(x, g, color=COLOR[m], ls=LS[m])
        ax[1].plot(r, np.interp(r, x, g) - gD, color=COLOR[m], ls=LS[m])
    ax[0].plot(r, gD, "--", color=INK)
    ax[0].set(xlim=(1.5, 6), xlabel="r (Å)", ylabel="g(r)", title="Total g(r), mean of 3 seeds")
    ax[1].axhline(0, color=INK, ls="--", lw=1)
    ax[1].set(xlim=(1.5, 6), ylim=(-0.3, 0.35), xlabel="r (Å)", ylabel="g(r) − g_DFT(r)", title="Difference from DFT-MD")
    for a in ax:
        a.axvspan(1.85, 2.3, color=GRID, alpha=0.5, lw=0, zorder=0)
        a.axvspan(3.4, 4.8, color=GRID, alpha=0.5, lw=0, zorder=0)
    ax[1].text(2.07, ax[1].get_ylim()[1] * 0.9, "C bonds", ha="center", color=INK2, fontsize=8)
    ax[1].text(4.1, ax[1].get_ylim()[1] * 0.9, "second shell", ha="center", color=INK2, fontsize=8)
    fig.suptitle("Amorphous GST + 10% C, the largest RDF misfit: the same deviation from DFT for every potential", x=0.01, ha="left",
                 fontweight="bold")
    legend_below(fig)
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    save(fig, "am_c10_detail")


def relaxation(D):
    am = ["am_gst", "am_c1", "am_c5", "am_c10"]
    fig, ax = plt.subplots(1, 3, figsize=(11, 3.2), sharey=True)
    y = np.arange(len(am))[::-1]
    specs = [("dPE_prod", "PE drift in the window (meV/atom)", 1000, "both"), ("S_total", "Δ VDOS overlap", 1, "delta"),
             ("nu_total", "Δ⟨ν⟩ (THz)", 1, "delta")]
    for a, (k, title, sc, mode) in zip(ax, specs):
        for j, m in enumerate(MODELS):
            off = (j - 1) * 0.22
            for yi, p in zip(y, am):
                std = {n.rsplit("_r", 1)[1]: mm[k] for n, mm, _ in D[m][p]}
                eq = {n.rsplit("_r", 1)[1]: mm[k] for n, mm, _ in D[m][p + "_eq25"]}
                if mode == "both":
                    a.scatter([sc * np.mean(list(std.values()))], [yi + off], color=COLOR[m], marker=MARK[m], s=30)
                    a.scatter([sc * np.mean(list(eq.values()))], [yi + off], facecolor=SURF, edgecolor=COLOR[m],
                              marker=MARK[m], s=30)
                else:
                    d = sc * np.array([eq[r] - std[r] for r in std])
                    a.errorbar(d.mean(), yi + off, xerr=d.std(ddof=1), color=COLOR[m], marker=MARK[m], ms=5, lw=1,
                               capsize=2, mec=SURF)
        a.axvline(0, color=AXIS, lw=1, zorder=0)
        a.set_title(title)
        a.grid(axis="y", visible=False)
    ax[0].set_yticks(y, [SHORT[p] for p in am])
    ax[0].set_title("PE drift in the window (meV/atom)\nfilled: standard; open: 20 ps later", fontsize=9)
    ax[1].xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
    fig.suptitle("Relaxation of the amorphous cells: the window 20 ps later (_eq25), paired by seed (mean ± std)",
                 x=0.01, ha="left", fontweight="bold")
    legend_below(fig, dft=False)
    fig.tight_layout(rect=(0, 0.09, 1, 0.92))
    save(fig, "relaxation")


def npt_density(N):
    phases = ["am_gst", "cub_gst", "hex_gst"]
    names = {"am_gst": "amorphous", "cub_gst": "rocksalt", "hex_gst": "trigonal"}
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for i, p in enumerate(phases):
        for j, m in enumerate(MODELS):
            s = N[m][p]
            ax.errorbar(i + (j - 1) * 0.18, s["rho"], yerr=s["se"], color=COLOR[m], marker=MARK[m], ms=7, lw=1.2,
                        capsize=3, mec=SURF, ls="none")
        ax.plot([i - 0.36, i + 0.36], [DFT_CELL_RHO[p]] * 2, "--", color=INK, lw=1.1)
    ax.set_xticks(range(3), [names[p] for p in phases])
    ax.set_ylabel("density (g/cm³)")
    ax.set_title("Density at 300 K, 0 bar (mean ± standard error of 3 seeds); dashed: the DFT cell")
    ax.grid(axis="x", visible=False)
    legend_below(fig, ncol=2, dft_label="DFT cell (fixed volume)")
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    save(fig, "npt_density")


def table(D, N):
    keys = ["R_rdf", "g1", "adf_overlap", "adf_count_ratio", "S_total", "nu_total", "nu_Ge", "nu_Sb", "nu_Te", "S_C",
            "nu_C"]
    lines = ["# phases/report/make_figures.py: mean +- sample std over 3 seeds per model; DFT value where defined; nu in THz\n"]
    for p in pc.PHASES:
        d = pc.dft_metrics(p, pc.load_dft(p))
        lines.append(f"\n{p}\n")
        for k in keys:
            if k not in D[MODELS[0]][p][0][1]:
                continue
            row = [f"{k:16s}"]
            for m in MODELS:
                v = np.array([mm[k] for _, mm, _ in D[m][p]])
                row.append(f"{v.mean():9.4f} +- {v.std(ddof=1):7.4f}")
            row.append(f"   DFT {d[k]:.4f}" if k in d and k not in ("adf_overlap", "S_total", "S_C", "R_rdf") else "")
            lines.append("  ".join(row) + "\n")
    lines.append("\nrelaxation, _eq25 minus standard (paired by seed): mean +- std\n")
    for p in ["am_gst", "am_c1", "am_c5", "am_c10"]:
        for k in ("dPE_prod", "S_total", "nu_total", "nu_C"):
            row = [f"{p:8s} {k:9s}"]
            for m in MODELS:
                std = {n.rsplit("_r", 1)[1]: mm.get(k) for n, mm, _ in D[m][p]}
                eq = {n.rsplit("_r", 1)[1]: mm.get(k) for n, mm, _ in D[m][p + "_eq25"]}
                if None in std.values():
                    break
                dd = np.array([eq[r] - std[r] for r in std])
                row.append(f"{dd.mean():+9.4f} +- {dd.std(ddof=1):7.4f}")
            else:
                lines.append("  ".join(row) + "\n")
    lines.append("\nNPT 300 K, 0 bar: density (g/cc) mean +- standard error, PE (eV/atom)\n")
    for p in ["am_gst", "cub_gst", "hex_gst"]:
        lines.append(f"{p:8s} DFT cell {DFT_CELL_RHO[p]:.3f}  " + "  ".join(
            f"{m} {N[m][p]['rho']:.4f} +- {N[m][p]['se']:.4f} PE {N[m][p]['PE']:.4f}" for m in MODELS) + "\n")
    lines.append("header columns: " + "  ".join(MODELS) + "\n")
    (OUT / "metrics_compare.txt").write_text("".join(lines))
    print("wrote metrics_compare.txt")


def main():
    D = {m: load_model(m) for m in MODELS}
    N = {m: pn.model_stats(m, 100.0)[1] for m in MODELS}
    metrics_summary(D)
    curves(D, "rdf_all", "Total g(r), 300 K, DFT cells: mean of 3 seeds per potential", 0, 1, (1.5, 6), "r (Å)",
           "g(r)", "rdf")
    curves(D, "adf_all", "Bond-angle distribution, DFT cells", 1, 1, (40, 180), "angle (°)", "probability (1/°)",
           "adf")
    curves(D, "vdos_all", "Total vibrational DOS, DFT cells (normalized over 0–60 THz)", 2, 1, (0, 10),
           "frequency (THz)", "VDOS (1/THz)", "dos", f=pc.unit)
    nu_species(D)
    curves(D, "c_vdos", "Vibrational DOS of C", 2, 5, (0, 50), "frequency (THz)", "VDOS (1/THz)", "dos", f=pc.unit,
           dft_col=5, phases=["am_c1", "am_c5", "am_c10", "cub_c1", "hex_c1"])
    am_c10_detail(D)
    relaxation(D)
    npt_density(N)
    table(D, N)


if __name__ == "__main__":
    main()
