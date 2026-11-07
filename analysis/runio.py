"""Shared definitions for the analysis scripts, so they all agree on them.

SPECIES        LAMMPS types 1-4 in order (Ge Sb Te C), fixed by the model.
BOND_RC        bond cutoff (A) per species pair, keyed by frozenset: 3.2 between Ge/Sb/Te (the common a-GST choice),
               2.5 for C-Ge/Sb/Te and 1.9 for C-C (each in the empty gap after its bonding peak in the x10 test glass,
               tests/mq_logic; to be rechecked on the first production x10 glass, meltquench/README.md). Fixed
               cutoffs, not the first g(r) minimum: in the 10 K/ps glass Te-Te has no bonding peak and Ge-Te and Sb-Te
               tail off with no minimum before the second shell, so first-minimum CNs come out at 6-11.
parse_rc(items) --rc overrides: ['GeTe=3.3', 'CC=1.8'] -> {frozenset({'Ge', 'Te'}): 3.3, frozenset({'C'}): 1.8}

load_dat(path)  the .dat time series written by common/in.analysis (mq.dat, ramp.dat, anneal.dat), as a dict of
                columns named by the file's own title line. Repeated steps are dropped: each LAMMPS run stage
                re-prints its first step, and appended resumes repeat the restart step and the title line.
mean_std(arrs)  mean and sample std (ddof = 1) over replicas (axis 0), ignoring NaN; the std is NaN with fewer than
                two values, so a single replica never reports a spread of zero.
complete_runs(runs)  the melt-quench run directories that finished (amorphous_300K.data, written last, exists);
                each other one is reported on stdout and left out, so a running or failed task does not stop the
                summary of the others. May return an empty list.
group_of(name)  the replica group of a run directory name: <cell>_q<qrate>_r<rep> -> <cell>_q<qrate>; any other
                name is its own group.
"""
import re
import warnings
from pathlib import Path

import numpy as np

SPECIES = ["Ge", "Sb", "Te", "C"]
BOND_RC = {frozenset([a, b]): (1.9 if a == b == "C" else 2.5 if "C" in (a, b) else 3.2)
           for k, a in enumerate(SPECIES) for b in SPECIES[k:]}


def parse_rc(items):
    out = {}
    for it in items:
        pair, _, val = it.partition("=")
        a = next((s for s in SPECIES if pair.startswith(s) and pair[len(s):] in SPECIES), None)
        if a is None or not val:
            raise SystemExit(f"--rc {it}: expected PAIR=R with PAIR like GeTe or CC")
        out[frozenset([a, pair[len(a):]])] = float(val)
    return out


def load_dat(path):
    with open(path) as f:
        names = f.readline().lstrip("#").split()
    d = np.loadtxt(path, comments=["#", names[0]], ndmin=2)
    if d.shape[1] != len(names):
        raise ValueError(f"{path}: {d.shape[1]} columns but the title line names {len(names)}")
    d = d[np.unique(d[:, 0], return_index=True)[1]]
    return {c: d[:, k] for k, c in enumerate(names)}


def mean_std(arrs):
    a = np.array(arrs, float)
    n = np.sum(np.isfinite(a), axis=0)
    with warnings.catch_warnings():                               # all-NaN columns: replicas never visited
        warnings.simplefilter("ignore", RuntimeWarning)
        m = np.nanmean(a, 0)
        s = np.where(n > 1, np.nanstd(a, 0, ddof=1), np.nan)
    return m, s


def complete_runs(runs):
    done = []
    for r in map(Path, runs):
        if (r / "amorphous_300K.data").exists():
            done.append(r)
        else:
            g = r / "gate.txt"
            failed = g.exists() and g.read_text().split()[-1] == "0"
            why = "MSD gate failed (gate.txt)" if failed else "no amorphous_300K.data"
            print(f"{r.name}: incomplete ({why}), skipped")
    return done


def group_of(name):
    m = re.match(r"(.+)_q([\d.]+)_r\d+$", Path(name).name)
    return f"{m[1]}_q{m[2]}" if m else Path(name).name
