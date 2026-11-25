"""Summarize recrystallization runs (recryst/in.ramp and recryst/in.anneal outputs).

The crystalline fraction throughout is xfracGST, the fraction of Ge/Sb/Te atoms classed crystalline
(common/in.analysis): C is left out so that the crystalline ceiling does not fall with C content.
ramp runs (ramp.dat):
  x_a, x_peak  xfracGST at 300 K (first 10 ps) and the maximum of its 5 ps moving average over the ramp
  Tx_xfrac  T where the 5 ps moving average of xfracGST first exceeds x_a + 0.5 (x_peak - x_a), i.e. half its rise;
            NaN unless it rose by at least RISE_MIN (0.2), i.e. the sample crystallized
  Tx_H      T of the fastest enthalpy release, max of -dH/dt (10 ps moving average), excluding the first 50 K
  Tx_rho    T of the fastest density change, max of |drho/dt| (10 ps moving average), excluding the first 50 K.
            Sign-agnostic: in this project's DFT reference the glass is about as dense as the crystal (test 1k,
            tests/results/nequip_no_zbl/RESULTS.md), so crystallization need not raise the density as in experiment
  drho_x    signed density change across Tx_rho (g/cc): mean over 20 ps after minus 20 ps before
  xfrac_end xfracGST at the ramp's end (tmax, 900 K by default)
  Tx_H and Tx_rho always return a value; read them only when Tx_xfrac is finite (crystallization happened).
anneal runs (anneal.dat; hold start from hold_start.txt and xstop from anneal_done.txt, both written by in.anneal):
  x_a       baseline, mean xfracGST of the first 20 ps of the hold
  x_c       the crystalline end point X is normalized to, from (first that applies): --x-end (one fixed value for every
            run, so t_inc and t50 mean the same xfracGST in every run of a set); the run's own plateau (mean of the
            last 100 ps, if the 5 ps-averaged xfracGST rose by less than 0.02 over the last 200 ps); --x-crystal (the
            calibrated crystal reference at Ta for the run's composition); the run's xstop. x_c_from names the source.
            Without --x-end, runs of one set can mix sources (a grown crystal plateaus near 0.71 at 600 K, against
            0.95 for the perfect x0 crystal), which makes their t50 incomparable (recryst/README.md, Halt level).
  t_inc     first hold time where X = (xfracGST - x_a) / (x_c - x_a) (5 ps average) exceeds 0.05
  t50       first hold time where X exceeds 0.5
  n_JMAK, k_JMAK  descriptors of the curve shape only: the fit X = 1 - exp(-k (t - t_inc)^n) on 0.05 < X < 0.95.
            JMAK assumes many nuclei in an unbounded volume; a 13.8k-atom cell usually crystallizes from one nucleus
            that then meets its own periodic images, so n is not an Avrami mechanism exponent. Use t_nuc, v_growth
            and the nucleation rates (--clusters) for kinetics.
both (stress.dat, written by in.ramp and in.anneal):
  sdev_base, sdev_end, sdev_z  deviatoric (von Mises) stress in kbar, from the pressure tensor averaged over
            non-overlapping 10 ps blocks (averaging the components first keeps thermal noise from adding a positive
            bias). Mean over the first and the last 2-10 blocks (of the hold for anneals, of the run for ramps), and
            sdev_z = their difference over its standard error (Welch). A crystal grown against the isotropic barostat
            leaves a stress that persists to the end, so it shows up as a large sdev_z; recryst/README.md gives the
            criterion. NaN when the series has fewer than 4 blocks.
Only complete runs are analysed (ramp: ramp_done.txt, or snap_900K.data for ramps from before in.ramp had tmax;
anneal: anneal_done.txt); others are listed and skipped.
--clusters (anneal runs), under the criterion --q-rc/--q-thr/--q-nmin (required with --clusters: the calibrated
  criterion of the model, recryst/calib/<MODEL_ID>/calib_params.sh, Q_ARGS):
  per dumped frame, the largest crystalline Ge/Sb/Te cluster and the number of such clusters of at least
  --nucleus-min atoms -> <run>/clusters_q<rc>_<thr>_<nmin>.txt (one file per criterion, so runs under the default
  and the calibrated criterion can be compared). Per run:
  t_nuc     first hold time the largest cluster has >= --nucleated-size atoms (required with --clusters; take it
            from calibrate.py at Ta and the same criterion: the glass already holds crystal-like patches of up to a
            few hundred atoms, recryst/README.md, so a small size would mark every run nucleated at t = 0)
  v_growth  growth velocity (m/s): slope of the largest cluster's equivalent-sphere radius while it holds 10-25% of
            the Ge/Sb/Te atoms (early growth, well before grown crystals saturate; see kinetics())
  single_grain  fraction of the window's frames in which no second cluster has --nucleated-size atoms (1: one grain
            throughout; below 0.8, i.e. a second grain in more than 20% of the frames, the radius mixes grains and
            v_growth is an upper bound), NaN without a window. A fraction, not a flag, so that a
            short-lived second cluster in a frame or two does not disqualify a run
  Per replica group:
  survival  n_nucleated of n_runs, J_surv = n_nucleated / (total observed hold time x V), runs that never nucleated
            counting as censored at t_end (maximum likelihood for an exponential waiting time), relative error
            1/sqrt(n_nucleated)
  MFPT      mean-first-passage-time analysis of the largest-cluster trajectories (Wedekind et al., J. Chem. Phys.
            126, 134103, 2007): tau(n) = mean over replicas of the first hold time the largest cluster reaches n,
            fitted with tau(n) = tau_J/2 [1 + erf(Z sqrt(pi) (n - n*))] -> critical size n_star (atoms), tau_J (ps)
            and J = 1 / (tau_J V) (m^-3 s^-1). Only sizes above n_base, the largest cluster any replica has in the
            first 20 ps of its hold (the glass's own order), and that every replica reached are fitted (at least 5);
            n_star, tau_J and J are NaN when the fitted n* is not inside that range (the critical size is then
            hidden in the glass's own order, or was never reached).
  Both rates need many replicas: one waiting time per run, so the error is ~1/sqrt(runs) (recryst/README.md).
Replica groups (runio.group_of: the name without _r<rep>) with two or more runs also get mean +- sample std.
Times in ps; NaN when the event did not happen within the run.
Output starts with '#' header lines: MODEL_ID (environment, common/model.sh), the model file each run's log names, the
criterion and end point used. A run whose log names a model other than MODEL_ID (or one of its MODEL_ALIASES) is reported as a WARNING line.

Usage: python recryst_summary.py [--tscale S] [--x-crystal X | --x-end X]
       [--clusters --nucleated-size N [--nucleus-min N]]
       [--q-rc R --q-thr T --q-nmin N] <run_dir> ...       Directory names select the mode: ramp_* or anneal_*_T<Ta>_*.
"""
import argparse
import os
import re
from math import erf, pi, sqrt
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

