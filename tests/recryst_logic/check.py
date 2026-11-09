"""Verdict for the recrystallization logic test (submit.sh runs it at the end). Expected values follow from the inputs
at tscale 0.1 and dt 1 fs: the anneal hold starts at step 4000 (10 ps at 300 K + 30 ps to 600 K, x 0.1) and ends at
24000 (max_ns 0.2); fix halt checks every 1000 steps; restarts every 5000 steps.
  ramp_x0_h10_r1     exit 0; snap_350K ... snap_900K (12 files); ramp.dat follows the programmed schedule (300 K for
                     10 ps, then +10 K/ps): mean deviation < 15 K, scatter < 50 K (a single instantaneous T of 461
                     atoms fluctuates by ~35 K, so one sample is not a test); stress.dat has a row for every ramp.dat
                     step
  anneal_x0_T600_r1  both jobs exit 0; anneal_done.txt at step 24000; anneal.dat rows every 1000 steps from 0 to
                     24000 with no gap across the resume; stress.dat rows every 1000 steps from 4000 to 24000;
                     restart files at 5000, 10000, 15000, 20000; trajectory frames every 2000 steps (2 ps) with
                     image flags: the two jobs' files overlap at 10000-14000 and agree there to 0.01 A in unwrapped
                     position (x + ix Lx), and unwrapped atoms move < 5 A between consecutive frames across the
                     resume (a lost or reset image flag would jump by a box length, ~24 A)
  halt_x0            (baro aniso) exit 0; stopped by fix halt at its first check, step 5000, with xfracGST > 0;
                     the barostat in log.anneal is aniso
  continuation       sbatch --test-only accepted the resource flags of submit_anneal.sh's continuation
  calib (C present)  both in.calib runs and calibrate.py exit 0; on every dumped frame that is also a .dat row, the
                     LAMMPS xfracGST equals a recount over Ge/Sb/Te atoms and xfrac a recount over all atoms (from
                     the dumped positions, analysis/bondorder.py; within 2 atoms, for the dump's 6-digit rounding),
                     and the two differ on at least one reference (the denominator matters); calibrate.py reports
                     xfracGST and a suggested XSTOP at 600 K
  analysis           recryst_summary on the outputs: ramp() gives finite Tx_H and stress metrics; anneal() reads
                     hold_start.txt (4 ps, criterion 3.6/0.5/4) and xstop from anneal_done.txt (0.8; halt_x0: 0),
                     takes x_c from xstop (no plateau in 20 ps), gives t_end 20 ps, and NaN stress metrics (20 ps < 4
                     blocks of 10 ps); clusters() writes clusters_q3.6_0.5_4.txt with every hold frame once, in step
                     order, across the two jobs' dump files, and gives the same clusters from the dumped c_ncb as
                     from a recount; main() skips an incomplete anneal (a copy without anneal_done.txt) by name
  known answers      load_dat keeps the last row of a repeated step; ramp() on a synthetic logistic xfracGST
                     centred at 650 K gives Tx_xfrac within 3 K of 650 for both a 0.8 and a 0.6 ceiling (the
                     half-rise definition does not move with the ceiling) and NaN when xfracGST does not rise;
                     kinetics() on a sphere growing at 2 A/ps (200 m/s) gives v_growth within 2% and t_nuc within one
                     frame of the analytic time; survival_rate() gives J = 2 / (1400 ps x 1e5 A^3) for nucleation at
                     100 and 300 ps and one run censored at 1000 ps; smooth() keeps a constant constant at the ends;
                     stress() on 300 ps of production-like noise
                     (0.46 kbar per instantaneous component, the 461-atom test cell's level scaled to 13.8k atoms):
                     |z| < 5 on pure noise; z > 10 and sdev_end within 15% of 2 kbar for a 2 kbar deviatoric step;
                     group_of maps ramp_/anneal_ names; the MFPT fit recovers n* = 40 and tau_J = 500 ps from
                     synthetic first-passage curves (3 replicas)
Writes RESULT.txt (one PASS/FAIL line per check, then the verdict) and exits 1 on any failure; a crash in the checker
is reported as a FAIL.
"""
import shutil
import subprocess
import sys
import tempfile
from math import erf, pi, sqrt
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "analysis"))
import recryst_summary as rs  # noqa: E402
from bondorder import crystal_bonds, read_dump  # noqa: E402
from runio import group_of, load_dat  # noqa: E402

