"""Verdict for the melt-quench logic test (submit.sh runs it at the end). Pass criteria, per run (x0, x10):
  - every output file exists: mq.dat, log.mq, traj, gate.txt, stages.txt, both RDF files, liquid_1500K.data,
    amorphous_300K.data, mq.restart.a/b; 12 snap_<T>K.data files; one 300-row block in each RDF file
  - stages.txt has heat_start, heat_end, quench_start, quench_end in increasing order, and mq.dat's T at each is
    near the schedule (300, 1500, 1500, 300 K; wide tolerances, as the thermostat lags the 100 K/ps test ramps)
  - LAMMPS exited 0; gate.txt reads hold_ps 100, passed 1; no gate ERROR in log.mq
  - mq_summary.summarize and mq_structure.analyze run on the outputs with finite results (x10: C motifs and
    clusters found), so an analysis that breaks on real outputs fails the test
  - their two independent estimates of each species' Z (RDF running coordination; bond counting on the trajectory)
    agree within 0.15. The trajectory side has only 2 frames of a ~500-atom cell here, hence the loose bound;
    measured differences are within 0.04 (job 12262741)
x0_gatefail (gate_A2 1e9, a gate that cannot be met): LAMMPS exited non-zero; gate.txt reads passed 0; log.mq has
the gate ERROR; the quench never started (no quench_start_ps, no amorphous_300K.data); runio.complete_runs skips
the run and names the failed gate.
Writes RESULT.txt (one PASS/FAIL line per check, then the verdict) and exits 1 on any failure.
Run with the analysis environment: ../../env/cgst-ana/bin/python check.py
"""
import contextlib
import io
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "analysis"))
from mq_structure import analyze, cutoff_matrix  # noqa: E402
from mq_summary import summarize  # noqa: E402
from runio import complete_runs, load_dat  # noqa: E402

TSCALE = 0.1
(HERE / "RESULT.txt").unlink(missing_ok=True)                      # never leave an earlier verdict in place
lines, ok = [], True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    lines.append(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def kv(path):
    w = path.read_text().split()
    return dict(zip(w[::2], w[1::2]))


def T_at(d, t):
    return d["T_K"][np.argmin(abs(d["time_ps"] - t))]


def gate_error(r):
    return any(l.startswith("ERROR: MSD gate not met") for l in (r / "log.mq").read_text().splitlines())


def run_checks():
    for run in ("x0", "x10"):
        r = HERE / run
        status = (r / "exit_status.txt").read_text().strip() if (r / "exit_status.txt").exists() else "missing"
        check(f"{run}: LAMMPS exit status 0", status == "0", status)
        need = ["mq.dat", "log.mq", "traj.lammpstrj.gz", "gate.txt", "stages.txt", "rdf_1500K.dat", "rdf_300K.dat",
                "liquid_1500K.data", "amorphous_300K.data", "mq.restart.a", "mq.restart.b"]
        missing = [f for f in need if not (r / f).exists()]
        check(f"{run}: output files", not missing, "missing " + " ".join(missing) if missing else "")
        if missing:
            continue
        snaps = sorted(r.glob("snap_*K.data"))
        check(f"{run}: 12 quench snapshots", len(snaps) == 12, f"{len(snaps)}")
        for f in ("rdf_1500K.dat", "rdf_300K.dat"):
            nblk = sum(1 for l in (r / f).read_text().splitlines() if l.split()[1:] == ["300"] and len(l.split()) == 2)
            check(f"{run}: {f} has one 300-row block", nblk == 1, f"{nblk} blocks")
        st = {k: float(v) for k, v in kv(r / "stages.txt").items()}
        keys = ["heat_start_ps", "heat_end_ps", "quench_start_ps", "quench_end_ps"]
        check(f"{run}: stages.txt keys in order", list(st) == keys and np.all(np.diff([st[k] for k in keys]) > 0),
              " ".join(f"{k}={v:g}" for k, v in st.items()))
        d = load_dat(r / "mq.dat")
        # targets: 300 K before heating, 1500 K at heating end and quench start, 300 K at quench end; the Nose-Hoover
        # thermostat lags a 100 K/ps test ramp, hence the wide tolerances
        for k, target, tol in (("heat_start_ps", 300, 60), ("heat_end_ps", 1500, 200), ("quench_start_ps", 1500, 200),
                               ("quench_end_ps", 300, 100)):
            if k not in st:                                           # already failed the keys check
                continue
            T = T_at(d, st[k])
            check(f"{run}: T at {k} near {target} K", abs(T - target) < tol, f"{T:.0f} K")
        g = kv(r / "gate.txt")
        check(f"{run}: gate.txt hold_ps 100, passed 1, no gate ERROR",
              float(g["hold_ps"]) == 100 and g["passed"] == "1" and not gate_error(r),
              f"hold_ps {g['hold_ps']} passed {g['passed']}")
        try:
            s = summarize(r, TSCALE)
            zs = [s.get(f"Z_{e}") for e in ("Ge", "Sb", "Te")]
            check(f"{run}: mq_summary runs, Z_Ge/Sb/Te finite", all(z is not None and np.isfinite(z) for z in zs),
                  " ".join(f"{z:.2f}" for z in zs))
            a = analyze(r, TSCALE, cutoff_matrix({}), 15.0, 5)
            check(f"{run}: mq_structure runs, S_NN finite", a["nframes"] > 0 and np.all(np.isfinite(a["snn"])),
                  f"{a['nframes']} frames")
            # two independent paths to Z: the RDF running coordination vs bond counting on trajectory frames
            zd = a["zdist"]
            zt = {e: (zd[k] * np.arange(zd.shape[1])).sum() for k, e in enumerate(("Ge", "Sb", "Te", "C"))}
            dz = {e: abs(s[f"Z_{e}"] - zt[e]) for e in zt if f"Z_{e}" in s}
            check(f"{run}: Z from the RDF and from trajectory frames agree within 0.15", max(dz.values()) < 0.15,
                  " ".join(f"{e} {v:.3f}" for e, v in dz.items()))
            if run == "x10":
                check("x10: C motifs and C-C clusters found", bool(a["cmotifs"]) and bool(a["cclusters"]))
        except Exception as e:                                        # report the failure, keep checking other runs
            check(f"{run}: analysis scripts", False, f"{type(e).__name__}: {e}")

    r = HERE / "x0_gatefail"
    status = (r / "exit_status.txt").read_text().strip() if (r / "exit_status.txt").exists() else "missing"
    check("x0_gatefail: LAMMPS exit status non-zero", status not in ("0", "missing"), status)
    g = kv(r / "gate.txt") if (r / "gate.txt").exists() else {}
    check("x0_gatefail: gate.txt passed 0 and the gate ERROR in log.mq",
          g.get("passed") == "0" and (r / "log.mq").exists() and gate_error(r), f"passed {g.get('passed')}")
    st = kv(r / "stages.txt") if (r / "stages.txt").exists() else {}
    check("x0_gatefail: the quench never started",
          "quench_start_ps" not in st and not (r / "amorphous_300K.data").exists(), " ".join(st))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        kept = complete_runs([HERE / "x0", r])
    check("x0_gatefail: complete_runs skips it and names the failed gate",
          kept == [HERE / "x0"] and "MSD gate failed" in buf.getvalue(), buf.getvalue().strip())


try:
    run_checks()
except Exception as e:                                            # a crash in the checker is a failed test, reported
    check("checker ran to completion", False, f"{type(e).__name__}: {e}")

lines.append(f"VERDICT: {'PASS' if ok else 'FAIL'}")
(HERE / "RESULT.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0 if ok else 1)