from bondorder import cluster_sizes, crystal_bonds, read_dump
from runio import complete_runs, group_of, load_dat, mean_std


def smooth(y, n):
    """Centred n-point moving average; near the ends it averages the points that exist (no zero padding)."""
    if len(y) <= n:
        return y
    w = np.ones(n)
    return np.convolve(y, w, "same") / np.convolve(np.ones_like(y, dtype=float), w, "same")


RISE_MIN = 0.2       # a ramp crystallized if its smoothed xfracGST rose at least this far above the 300 K value


def first_cross(t, y, level):
    i = np.flatnonzero(y > level)
    return t[i[0]] if len(i) else np.nan


def stress(run, t_start):
    """Deviatoric-stress metrics (kbar) from stress.dat, from hold time t_start (ps); NaN if absent or too short."""
    keys = ("sdev_base", "sdev_end", "sdev_z")
    if not (run / "stress.dat").exists():
        return dict.fromkeys(keys, np.nan)
    d = load_dat(run / "stress.dat")
    m = d["time_ps"] >= t_start - 1e-9
    nb = m.sum() // 10                                            # 10 ps blocks (one row per ps)
    nw = max(2, min(10, nb // 4))                                 # blocks in each comparison window
    if nb < 2 * nw:
        return dict.fromkeys(keys, np.nan)
    c = {k: d[k][m][:10 * nb].reshape(nb, 10).mean(1) for k in ("pxx", "pyy", "pzz", "pxy", "pxz", "pyz")}
    vm = np.sqrt(0.5 * ((c["pxx"] - c["pyy"]) ** 2 + (c["pyy"] - c["pzz"]) ** 2 + (c["pzz"] - c["pxx"]) ** 2)
                 + 3 * (c["pxy"] ** 2 + c["pxz"] ** 2 + c["pyz"] ** 2)) / 1000.0
    b, e = vm[:nw], vm[-nw:]
    se = np.sqrt(b.var(ddof=1) / nw + e.var(ddof=1) / nw)
    return {"sdev_base": b.mean(), "sdev_end": e.mean(), "sdev_z": (e.mean() - b.mean()) / se if se > 0 else np.nan}


def ramp(run, tscale):
    d = load_dat(run / "ramp.dat")
    t, T, x = d["time_ps"], d["T_K"], d["xfracGST"]
    m = t >= 10 * tscale
    xa = x[~m].mean() if (~m).any() else x[0]
    xs = smooth(x[m], 5)
    xpk = xs.max()
    late = T[m] > 350
    dH = smooth(np.gradient(d["H_eV_per_atom"][m], t[m]), 10)
    rho, tm = d["rho_gcc"][m], t[m]
    drho = smooth(np.gradient(rho, tm), 10)
    k = np.flatnonzero(late)[np.argmax(np.abs(drho[late]))]
    after, before = (tm > tm[k]) & (tm <= tm[k] + 20 * tscale), (tm < tm[k]) & (tm >= tm[k] - 20 * tscale)
    return {"x_a": xa, "x_peak": xpk,
            "Tx_xfrac": first_cross(T[m], xs, xa + 0.5 * (xpk - xa)) if xpk - xa >= RISE_MIN else np.nan,
            "Tx_H": T[m][late][np.argmin(dH[late])],
            "Tx_rho": T[m][k],
            "drho_x": rho[after].mean() - rho[before].mean() if after.any() and before.any() else np.nan,
            "xfrac_end": x[-5:].mean(),
            **stress(run, 0.0)}


def hold_info(run):
    """hold_start.txt, written by in.anneal: {'hold_start_ps': t, 'q_rc': .., 'q_thr': .., 'q_nmin': ..}."""
    f = (run / "hold_start.txt").read_text().split()
    return {k: float(v) for k, v in zip(f[::2], f[1::2])}


def hold_start(run):
    """Hold start (ps) recorded by in.anneal in hold_start.txt."""
    return hold_info(run)["hold_start_ps"]


def xstop_of(run):
    """The xstop the run used, from anneal_done.txt ('... (stop at xfracGST > X or step N)')."""
    return float(re.search(r"stop at xfracGST > ([-\d.eE+]+)", (run / "anneal_done.txt").read_text())[1])


def anneal(run, tscale, x_crystal=None, x_end=None):
    d = load_dat(run / "anneal.dat")
    t0 = hold_start(run)
    m = d["time_ps"] >= t0
    t, x = d["time_ps"][m] - t0, d["xfracGST"][m]
    xa = x[t <= 20 * tscale].mean()
    xs = smooth(x, 5)
    late, last = t >= t.max() - 200 * tscale, t >= t.max() - 100 * tscale
    if x_end is not None:                             # one end point for every run of a set (--x-end)
        xc, src = x_end, "x-end"
    elif t.max() >= 300 * tscale and xs[late][-1] - xs[late][0] < 0.02 and xs[late].mean() > xa + 0.1:
        xc, src = x[last].mean(), "plateau"
    elif x_crystal is not None:
        xc, src = x_crystal, "x-crystal"
    else:
        xc, src = xstop_of(run), "xstop"
    t_inc = first_cross(t, xs, xa + 0.05 * (xc - xa))
    t50 = first_cross(t, xs, xa + 0.5 * (xc - xa))
    X = (x - xa) / (xc - xa)
    fit = (X > 0.05) & (X < 0.95) & (t > (t_inc if np.isfinite(t_inc) else np.inf))
    n = k = np.nan
    if fit.sum() >= 5:
        n, lnk = np.polyfit(np.log(t[fit] - t_inc), np.log(-np.log(1 - X[fit])), 1)
        k = np.exp(lnk)
    return {"x_a": xa, "x_c": xc, "x_c_from": src, "t_inc": t_inc, "t50": t50, "n_JMAK": n, "k_JMAK": k,
            "t_end": t.max(), "xfrac_end": x[-5:].mean(), **stress(run, t0)}


def clusters(run, rc, thr, nmin, nuc_min, reuse=True):
    """Per dumped frame of the hold (all traj.<first step>.lammpstrj.gz files; a step in two files, from a job
    killed after its last restart and its resumed successor, is taken from the later file): hold time, largest
    crystalline Ge/Sb/Te cluster, number of such clusters >= nuc_min atoms, xfracGST, second-largest cluster (for the
    single-grain flag of kinetics()). The per-atom bond count is the
    dumped c_ncb when the run's criterion (hold_start.txt) has the same q_rc and q_thr and reuse is set, else it is
    recomputed. Writes clusters_q<rc>_<thr>_<nmin>.txt; returns {'t', 'big', 'big2'} arrays, the mean cell volume
    (A^3) and the number of Ge/Sb/Te atoms."""
    d = load_dat(run / "anneal.dat")
    dt = d["time_ps"][-1] / d["step"][-1]
    info = hold_info(run)
    t0 = info["hold_start_ps"]
    same = reuse and (info.get("q_rc"), info.get("q_thr")) == (rc, thr)
    frames = {}
    for f in sorted(run.glob("traj.*.lammpstrj.gz"), key=lambda f: int(f.name.split(".")[1]), reverse=True):
        for step, L, c in read_dump(f):
            if step * dt < t0 - 1e-9 or step in frames:
                continue
            gst = c["type"] != 4
            ncb = c["c_ncb"] if same and "c_ncb" in c else crystal_bonds(c["pos"], L, rc, thr)
            mask = (ncb >= nmin) & gst
            s = cluster_sizes(mask, c["pos"], L, rc)
            frames[step] = (step * dt - t0, int(s[0]) if len(s) else 0, int((s >= nuc_min).sum()),
                            mask.sum() / gst.sum(), float(np.prod(L)), int(gst.sum()), int(s[1]) if len(s) > 1 else 0)
    rows = [frames[k] for k in sorted(frames)]
    lines = [f"hold_time_ps largest_cluster n_clusters_ge{nuc_min} xfracGST second_cluster"]
    lines += [f"{t:.2f} {big} {nn} {x:.4f} {b2}" for t, big, nn, x, _, _, b2 in rows]
    (run / f"clusters_q{rc:g}_{thr:g}_{nmin}.txt").write_text("\n".join(lines) + "\n")
    return {"t": np.array([r[0] for r in rows]), "big": np.array([r[1] for r in rows]),
            "big2": np.array([r[6] for r in rows]), "volume": float(np.mean([r[4] for r in rows])), "n_gst": rows[0][5]}


V_WINDOW = (0.10, 0.25)   # v_growth fit window, fraction of Ge/Sb/Te in the largest cluster (see kinetics())


def kinetics(cl, nucleated):
    """From one run's clusters() output: t_nuc, the first hold time the largest cluster has >= nucleated atoms;
    v_growth (m/s), the slope of its equivalent-sphere radius r = (3 N V / (4 pi N_GST))^(1/3) while it holds
    V_WINDOW (10-25%) of the Ge/Sb/Te atoms (least squares; NaN with fewer than 3 frames there); and single_grain,
    the fraction of that window's frames with no second cluster of `nucleated` atoms (1: one grain throughout),
    NaN without a window. Why 25%: grown crystals saturate (nequip_no_zbl: xfracGST ~0.65, ~0.61 of the Ge/Sb/Te
    atoms in the largest cluster), and the front slows throughout a run, so a window reaching toward saturation
    averages in the slow end: the earlier 10-60% window read 2-4x below 10-25% in the nequip_no_zbl grid
    (2026-11-24) and collapsed slow cells onto ~1 m/s. Geometry is no limit below 60% (a sphere counted exactly in a
    periodic cell keeps its slope within 0.5% up to 60%; tests/recryst_logic, check.py)."""
    t, big, n = cl["t"], cl["big"], cl["n_gst"]
    big2 = cl.get("big2", np.zeros_like(big))
    r = (3 * big * cl["volume"] / (4 * pi * n)) ** (1 / 3)
    g = (big >= V_WINDOW[0] * n) & (big <= V_WINDOW[1] * n)
    ok = g.sum() >= 3
    return {"t_nuc": first_cross(t, big, nucleated - 0.5),
            "v_growth": np.polyfit(t[g], r[g], 1)[0] * 100.0 if ok else np.nan,     # A/ps -> m/s
            "single_grain": float((big2[g] < nucleated).mean()) if ok else np.nan}


def survival_rate(t_nuc, t_end, volume):
    """Nucleation rate from first-nucleation times over replicas, a run that never nucleated counting as censored at
    its t_end: maximum-likelihood rate of an exponential waiting time, k = n_nucleated / total observed time, and
    J = k / V (m^-3 s^-1) with relative standard error 1/sqrt(n_nucleated)."""
    t_nuc, t_end = np.asarray(t_nuc, float), np.asarray(t_end, float)
    hit = np.isfinite(t_nuc)
    exposure = np.where(hit, t_nuc, t_end).sum()
    J = hit.sum() / (exposure * 1e-12 * volume * 1e-30) if hit.any() else np.nan
    return {"n_nucleated": int(hit.sum()), "n_runs": len(t_nuc), "J_surv_per_m3_s": J,
            "J_surv_rel_err": 1 / sqrt(hit.sum()) if hit.any() else np.nan}


def mfpt(tracks, volume, t_base=20.0):
    """MFPT fit over replicas: tracks = [(hold times, largest cluster sizes)]. Fits sizes n_base < n <= top, where
    n_base is the largest cluster any replica has at hold time <= t_base (ps) and top the largest size every replica
    reached. Returns n_base, n_star, tau_J (ps), J; the last three NaN with fewer than 5 sizes, a failed fit, or a
    fitted n* outside (n_base, top)."""
    n_base = max(int(big[t <= t_base].max(initial=0)) for t, big in tracks)
    nan = {"n_base": n_base, "n_star": np.nan, "tau_J_ps": np.nan, "J_per_m3_s": np.nan, "n_replicas": len(tracks)}
    top = min(int(np.maximum.accumulate(big).max()) for _, big in tracks)    # every replica reached this size
    if len(tracks) < 2 or top - n_base < 5:
        return nan
    sizes = np.arange(n_base + 1, top + 1)
    tau = np.array([np.mean([t[np.argmax(np.maximum.accumulate(big) >= n)] for t, big in tracks]) for n in sizes])
    model = np.vectorize(lambda n, tj, z, ns: 0.5 * tj * (1 + erf(z * sqrt(pi) * (n - ns))))
    try:
        (tj, z, ns), _ = curve_fit(model, sizes, tau, p0=(tau[-1], 0.05, sizes[len(sizes) // 2]), maxfev=20000)
    except RuntimeError:
        return nan
    if not n_base < ns < top:
        return nan
    return {"n_base": n_base, "n_star": ns, "tau_J_ps": tj, "J_per_m3_s": 1.0 / (tj * 1e-12 * volume * 1e-30),
            "n_replicas": len(tracks)}


def model_of(run):
    """Stem of the compiled model a run used (models/<MODEL_ID>[.G|.N|.K].nequip.pt2 -> MODEL_ID), from the substituted
    pair_coeff line of its first LAMMPS log; None if no log names one."""
    for log in sorted(run.glob("log.*")):
        m = re.search(r"^pair_coeff\s+\*\s+\*\s+(\S+\.pt2)\s", log.read_text(errors="replace"), re.M)
        if m:
            return Path(m[1]).name.split(".")[0]
    return None


def fmt(v):
    return v if isinstance(v, str) else f"{v:.4g}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--tscale", type=float, default=1.0)
    ap.add_argument("--x-crystal", type=float, help="crystal-reference xfracGST at Ta, for x_c (from calibrate.py)")
    ap.add_argument("--x-end", type=float, help="fixed x_c for every run (overrides plateau, --x-crystal, xstop), "
                    "so t_inc/t50 aim at the same xfracGST in every run; use a value every run reaches")
    ap.add_argument("--clusters", action="store_true")
    ap.add_argument("--nucleus-min", type=int, default=10, help="smallest cluster counted in n_clusters (atoms)")
    ap.add_argument("--nucleated-size", type=int,
                    help="largest-cluster size (atoms) that marks a run as nucleated, for t_nuc; required with "
                         "--clusters: the 'suggested --nucleated-size' that calibrate.py prints for Ta and this "
                         "criterion")
    ap.add_argument("--q-rc", type=float, help="criterion, required with --clusters (calib_params.sh Q_ARGS)")
    ap.add_argument("--q-thr", type=float)
    ap.add_argument("--q-nmin", type=int)
    a = ap.parse_args()
    if a.x_crystal is not None and a.x_end is not None:
        ap.error("--x-crystal and --x-end are alternatives: --x-end fixes x_c for every run, --x-crystal is a fallback")
    if a.clusters and a.nucleated_size is None:
        ap.error("--clusters needs --nucleated-size: the glass already has crystal-like clusters of up to a few "
                 "hundred atoms, so use the value recryst/calib/calibrate.py suggests for Ta and this criterion")
    if a.clusters and None in (a.q_rc, a.q_thr, a.q_nmin):
        ap.error("--clusters needs --q-rc, --q-thr and --q-nmin: the model's calibrated criterion "
                 "(recryst/calib/<MODEL_ID>/calib_params.sh, Q_ARGS)")
    ramps = [r for r in a.runs if r.name.startswith("ramp_")]
    anneals = [r for r in a.runs if re.match(r"anneal_.+_T\d+_", r.name)]
    for r in set(a.runs) - set(ramps) - set(anneals):
        print(f"{r.name}: not a ramp_* or anneal_*_T<Ta>_* directory, skipped")
    expected = os.environ.get("MODEL_ID")
    # ramps from before in.ramp took tmax end at 900 K and write no ramp_done.txt; their log has no tmax
    old = [r for r in ramps if not (r / "ramp_done.txt").exists() and (r / "snap_900K.data").exists()
           and (r / "log.ramp").exists() and "tmax" not in (r / "log.ramp").read_text(errors="replace")]
    done = (complete_runs([r for r in ramps if r not in old], "ramp_done.txt") + old
            + complete_runs(anneals, "anneal_done.txt"))
    used = {run.name: model_of(run) for run in done}
    print(f"# MODEL_ID {expected or 'unset'}; runs used: " + ", ".join(sorted({str(m) for m in used.values()})))
    print(f"# x_c: {f'--x-end {a.x_end:g}' if a.x_end is not None else 'per run (x_c_from)'}"
          + (f"; clusters: criterion q_rc {a.q_rc:g} q_thr {a.q_thr:g} q_nmin {a.q_nmin}, t_nuc at "
             f"{a.nucleated_size} atoms" if a.clusters else ""))
    accepted = {expected, *os.environ.get("MODEL_ALIASES", "").split()}  # earlier names of the same model (common/model.sh)
    for name, m in sorted(used.items()):
        if expected and m not in accepted:
            print(f"WARNING: {name} ran with model {m}, not MODEL_ID {expected}")
    groups, cls = {}, {}
    for run in done:
        name = run.name
        if run in ramps:
            res = ramp(run, a.tscale)
        else:
            res = anneal(run, a.tscale, a.x_crystal, a.x_end)
            if a.clusters:
                cl = clusters(run, a.q_rc, a.q_thr, a.q_nmin, a.nucleus_min)
                res = kinetics(cl, a.nucleated_size) | res
                cls.setdefault(group_of(name), []).append((cl, res))
        print(f"{name:28s} " + "  ".join(f"{k} {fmt(v)}" for k, v in res.items()))
        groups.setdefault(group_of(name), []).append(res)
    for g, rs in sorted(groups.items()):
        if len(rs) > 1:
            keys = [k for k, v in rs[0].items() if not isinstance(v, str)]
            mean, std = mean_std([[r[k] for k in keys] for r in rs])
            print(f"{g:28s} n={len(rs)} mean +- sample std: "
                  + "  ".join(f"{k} {m:.4g} +- {s:.2g}" for k, m, s in zip(keys, mean, std)))
    for g, runs in sorted(cls.items()):
        vol = np.mean([cl["volume"] for cl, _ in runs])
        r = survival_rate([res["t_nuc"] for _, res in runs], [res["t_end"] for _, res in runs], vol)
        r |= mfpt([(cl["t"], cl["big"]) for cl, _ in runs], vol, 20 * a.tscale)
        print(f"{g:28s} nucleation: " + "  ".join(f"{k} {v:.4g}" for k, v in r.items()))


if __name__ == "__main__":
    main()
