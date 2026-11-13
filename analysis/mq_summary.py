"""Summarize melt-quench runs (meltquench/in.meltquench outputs).

Per run directory (mq.dat, gate.txt, stages.txt, rdf_300K.dat, amorphous_300K.data):
  Tm_app    apparent melting T on the 10 K/ps heating ramp (window from stages.txt): T at max dH/dt (5 ps
            smoothing). This is superheated (no crystal-liquid interface), so it is an upper bound on the model
            Tm, not Tm itself.
  rho_l     liquid density at tmelt (1500 K by default; g/cc), mean over the tmelt hold (end of heating to quench start)
  rho_a     amorphous density at 300 K (g/cc), mean over the final 50 ps
  Tg        glass transition from a bilinear fit of V/atom(T) on the quench (times from stages.txt), breakpoint
            scanned over 400-1300 K; NaN if the quench has fewer than 20 points
  xfrac_a   crystalline fraction at 300 K. Not ~0: a 10 K/ps glass reads ~0.15, persistent crystal-like patches
            (recryst/README.md, "Crystal-like order already in the glass"); compare runs against that baseline
  CN_ij     partial coordination at 300 K: mean number of j atoms within the bond cutoff of an i atom (rdf_300K.dat)
  Z_i       total coordination of species i, summed over all partners (needs amorphous_300K.data for the counts)
  rmin_l, rmin_a  closest approach (A) of any atom pair in the liquid (rdf_<tmelt>K.dat, last 20 ps of the hold) and
            the glass (rdf_300K.dat): the lower edge of the first RDF bin (0.02 A) with g > 0, over all pairs. A
            WARNING names any pair below RMIN_WARN (1.0 A): a potential without short-range repulsion (no ZBL) can let
            atoms collapse in the hot liquid. The per-pair values are printed below the table. C-C bonds are
            1.2-1.5 A, so judge pairs, not one threshold; the RDF is time-averaged, so a brief contact can be missed
            (a crash or an energy drift in tests/dt is the other sign)
  hold_ps   the tmelt hold (gate.txt). A run that fails its MSD gate stops before the quench, so every complete run
            passed it; runs compared with each other must share hold_ps, and a WARNING is printed if they do not.
With --out DIR, also writes DIR/<group>_curves.dat: rho(T) and H(T) on the heating ramp and the quench in 10 K bins,
mean and sample std over the replicas of each (cell, qrate) group (the header lists the replicas; std is NaN for one).
Bond cutoffs: runio.BOND_RC (fixed per pair; the reasons are there). Override with --rc PAIR=R.
Prints one row per run, then mean +- sample std over replicas per (cell, qrate) with two or more replicas.

Usage: python mq_summary.py [--tscale S] [--rc GeTe=3.3 ...] [--out DIR] <run_dir> ...   (e.g. ../meltquench/runs/<MODEL_ID>/*)
Run dirs named <cell>_q<qrate>_r<rep> are grouped by runio.group_of; other names are reported individually.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runio import BOND_RC, SPECIES, complete_runs, group_of, load_dat, mean_std, parse_rc  # noqa: E402

PAIRS = [(i, j) for i in range(4) for j in range(i, 4)]          # order of compute rdf in common/in.rdf
RMIN_WARN = 1.0                                                   # A, closest-approach warning level (rmin_*)


def load_rdf(path):
    """Return r and a dict {(i, j): (g, cn_j_around_i)} from a single-block fix ave/time rdf file."""
    rows = [l.split() for l in Path(path).read_text().splitlines() if l and not l.startswith("#")]
    block = np.array([[float(v) for v in r] for r in rows if len(r) == 24])
    if len(block) == 0:
        raise ValueError(f"{path}: no RDF block")
    r = block[:, 1]
    out = {}
    for k, p in enumerate(PAIRS):
        out[p] = (block[:, 4 + 2 * k], block[:, 5 + 2 * k])
    return r, out


def closest(path):
    """{pair name: lower edge (A) of the first bin with g > 0} from an RDF file; NaN for a pair never seen."""
    r, rdf = load_rdf(path)
    lo = r - 0.5 * (r[1] - r[0])
    out = {}
    for (i, j), (g, _) in rdf.items():
        k = np.flatnonzero(g > 0)
        out[f"{SPECIES[i]}-{SPECIES[j]}"] = lo[k[0]] if len(k) else np.nan
    return out


def liquid_rdf(run):
    """The run's liquid RDF file, rdf_<tmelt>K.dat (any rdf_*K.dat that is not 300 K), or None."""
    f = [p for p in sorted(run.glob("rdf_*K.dat")) if p.name != "rdf_300K.dat"]
    return f[0] if f else None


