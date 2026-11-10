#!/bin/bash
# Tested on fake run trees only (2026-11-10), not yet on real outputs. Run from anywhere; paths resolve
# from this file's location.
# ramp aniso analysis: compares a composition's 1 K/ps iso ramps (runs/ramp_<c>_h1_r1-3) with their TAG=aniso
# reruns (runs/ramp_<c>_aniso_h1_r1-3, same seeds and glasses; scripts/submit_aniso.sh KIND=ramp). Final criterion
# 3.8/0.6/4 for both. recryst_summary.py on ramps reads ramp.dat/stress.dat only (login node OK unless overloaded).
#   CELL=<cell> bash scripts/analyze_ramp_aniso.sh            (FORCE=1 to compare an incomplete set)
# Stops unless both sets have 3 finished runs, the final criterion, and the barostat their name says (from the
# substituted 'fix npt' line in log.ramp: ' iso 0.0 0.0' vs ' aniso 0.0 0.0').
set -uo pipefail
ROOT=$(realpath "$(dirname "$(realpath "$0")")/../..")
cd "${RECRYST:-$ROOT/recryst}"                 # RECRYST: another run tree (tests)
PY=${PY:-$ROOT/env/cgst-ana/bin/python}
die() { echo "STOPPED: $*" >&2; exit 1; }
check() { [ "${FORCE:-0}" = 1 ] && { echo "WARNING (FORCE=1): $*"; return; }; die "$*"; }
CELL=${CELL:?set CELL}
ISO="runs/ramp_${CELL}_h1_r"; ANI="runs/ramp_${CELL}_aniso_h1_r"

# 0. Completeness, criterion and barostat of every run in both sets.
for set in iso aniso; do
    pre=$([ $set = iso ] && echo $ISO || echo $ANI); n=0
    for r in 1 2 3; do d=$pre$r; l=$d/log.ramp
        [ -e $d/snap_900K.data ] || { check "$d not finished"; continue; }; n=$((n + 1))
        grep -q 'cutoff 3.8 components' $l && grep -q 'orientorder q4 0.6$' $l && grep -q 'c_ncb>=4$' $l \
            || check "$d: criterion is not 3.8/0.6/4"
        if [ $set = aniso ]; then grep -q ' aniso 0.0 0.0' $l && ! grep -q ' iso 0.0 0.0' $l || check "$d: not aniso"
        else grep -q ' iso 0.0 0.0' $l && ! grep -q ' aniso 0.0 0.0' $l || check "$d: not iso"; fi
    done
    echo "$set: $n of 3 finished, criterion and barostat checked"
done

# 1. Summaries (one call, both groups; group_of keeps ramp_<c>_h1 and ramp_<c>_aniso_h1 apart).
$PY $ROOT/analysis/recryst_summary.py ${ISO}* ${ANI}* > ramp_aniso_${CELL}.txt || die "recryst_summary.py failed"

# 2. Per group from the per-run rows (the group lines' means skip NaN), and the iso-vs-aniso comparison.
$PY - ramp_aniso_${CELL}.txt $CELL <<'EOF' | tee ramp_aniso_${CELL}_verdict.txt
import math, re, sys
from scipy.stats import ttest_ind
path, cell = sys.argv[1], sys.argv[2]
runs = {}
for line in open(path):
    f = line.split()
    if f and re.match(rf"ramp_{cell}(_aniso)?_h1_r\d+$", f[0]):
        runs.setdefault("aniso" if "_aniso_" in f[0] else "iso", []).append({k: float(v) for k, v in zip(f[1::2], f[2::2])})
fin = lambda xs: [x for x in xs if math.isfinite(x)]
stat = {}
for g in ("iso", "aniso"):
    rs = runs.get(g, [])
    tx, th = fin([r["Tx_xfrac"] for r in rs]), [r["Tx_H"] for r in rs if math.isfinite(r["Tx_xfrac"])]
    sz = fin([r["sdev_z"] for r in rs if math.isfinite(r["Tx_xfrac"])])
    stat[g] = (tx, th, sz)
    sd = f"{(sum((x - sum(tx)/len(tx))**2 for x in tx)/(len(tx)-1))**0.5:.1f}" if len(tx) > 1 else "n/a"
    print(f"{g:6s} crystallized {len(tx)} of {len(rs)}: Tx_xfrac " + (f"{sum(tx)/len(tx):.1f} +- {sd} K" if tx else "none")
          + (f", Tx_H {sum(th)/len(th):.1f} K" if th else "") + (f", sdev_z max {max(sz):.1f}" if sz else ""))
(ti, hi, zi), (ta, ha, za) = stat["iso"], stat["aniso"]
if za:
    print("stress: " + ("aniso removed it (max sdev_z <= 5)" if max(za) <= 5 else
                        f"aniso still stressed (max sdev_z {max(za):.1f}): the stress is not from the box shape"))
for name, a, b in (("Tx_xfrac", ti, ta), ("Tx_H", hi, ha)):
    if len(a) < 2 or len(b) < 2:
        print(f"{name}: too few crystallized runs to compare ({len(a)} iso, {len(b)} aniso)"); continue
    d = sum(b)/len(b) - sum(a)/len(a); p = ttest_ind(b, a, equal_var=False).pvalue
    print(f"{name}: aniso - iso = {d:+.1f} K, Welch p = {p:.3g}"
          + (" -> aniso crystallizes EARLIER: the iso box held it back; iso Tx for this composition is biased"
             if p < 0.05 and d < 0 else " -> aniso LATER (unexpected; check the runs)" if p < 0.05
             else " -> no significant shift (3 vs 3 detects only shifts of several replica spreads)"))
EOF
# If biased: the Tx-vs-C trend needs every composition under the same barostat (rerun the others with TAG=aniso, or
# report this composition's aniso Tx with the caveat). The 0.2 K/ps x0 run has no aniso counterpart (A30-only, >21 h).
