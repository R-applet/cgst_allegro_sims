"""Grain statistics from analysis/grains.py output (<run>/grains_r0.15_m30.txt) for x0, x1, x2p5 over the anneal grid.

Writes recryst/results/<MODEL_ID>/grains_summary.csv and figures/grains_*.png/.pdf:
  grains_size_dist   grain-size distributions per composition (pooled over replicas) at the first frame where
                     xfracGST >= X_CMP (a crystallized fraction every crystallizing run reaches), one panel per Ta
  grains_count       grains per cell vs Ta at X_CMP, per composition (replicas and mean)
  grains_v           interface velocity vs Ta, three estimates per composition:
                     v_flux (line): growth of all tracked grains between frames (a merged grain against the sum of
                       its parents, births excluded) / (n_Te x sum of grain areas), frames up to xfracGST X_FLUX,
                       pooled over replicas: an area-weighted mean with no merge bias and no size cap;
                     v_grain (dots, median in the csv): each grain's equivalent-radius slope from its birth until its
                       first merge or until it holds V_CAP Te atoms;
                     v_growth of recryst_summary (dashed, growth_summary.csv v_mean): slope of the largest Q4
                       cluster's radius at 10-25%. NOT an interface velocity: that cluster spans several grains and
                       grows mostly by coalescence (see budget below).
  budget check       (csv budget_flux, budget_cluster) each run's tracked grains (not 'lost') born at their observed
                     times with radius r(MIN_TE) + v (t - t_birth), extended volume -> X = 1 - exp(-V_ext/V); the
                     ratio X_pred/X_obs at the first frame with xfracGST >= X_FLUX (X_obs = Te in grains / all Te),
                     mean over runs. A velocity that describes the grains gives ~1; v_growth gives 3-11.
  grains_carbon      where C sits vs xfracGST: fraction of C in grain interiors and at boundaries, divided by the
                     same fraction for Ge/Sb (same sites): < 1 means C is rejected
Grain size: d_eq = (6 n V_Te / pi)^(1/3), n the template-matched Te atoms of the grain and V_Te the cell volume per Te
atom: the crystalline core of the grain, smaller than the grain with its disordered rim; compare between runs, not
with experimental grain sizes. The cell (~96 A) caps grains near 7 nm.

Usage: MODEL_ID=nequip_no_zbl env/cgst-ana/bin/python analysis/plot_grains.py
"""
import os
from math import pi
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import plot_growth as pg

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = os.environ.get("MODEL_ID", "nequip_no_zbl")
RUNS = ROOT / "recryst" / "runs" / MODEL_ID
RES = ROOT / "recryst" / "results" / MODEL_ID
CELLS = ["x0", "x1", "x2p5"]
TAS = [500, 550, 600, 650, 700]
X_CMP = 0.28            # x2p5 at 500 K ends at 0.288-0.291 after 2 ns: the highest level every crystallizing run reaches
X_FLUX = 0.45          # xfracGST: v_flux and the budget use frames up to here (before grains impinge heavily)
V_CAP = 800             # Te atoms: a grain's growth fit stops here (d_eq ~ 4 nm), well before it fills its share
FNAME = "grains_r0.15_m30.txt"
MIN_TE = 30             # grains.py MIN_TE: radius of a grain at birth in the budget check


def load(run):
    F, G, E = [], [], []
    for line in (run / FNAME).read_text().splitlines():
        w = line.split()
        if not w or w[0].startswith("#"):
            continue
        if w[0] == "F":
            F.append([float(x) for x in w[1:]])
        elif w[0] == "G":
            G.append([float(x) for x in w[1:4]])
        elif w[0] == "E":
            E.append((float(w[1]), w[2], [int(x) for x in w[3:]]))
    return np.array(F), np.array(G).reshape(-1, 3), E


def v_te(run):
    """(cell volume per Te atom A^3, number of Te atoms)"""
    d = np.genfromtxt(run / "anneal.dat", names=True)
    L = (run / "final.data").read_text().splitlines()
    n = int(next(l for l in L if l.strip().endswith(" atoms")).split()[0])
    i = next(k for k, l in enumerate(L) if l.startswith("Atoms"))
    n_te = sum(1 for l in L[i + 2:i + 2 + n] if l.split()[1] == "3")
    return d["V_A3_per_atom"][-200:].mean() * n / n_te, n_te