def type_counts(path):
    """Number of atoms of each LAMMPS type (1-4) in a write_data file."""
    lines = Path(path).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("Atoms"))
    n = int(next(l.split()[0] for l in lines if l.endswith(" atoms")))
    types = [int(l.split()[1]) for l in lines[i + 2:i + 2 + n]]
    return np.bincount(types, minlength=5)[1:]


def bilinear_tg(T, V, lo=400.0, hi=1300.0):
    best = (np.inf, np.nan)
    for Tb in np.arange(lo, hi + 1, 5.0):
        a, b = T <= Tb, T >= Tb
        if a.sum() < 5 or b.sum() < 5:
            continue
        sse = sum(np.sum((V[m] - np.polyval(np.polyfit(T[m], V[m], 1), T[m])) ** 2) for m in (a, b))
        best = min(best, (sse, Tb))
    return best[1]


T_BINS = np.arange(295.0, 2015.0, 10.0)                        # 10 K bins centred on 300, 310, ..., 2000 K (tmelt)


def binned(T, y):
    """Mean of y in each T_BINS bin (NaN where empty)."""
    k = np.digitize(T, T_BINS) - 1
    ok = (k >= 0) & (k < len(T_BINS) - 1)
    s = np.bincount(k[ok], weights=y[ok], minlength=len(T_BINS) - 1)
    n = np.bincount(k[ok], minlength=len(T_BINS) - 1)
    with np.errstate(invalid="ignore"):
        return s / n


def write_curves(path, rs):
    centres = 0.5 * (T_BINS[1:] + T_BINS[:-1])
    lines = [f"# {len(rs)} replica(s): " + " ".join(r["run"] for r in rs),
             "stage T_K rho_mean rho_std H_mean H_std"]
    for s in ("heat", "quench"):
        rho = np.array([r["_curves"][s][0] for r in rs])
        H = np.array([r["_curves"][s][1] for r in rs])
        cols = (*mean_std(rho), *mean_std(H))
        for k, T in enumerate(centres):
            if np.isfinite(cols[0][k]):
                lines.append(f"{s} {T:.0f} " + " ".join(f"{c[k]:.6f}" for c in cols))
    Path(path).write_text("\n".join(lines) + "\n")


def summarize(run, tscale=1.0, rc=None):
    """Stage windows come from stages.txt, written by in.meltquench as each stage starts and ends: the RDF padding
    (common/in.rdf) makes stage lengths unpredictable from the schedule."""
    run = Path(run)
    rc = rc or {}
    d = load_dat(run / "mq.dat")
    t, T, H = d["time_ps"], d["T_K"], d["H_eV_per_atom"]
    w = (run / "gate.txt").read_text().split()
    gate = dict(zip(w[::2], w[1::2]))
    stages = dict(l.split() for l in (run / "stages.txt").read_text().splitlines() if l.strip())
    t_heat0, t_heat1 = float(stages["heat_start_ps"]), float(stages["heat_end_ps"])
    t_q0, t_q1 = float(stages["quench_start_ps"]), float(stages["quench_end_ps"])
    t_end = t.max()
    res = {"run": run.name, "hold_ps": float(gate["hold_ps"])}
    heat = (t >= t_heat0) & (t <= t_heat1)
    dH = np.convolve(np.gradient(H[heat], t[heat]), np.ones(5) / 5, "same")
    res["Tm_app"] = T[heat][2:-2][np.argmax(dH[2:-2])]
    res["rho_l"] = d["rho_gcc"][(t > t_heat1) & (t <= t_q0)].mean()
    final = t >= t_end - 50 * tscale
    res["rho_a"] = d["rho_gcc"][final].mean()
    res["xfrac_a"] = d["xfrac"][final].mean()
    quench = (t > t_q0) & (t <= t_q1)
    res["Tg"] = bilinear_tg(T[quench], d["V_A3_per_atom"][quench]) if quench.sum() > 20 else np.nan
    res["_curves"] = {s: [binned(T[m], d[c][m]) for c in ("rho_gcc", "H_eV_per_atom")]
                      for s, m in (("heat", heat), ("quench", quench))}
    res["_rmin"] = {}
    for tag, f in (("l", liquid_rdf(run)), ("a", run / "rdf_300K.dat")):
        if f is not None and f.exists():
            res["_rmin"][tag] = closest(f)
            res[f"rmin_{tag}"] = np.nanmin(list(res["_rmin"][tag].values()))
    if (run / "rdf_300K.dat").exists():
        r, rdf = load_rdf(run / "rdf_300K.dat")
        n = type_counts(run / "amorphous_300K.data") if (run / "amorphous_300K.data").exists() else None
        z = np.zeros(4)
        for (i, j), (g, cn) in rdf.items():
            if n is not None and (n[i] == 0 or n[j] == 0):
                continue
            key = frozenset([SPECIES[i], SPECIES[j]])
            # cn = number of type-j atoms around a type-i atom, counted through the upper edge of each bin
            c = np.interp(rc.get(key, BOND_RC[key]), r + 0.5 * (r[1] - r[0]), cn)
            res[f"CN_{SPECIES[i]}{SPECIES[j]}"] = c
            if n is not None:
                z[i] += c
                if i != j:
                    z[j] += c * n[i] / n[j]                       # i atoms around a j atom
        if n is not None:
            for i in range(4):
                if n[i]:
                    res[f"Z_{SPECIES[i]}"] = z[i]
    return res