(HERE / "RESULT.txt").unlink(missing_ok=True)
lines, ok = [], True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    lines.append(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def status(path):
    return path.read_text().strip() if path.exists() else "missing"


def done_step(run):
    f = run / "anneal_done.txt"
    return int(f.read_text().split()[1]) if f.exists() else None


def run_checks():
    r = HERE / "ramp_x0_h10_r1"
    check("ramp: exit status 0", status(r / "exit_status.txt") == "0", status(r / "exit_status.txt"))
    snaps = sorted(int(f.name[5:-6]) for f in r.glob("snap_*K.data"))
    check("ramp: snap_350K ... snap_900K", snaps == list(range(350, 901, 50)), f"{len(snaps)} files")
    d = load_dat(r / "ramp.dat")
    dev = d["T_K"] - np.where(d["time_ps"] < 10, 300.0, 300.0 + 10.0 * (d["time_ps"] - 10))
    check("ramp: T follows the programmed schedule (mean deviation < 15 K, scatter < 50 K)",
          abs(dev.mean()) < 15 and dev.std() < 50, f"mean {dev.mean():+.1f} K, scatter {dev.std():.1f} K")
    s = load_dat(r / "stress.dat")
    check("ramp: stress.dat has a row for every ramp.dat step", np.array_equal(s["step"], d["step"]),
          f"{len(s['step'])} vs {len(d['step'])} rows")

    a = HERE / "anneal_x0_T600_r1"
    st = (status(a / "exit_status.1.txt"), status(a / "exit_status.2.txt"))
    check("anneal: fresh and resumed jobs exit 0", st == ("0", "0"), " ".join(st))
    check("anneal: anneal_done.txt at step 24000", done_step(a) == 24000, str(done_step(a)))
    d = load_dat(a / "anneal.dat")
    check("anneal: anneal.dat every 1000 steps, 0-24000, no gap across the resume",
          np.array_equal(d["step"], np.arange(0, 24001, 1000)), f"{len(d['step'])} rows")
    s = load_dat(a / "stress.dat")
    check("anneal: stress.dat every 1000 steps, 4000-24000, across the resume",
          np.array_equal(s["step"], np.arange(4000, 24001, 1000)), f"{len(s['step'])} rows")
    rst = sorted(int(f.name.split(".")[1]) for f in a.glob("anneal.*.restart"))
    check("anneal: restart files every 5000 steps", rst == [5000, 10000, 15000, 20000], str(rst))
    unw = {}
    for f in sorted(a.glob("traj.*.lammpstrj.gz"), key=lambda f: int(f.name.split(".")[1])):
        for step, L, fr in read_dump(f):
            u = fr["pos"] + np.stack([fr["ix"], fr["iy"], fr["iz"]], 1) * L
            unw.setdefault(step, []).append(u)
    steps = sorted(unw)
    overlap = [k for k in steps if len(unw[k]) == 2]
    same = max((np.abs(unw[k][0] - unw[k][1]).max() for k in overlap), default=np.inf)
    jump = max(np.linalg.norm(unw[b][-1] - unw[c][-1], axis=1).max() for c, b in zip(steps, steps[1:]))
    check("anneal: frames every 2 ps with image flags, continuous across the resume",
          steps == list(range(4000, 24001, 2000)) and overlap == [10000, 12000, 14000] and same < 0.01 and jump < 5,
          f"{len(steps)} steps, overlap {overlap}, overlap difference {same:.3g} A, largest step {jump:.2f} A")

    h = HERE / "halt_x0"
    check("halt: exit status 0", status(h / "exit_status.txt") == "0", status(h / "exit_status.txt"))
    x = float((h / "anneal_done.txt").read_text().split()[5]) if (h / "anneal_done.txt").exists() else -1
    check("halt: fix halt stopped the hold at its first check (step 5000), xfracGST > 0",
          done_step(h) == 5000 and x > 0, f"step {done_step(h)}, xfracGST {x:.3f}")
    log = (h / "log.anneal").read_text() if (h / "log.anneal").exists() else ""
    check("halt: the hold ran with the anisotropic barostat", "aniso 0.0 0.0" in log and " iso 0.0 0.0" not in log)

    c = (HERE / "continuation_test.txt").read_text() if (HERE / "continuation_test.txt").exists() else ""
    check("continuation: sbatch --test-only accepts the inherited resource flags",
          c.strip().endswith("exit 0") and "to start" in c, c.strip().replace("\n", " | ")[:120])

    cd = HERE / "calib"
    st = [status(cd / f"exit_status.{k}.txt") for k in ("amor", "crys", "calibrate")]
    check("calib: in.calib (x10 glass, x5 rocksalt) and calibrate.py exit 0", st == ["0"] * 3, " ".join(st))
    worst, differ = 0, False
    for tag in ("amor_x10_300K", "crys_x5_600K"):
        d = load_dat(cd / f"{tag}.dat")
        rows = dict(zip(d["step"].astype(int), zip(d["xfrac"], d["xfracGST"])))
        for step, L, fr in read_dump(cd / f"{tag}.lammpstrj.gz"):
            if step not in rows:
                continue
            xtal, gst = crystal_bonds(fr["pos"], L, 3.6, 0.5) >= 4, fr["type"] != 4
            worst = max(worst, abs(rows[step][0] - xtal.mean()) * len(gst),
                        abs(rows[step][1] - xtal[gst].mean()) * gst.sum())
            differ |= abs(rows[step][0] - rows[step][1]) * len(gst) > 2.5
    check("calib: LAMMPS xfracGST = recount over Ge/Sb/Te, xfrac = recount over all (within 2 atoms); they differ",
          worst <= 2 and differ, f"largest difference {worst:.1f} atoms")
    out = (cd / "calibrate.out").read_text() if (cd / "calibrate.out").exists() else ""
    check("calib: calibrate.py reports xfracGST and a suggested XSTOP at 600 K",
          "xfracGST" in out and "suggested XSTOP at 600 K" in out, out.strip().splitlines()[0][:100] if out else "")

    rr = rs.ramp(r, 1.0)
    check("analysis: ramp() gives finite Tx_H and stress metrics",
          all(np.isfinite(rr[k]) for k in ("Tx_H", "sdev_base", "sdev_end", "sdev_z")),
          f"Tx_H {rr['Tx_H']:.0f} K, sdev {rr['sdev_base']:.2f} -> {rr['sdev_end']:.2f} kbar, z {rr['sdev_z']:.1f}")
    check("analysis: hold_start.txt = 4 ps with criterion 3.6/0.5/4; xstop read back (0.8 default, 0 for halt_x0)",
          rs.hold_info(a) == {"hold_start_ps": 4.0, "q_rc": 3.6, "q_thr": 0.5, "q_nmin": 4.0}
          and rs.xstop_of(a) == 0.8 and rs.xstop_of(h) == 0.0, f"{rs.hold_info(a)}, {rs.xstop_of(a)}, {rs.xstop_of(h)}")
    ra = rs.anneal(a, 0.1)
    check("analysis: anneal() gives t_end 20 ps, x_c from xstop, NaN stress metrics for a 20 ps hold",
          abs(ra["t_end"] - 20) < 1e-6 and ra["x_c_from"] == "xstop" and ra["x_c"] == 0.8
          and np.isnan(ra["sdev_z"]), f"t_end {ra['t_end']:g}, x_c {ra['x_c']} from {ra['x_c_from']}")
    steps = sorted({s for f in a.glob("traj.*.lammpstrj.gz") for s, _, _ in read_dump(f) if s >= 4000})
    cl = rs.clusters(a, 3.6, 0.5, 4, 10)
    rows = (a / "clusters_q3.6_0.5_4.txt").read_text().splitlines()
    check("analysis: clusters_q3.6_0.5_4.txt has every dumped hold step once, in order, across both jobs' files",
          len(rows) - 1 == len(cl["t"]) == len(steps) >= 2 and np.all(np.diff(cl["t"]) > 0) and cl["volume"] > 0,
          f"{len(cl['t'])} frames, {len(steps)} distinct dumped hold steps")
    cl2 = rs.clusters(a, 3.6, 0.5, 4, 10, reuse=False)
    check("analysis: clusters from the dumped c_ncb equal clusters from a recount",
          np.array_equal(cl["big"], cl2["big"]), f"largest {cl['big'].tolist()} vs {cl2['big'].tolist()}")
    with tempfile.TemporaryDirectory() as tmp:                    # an anneal that has not finished
        inc = Path(tmp) / "anneal_x0_T600_r9"
        inc.mkdir()
        for f in ("anneal.dat", "hold_start.txt", "stress.dat"):
            shutil.copy(a / f, inc / f)
        out = subprocess.run([sys.executable, str(HERE.parents[1] / "analysis/recryst_summary.py"), "--tscale", "0.1",
                              str(a), str(inc)], capture_output=True, text=True).stdout
    check("analysis: main() skips an incomplete anneal and still reports the complete one",
          "anneal_x0_T600_r9: incomplete (no anneal_done.txt), skipped" in out
          and any(l.startswith("anneal_x0_T600_r1 ") for l in out.splitlines()), out.strip().replace("\n", " | ")[:120])

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "x.dat"
        f.write_text("step a\n0 1\n1 2\n2 3\n1 9\n2 8\n3 4\n")             # steps 1-2 rewritten by a resume
        d = load_dat(f)
    check("known answer: load_dat keeps the last row of a repeated step",
          d["step"].tolist() == [0, 1, 2, 3] and d["a"].tolist() == [1, 9, 8, 4], str(d["a"].tolist()))

    tx = {}
    with tempfile.TemporaryDirectory() as tmp:
        for case, top in (("0.8", 0.8), ("0.6", 0.6), ("flat", 0.08)):
            d = Path(tmp) / case
            d.mkdir()
            t = np.arange(0.0, 611.0)
            T = np.where(t < 10, 300.0, 300.0 + (t - 10))
            x = 0.08 + (top - 0.08) / (1 + np.exp(-(T - 650) / 10))
            rows = ["step time_ps T_K H_eV_per_atom rho_gcc xfrac xfracGST"]
            rows += [f"{int(k * 1000)} {k} {TT} {-3 - 1e-4 * TT - 0.05 * xx} {6.2 - 0.1 * xx} {xx} {xx}"
                     for k, TT, xx in zip(t, T, x)]
            (d / "ramp.dat").write_text("\n".join(rows) + "\n")
            tx[case] = rs.ramp(d, 1.0)["Tx_xfrac"]
    check("known answer: ramp() Tx_xfrac at the half-rise, 650 K for a 0.8 and a 0.6 ceiling, NaN without a rise",
          abs(tx["0.8"] - 650) < 3 and abs(tx["0.6"] - 650) < 3 and np.isnan(tx["flat"]),
          f"{tx['0.8']:.0f} K, {tx['0.6']:.0f} K, {tx['flat']}")

    t = np.arange(0.0, 20.0, 0.5)                   # a sphere, r = 2 A/ps x t; 10000 Ge/Sb/Te atoms, 30 A^3 each
    big = np.floor(4 * pi / 3 * (2.0 * t) ** 3 / 30.0).astype(int).clip(max=10000)
    kin = rs.kinetics({"t": t, "big": big, "volume": 3e5, "n_gst": 10000}, 50)
    t50 = (3 * 50 * 30 / (4 * pi)) ** (1 / 3) / 2.0
    check("known answer: kinetics() v_growth 200 m/s within 2%, t_nuc within one frame of the analytic time",
          abs(kin["v_growth"] / 200 - 1) < 0.02 and 0 <= kin["t_nuc"] - t50 <= 0.5,
          f"v {kin['v_growth']:.1f} m/s, t_nuc {kin['t_nuc']} ps (analytic {t50:.2f})")
    sr = rs.survival_rate([100.0, 300.0, np.nan], [1000.0, 1000.0, 1000.0], 1e5)
    J = 2 / (1400e-12 * 1e5 * 1e-30)
    check("known answer: survival_rate() J = 2 / (1400 ps x 1e5 A^3), 2 of 3 nucleated",
          abs(sr["J_surv_per_m3_s"] / J - 1) < 1e-9 and sr["n_nucleated"] == 2, f"{sr['J_surv_per_m3_s']:.4g}")

    check("known answer: smooth() keeps a constant constant at the ends",
          np.allclose(rs.smooth(np.ones(40), 10), 1.0))
    rng = np.random.default_rng(1)
    with tempfile.TemporaryDirectory() as tmp:
        z = {}
        for case, step in (("noise", 0.0), ("step", 2000.0)):
            d = Path(tmp) / case
            d.mkdir()
            n = 300
            noise = rng.normal(0.0, 460.0, (n, 6))                   # bar
            noise[150:, 0] += step                                   # pxx, from 150 ps on
            rows = ["step time_ps pxx pyy pzz pxy pxz pyz"]
            rows += [f"{k * 1000} {k} " + " ".join(f"{v:.3f}" for v in noise[k]) for k in range(n)]
            (d / "stress.dat").write_text("\n".join(rows) + "\n")
            z[case] = rs.stress(d, 0.0)
    check("known answer: stress() |z| < 5 on pure noise, z > 10 and sdev_end ~ 2 kbar for a 2 kbar step",
          abs(z["noise"]["sdev_z"]) < 5 and z["step"]["sdev_z"] > 10 and abs(z["step"]["sdev_end"] / 2.0 - 1) < 0.15,
          f"noise z {z['noise']['sdev_z']:.1f}; step z {z['step']['sdev_z']:.1f}, end {z['step']['sdev_end']:.2f} kbar")

    names = {"ramp_x5_h1_r3": "ramp_x5_h1", "anneal_x0_T600_r2": "anneal_x0_T600", "x0_q10_r1": "x0_q10"}
    check("analysis: group_of strips the replica suffix", all(group_of(k) == v for k, v in names.items()))

    # MFPT known answer: largest-cluster tracks whose first passage of n is exactly tau(n)
    n_star, tau_j, z = 40.0, 500.0, 0.05
    times = np.arange(0.0, 1500.0, 1.0)
    tau = lambda n: 0.5 * tau_j * (1 + erf(z * sqrt(pi) * (n - n_star)))
    sizes = np.arange(1, 121)
    tp = np.array([tau(n) for n in sizes])
    track = np.array([sizes[tp <= tt].max(initial=0) for tt in times])
    res = rs.mfpt([(times, track)] * 3, 1e5)
    check("analysis: MFPT fit recovers n* = 40 and tau_J = 500 ps",
          abs(res["n_star"] - n_star) < 1 and abs(res["tau_J_ps"] / tau_j - 1) < 0.02,
          f"n* {res['n_star']:.2f}, tau_J {res['tau_J_ps']:.1f} ps")


try:
    run_checks()
except Exception as e:                                            # a crash in the checker is a failed test, reported
    check("checker ran to completion", False, f"{type(e).__name__}: {e}")
lines.append(f"VERDICT: {'PASS' if ok else 'FAIL'}")
(HERE / "RESULT.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0 if ok else 1)