def rad(n, vte):
    return (3 * n * vte / (4 * pi)) ** (1 / 3)          # A


def flux(F, G, E, vte):
    """(sum of tracked-grain growth rates Te/ps, sum of n_Te x area A^-1) over frame pairs up to X_FLUX"""
    ts = F[:, 0]
    parents = {(t, tr[0]): tr[1:] for t, ev, tr in E if ev == "merge"}
    size = {t: {int(g[1]): g[2] for g in G[G[:, 0] == t]} for t in ts}
    num = den = 0.0
    for a, b, xa in zip(ts[:-1], ts[1:], F[:-1, 1]):
        if xa > X_FLUX:
            break
        for tr, nb in size[b].items():
            na = [size[a][p] for p in parents.get((b, tr), [tr]) if p in size[a]]
            if na:                                       # else a birth
                num += (nb - sum(na)) / (b - a)
                den += sum(4 * pi * rad(x, vte) ** 2 for x in na) / vte
    return num, den


def budget(F, E, vte, n_te, v):
    """X_pred / X_obs at the first frame with xfracGST >= X_FLUX for velocity v (m/s), NaN if never reached"""
    k = np.flatnonzero(F[:, 1] >= X_FLUX)
    if not len(k) or not np.isfinite(v) or F[k[0], 3] <= 0:
        return np.nan
    te = F[k[0], 0]
    lost = {tr[0] for t, ev, tr in E if ev == "lost"}
    births = [t for t, ev, tr in E if ev == "new" and tr[0] not in lost and t <= te]
    vext = sum(4 / 3 * pi * (rad(MIN_TE, vte) + v / 100 * (te - b)) ** 3 for b in births)
    return (1 - np.exp(-vext / (n_te * vte))) / (F[k[0], 3] / n_te)


def deq(n, vte):
    return (6 * n * vte / pi) ** (1 / 3) / 10            # nm


def per_run(run):
    F, G, E = load(run)
    vte, n_te = v_te(run)
    out = {"vte": vte, "n_te": n_te, "F": F, "E": E, "flux": flux(F, G, E, vte)}
    k = np.flatnonzero(F[:, 1] >= X_CMP)
    if len(k):
        t = F[k[0], 0]
        out["t_cmp"] = t
        out["sizes_cmp"] = G[G[:, 0] == t, 2]
    out["sizes_end"] = G[G[:, 0] == F[-1, 0], 2]
    merged = {}
    for t, ev, tr in E:
        if ev == "merge":
            for p in tr:
                merged.setdefault(p, t)
    v = []
    for tr in np.unique(G[:, 1]):
        g = G[G[:, 1] == tr]
        stop = merged.get(int(tr), np.inf)
        g = g[(g[:, 0] < stop) & (g[:, 2] <= V_CAP)]
        if len(g) >= 4 and g[-1, 2] - g[0, 2] >= 100:
            r = rad(g[:, 2], vte)
            v.append(np.polyfit(g[:, 0], r, 1)[0] * 100)       # A/ps -> m/s
    out["v"] = np.array(v)
    return out