def main(runs, tscale, rc, out=None):
    runs = complete_runs(runs)
    if not runs:
        raise SystemExit("no complete runs")
    rows = [summarize(r, tscale, rc) for r in runs]
    keys = ["Tm_app", "rho_l", "rho_a", "Tg", "xfrac_a", "rmin_l", "rmin_a", "hold_ps"]
    keys += sorted({k for r in rows for k in r if k.startswith("CN_")})
    keys += [f"Z_{s}" for s in SPECIES if any(f"Z_{s}" in r for r in rows)]
    print("run".ljust(18) + "".join(k.rjust(9) for k in keys))
    for r in rows:
        print(r["run"].ljust(18) + "".join(f"{r.get(k, np.nan):9.3f}" for k in keys))
    names = [f"{SPECIES[i]}-{SPECIES[j]}" for i, j in PAIRS]
    print("\nclosest approach per pair (A), liquid / glass; nan: pair absent")
    print("run".ljust(18) + "".join(n.rjust(12) for n in names))
    for r in rows:
        mm = r["_rmin"]
        print(r["run"].ljust(18) + "".join(f"{mm.get('l', {}).get(n, np.nan):6.2f}/{mm.get('a', {}).get(n, np.nan):<5.2f}"
                                           .rjust(12) for n in names))
        for tag, lab in (("l", "liquid"), ("a", "glass")):
            for n, v in mm.get(tag, {}).items():
                if v < RMIN_WARN:
                    print(f"WARNING: {r['run']} {lab}: {n} pairs as close as {v:.2f} A (< {RMIN_WARN} A): close contact")
    groups = {}
    for r in rows:
        groups.setdefault(group_of(r["run"]), []).append(r)
    holds = sorted({r["hold_ps"] for r in rows})
    if len(holds) > 1:
        print(f"WARNING: the runs have different tmelt holds ({', '.join(f'{h:g}' for h in holds)} ps), so their "
              "melts had different thermal histories")
    if out:
        Path(out).mkdir(parents=True, exist_ok=True)
        for g, rs in groups.items():
            write_curves(Path(out) / f"{g}_curves.dat", rs)
    groups = {g: rs for g, rs in groups.items() if len(rs) > 1}
    if groups:
        print("\nmean +- sample std (ddof = 1) over replicas")
        for g, rs in sorted(groups.items()):
            m, s = mean_std([[x.get(k, np.nan) for k in keys] for x in rs])
            print(f"{g:14s}n={len(rs)} " + "".join(f"{v:9.3f}" for v in m) + "\n" + " " * 18
                  + "".join(f"{v:9.3f}" for v in s))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--tscale", type=float, default=1.0,
                    help="tscale the runs used, for the final 50 ps window (tests only)")
    ap.add_argument("--rc", action="append", default=[], metavar="PAIR=R",
                    help="bond cutoff override in A, repeatable, e.g. --rc GeTe=3.3 --rc CC=1.8")
    ap.add_argument("--out", help="directory for the per-group rho(T), H(T) curves")
    a = ap.parse_args()
    main(a.runs, a.tscale, parse_rc(a.rc), a.out)