def main():
    data = {}
    for c in CELLS:
        for T in TAS:
            for r in (1, 2, 3):
                run = RUNS / f"anneal_{c}_T{T}_r{r}"
                if (run / FNAME).exists():
                    data[(c, T, r)] = per_run(run)
    missing = [f"{c} T{T} r{r}" for c in CELLS for T in TAS for r in (1, 2, 3) if (c, T, r) not in data]
    if missing:
        print("missing grain files:", ", ".join(missing))
    vcl = {}
    for line in (RES / "growth_summary.csv").read_text().splitlines():
        w = line.split(",")
        if w[0] in CELLS:
            vcl[(w[0], int(w[2]))] = float(w[6])
    rows = []
    for c in CELLS:
        for T in TAS:
            rs = [data[(c, T, r)] for r in (1, 2, 3) if (c, T, r) in data]
            if not rs:
                continue
            cmp = [x for x in rs if "sizes_cmp" in x]
            sizes = np.concatenate([x["sizes_cmp"] for x in cmp]) if cmp else np.array([])
            d = deq(sizes, np.mean([x["vte"] for x in cmp])) if cmp else np.array([])
            v = np.concatenate([x["v"] for x in rs])
            last = [x["F"][-1] for x in rs]
            fn, fd = np.sum([x["flux"] for x in rs], axis=0)
            vf = fn / fd * 100 if fd > 0 else np.nan                             # A/ps -> m/s
            vfr = [x["flux"][0] / x["flux"][1] * 100 for x in rs if x["flux"][1] > 0]
            def bud(v):
                b = [y for y in (budget(x["F"], x["E"], x["vte"], x["n_te"], v) for x in rs) if np.isfinite(y)]
                return np.mean(b) if b else np.nan
            cfrac = [(f[4] / max(f[4] + f[5] + f[6], 1), f[5] / max(f[4] + f[5] + f[6], 1),
                      f[7] / max(f[7] + f[8] + f[9], 1), f[8] / max(f[7] + f[8] + f[9], 1)) for f in last]
            rows.append(dict(cell=c, Ta=T, runs=len(rs), runs_at_xcmp=len(cmp),
                             grains_per_run=np.mean([len(x["sizes_cmp"]) for x in cmp]) if cmp else np.nan,
                             grains_sd=np.std([len(x["sizes_cmp"]) for x in cmp], ddof=1) if len(cmp) > 1 else np.nan,
                             d_mean_nm=d.mean() if len(d) else np.nan, d_median_nm=np.median(d) if len(d) else np.nan,
                             d_p90_nm=np.percentile(d, 90) if len(d) else np.nan, n_grains=len(d),
                             v_grain_median=np.median(v) if len(v) else np.nan, v_grain_n=len(v),
                             v_grain_iqr=(np.percentile(v, 75) - np.percentile(v, 25)) if len(v) > 3 else np.nan,
                             v_flux=vf, v_flux_sd=np.std(vfr, ddof=1) if len(vfr) > 1 else np.nan,
                             v_flux_runs=len(vfr), v_growth_cluster=vcl.get((c, T), np.nan),
                             budget_flux=bud(vf), budget_cluster=bud(vcl.get((c, T), np.nan)),
                             xfrac_end=np.mean([f[1] for f in last]),
                             C_interior=np.mean([q[0] for q in cfrac]), C_boundary=np.mean([q[1] for q in cfrac]),
                             GeSb_interior=np.mean([q[2] for q in cfrac]), GeSb_boundary=np.mean([q[3] for q in cfrac]),
                             _d=d, _v=v, _cmp=cmp, _rs=rs))
    keys = [k for k in rows[0] if not k.startswith("_")]
    with open(RES / "grains_summary.csv", "w") as f:
        f.write(f"# MODEL_ID {MODEL_ID}; grains: analysis/grains.py ({FNAME}); sizes at xfracGST >= {X_CMP}; "
                f"v_grain: per-grain radius slope before first merge, up to {V_CAP} Te; v_flux: grain growth / (n_Te x grain "
                f"area) up to xfracGST {X_FLUX}, pooled (v_flux_sd: sample std of the per-run values); v_growth_cluster: growth_summary v_mean (largest Q4 cluster, coalescence-"
                f"dominated); budget_*: X_pred/X_obs at xfracGST {X_FLUX} from observed grain births; C/GeSb site fractions at the "
                "last analysed frame\n" + ",".join(keys) + "\n")
        for r in rows:
            f.write(",".join(f"{r[k]:.4g}" if isinstance(r[k], float) else str(r[k]) for k in keys) + "\n")
    figs(rows, data)
    print(f"wrote {RES / 'grains_summary.csv'} and {pg.FIG}/grains_*.png/.pdf")


def figs(rows, data):
    R = {(r["cell"], r["Ta"]): r for r in rows}
    tas = [T for T in TAS if any((c, T) in R and R[(c, T)]["n_grains"] for c in CELLS)]
    # size distributions
    fig, axs = plt.subplots(1, len(tas), figsize=(2.6 * len(tas), 3.2), sharey=True)
    bins = np.arange(0, 8.01, 0.5)
    for ax, T in zip(np.atleast_1d(axs), tas):
        for c in CELLS:
            r = R.get((c, T))
            if r is None or not len(r["_d"]):
                continue
            h, _ = np.histogram(r["_d"], bins)
            ax.step(bins[:-1], h / max(r["runs_at_xcmp"], 1), where="post", color=pg.COLOR[c], lw=1.6,
                    label=f"{pg.LABEL[c]} ({len(r['_d'])} grains)")
            ax.axvline(np.median(r["_d"]), color=pg.COLOR[c], lw=1, ls=":")
        ax.set_title(f"{T} K")
        ax.set_xlabel("grain core d_eq (nm)")
        ax.legend(fontsize=6.5, loc="upper right")
    np.atleast_1d(axs)[0].set_ylabel("grains per cell")
    fig.text(0.01, -0.04, f"At the first frame with xfracGST >= {X_CMP}; dotted: median. Grain core = template-matched "
             "Te atoms (smaller than the grain with its disordered rim); cell ~9.6 nm.", fontsize=7, color=pg.INK2)
    fig.tight_layout()
    pg.save(fig, "grains_size_dist")
    # count and v
    for key, ylab, name, log in (("grains_per_run", f"grains per cell at xfracGST {X_CMP}", "grains_count", False),
                                 ("v_flux", "interface velocity (m/s)", "grains_v", True)):
        fig, ax = plt.subplots(figsize=(5.2, 3.8))
        for c in CELLS:
            pts = [(T, R[(c, T)][key]) for T in TAS if (c, T) in R and np.isfinite(R[(c, T)][key])]
            if not pts:
                continue
            for T in TAS:
                if (c, T) not in R:
                    continue
                if key == "grains_per_run":
                    ys = [len(x["sizes_cmp"]) for x in R[(c, T)]["_cmp"]]
                else:
                    ys = list(R[(c, T)]["_v"])
                ax.scatter(np.full(len(ys), T + pg.offset(c)), ys, s=8, color=pg.COLOR[c], alpha=0.35, lw=0)
            x, y = zip(*pts)
            ax.plot(np.array(x) + pg.offset(c), y, color=pg.COLOR[c], marker=pg.MARK[c], ms=7, mec=pg.SURF, mew=1.2,
                    label=pg.LABEL[c] + (" v_flux" if key == "v_flux" else ""))
            if key == "v_flux":
                cl = [(T, R[(c, T)]["v_growth_cluster"]) for T in TAS
                      if (c, T) in R and np.isfinite(R[(c, T)]["v_growth_cluster"])]
                if cl:
                    x, y = zip(*cl)
                    ax.plot(np.array(x) + pg.offset(c), y, color=pg.COLOR[c], ls="--", lw=1, marker=pg.MARK[c], ms=5,
                            mfc="none", label=f"{pg.LABEL[c]} largest cluster (not v)" if c == CELLS[-1] else None)
        if log:
            pg.plain_log(ax)
        ax.set_xticks(TAS)
        ax.set_xlabel("anneal temperature Ta (K)")
        ax.set_ylabel(ylab)
        ax.legend(fontsize=7)
        if key == "v_flux":
            fig.text(0.01, -0.06, "Line: v_flux (all tracked grains, merge-corrected). Dots: single grains before their "
                     "first merge.\nDashed, open: largest Q4 cluster at 10-25% (grows by coalescence; not an interface "
                     "velocity).", fontsize=7, color=pg.INK2)
        pg.save(fig, name)
    # carbon sites vs xfracGST (x1, x2p5)
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, c in zip(axs, ["x1", "x2p5"]):
        for T, col in zip([500, 550, 600, 650], pg.TA_COLORS):
            for r in (1, 2, 3):
                x = data.get((c, T, r))
                if x is None:
                    continue
                F = x["F"]
                nC = F[:, 4] + F[:, 5] + F[:, 6]
                nG = F[:, 7] + F[:, 8] + F[:, 9]
                ok = F[:, 1] > 0.2
                with np.errstate(invalid="ignore", divide="ignore"):
                    ratio = (F[ok, 4] / nC[ok]) / (F[ok, 7] / nG[ok])
                ax.plot(F[ok, 1], ratio, color=col, lw=1, alpha=0.8, label=f"{T} K" if r == 1 else None)
        ax.axhline(1, color=pg.AXIS, lw=1)
        ax.set_title(f"{pg.LABEL[c]}: C in grain interiors relative to Ge/Sb")
        ax.set_xlabel("xfracGST")
    axs[0].set_ylabel("(C interior fraction) / (Ge/Sb interior fraction)")
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    pg.save(fig, "grains_carbon")


if __name__ == "__main__":
    main()
