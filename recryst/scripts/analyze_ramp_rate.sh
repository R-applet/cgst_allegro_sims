#!/bin/bash
# Tested on fake run trees only (2026-11-10), not yet on real outputs. Run from anywhere; paths resolve
# from this file's location.
# Heating-rate check (recryst/README.md section 2): x0 r1 at 0.2 K/ps (runs/ramp_x0_h0.2_r1) against the same glass and
# seed index at 1 K/ps (runs/ramp_x0_h1_r1), with the 1 K/ps replica spread (ramp_x0_h1_r1-3) as the yardstick.
# Slower heating gives crystallization more time, so Tx should drop. Only the direction and size of the shift compare
# with experiment (MD rates are ~1e10 x DSC); a two-point Kissinger slope gives a rough apparent activation energy.
#   bash scripts/analyze_ramp_rate.sh            (after jobs 12308688 and 12308689; FORCE=1 to run on fewer x0 ramps)
set -uo pipefail
ROOT=$(realpath "$(dirname "$(realpath "$0")")/../..")
cd "${RECRYST:-$ROOT/recryst}"                 # RECRYST: another run tree (tests)
PY=${PY:-$ROOT/env/cgst-ana/bin/python}
die() { echo "STOPPED: $*" >&2; exit 1; }
check() { [ "${FORCE:-0}" = 1 ] && { echo "WARNING (FORCE=1): $*"; return; }; die "$*"; }

# 0. Both rates finished, same criterion; the 1 K/ps replicas for the spread.
[ -e runs/ramp_x0_h0.2_r1/snap_900K.data ] || die "0.2 K/ps ramp not finished (no snap_900K.data)"
for r in runs/ramp_x0_h0.2_r1 runs/ramp_x0_h1_r1 runs/ramp_x0_h1_r2 runs/ramp_x0_h1_r3; do
    [ -e $r/snap_900K.data ] || { check "$r not finished"; continue; }
    grep -q 'cutoff 3.8 components' $r/log.ramp && grep -q 'orientorder q4 0.6$' $r/log.ramp \
        && grep -q 'c_ncb>=4$' $r/log.ramp || check "$r: criterion is not 3.8/0.6/4"
done

# 1. One summary over the four runs (groups ramp_x0_h0.2 and ramp_x0_h1).
$PY $ROOT/analysis/recryst_summary.py runs/ramp_x0_h0.2_r1 runs/ramp_x0_h1_r[123] > ramp_rate_x0.txt \
    || die "recryst_summary.py failed"

# 2. Shift, against the replica spread, and the Kissinger estimate.
$PY - ramp_rate_x0.txt <<'EOF' | tee ramp_rate_x0_verdict.txt
import math, re, sys
rows = {}
for line in open(sys.argv[1]):
    f = line.split()
    if f and re.match(r"ramp_x0_h(0\.2|1)_r\d+$", f[0]):
        rows[f[0]] = {k: float(v) for k, v in zip(f[1::2], f[2::2])}
slow, fast = rows.get("ramp_x0_h0.2_r1"), rows.get("ramp_x0_h1_r1")
if not slow or not fast:
    sys.exit("missing ramp_x0_h0.2_r1 or ramp_x0_h1_r1 in the summary")
reps = [r for k, r in rows.items() if k.startswith("ramp_x0_h1_")]
for key in ("Tx_xfrac", "Tx_H", "Tx_rho"):
    a, b = slow[key], fast[key]
    vals = [r[key] for r in reps if math.isfinite(r[key])]
    sd = (sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5 if len(vals) > 1 else math.nan
    if not (math.isfinite(a) and math.isfinite(b)):
        print(f"{key}: 0.2 K/ps {a:.1f}, 1 K/ps {b:.1f} -- not both finite"); continue
    d = a - b
    size = (f"{abs(d) / sd:.1f} x the 1 K/ps replica std ({sd:.1f} K, {len(vals)} runs)" if math.isfinite(sd) and sd > 0
            else "no replica spread available")
    if math.isfinite(sd) and sd > 0 and abs(d) < 2 * sd:
        verdict = " -> within 2 replica std: not resolved"
    elif d < 0:
        verdict = " -> LOWER at slower heating, as expected"
    elif d > 0:
        verdict = " -> HIGHER at slower heating: unexpected, check the runs"
    else:
        verdict = " -> no shift"
    print(f"{key}: 0.2 K/ps {a:.1f} K, 1 K/ps {b:.1f} K, shift {d:+.1f} K = {size}{verdict}")
print(f"x_peak: 0.2 K/ps {slow['x_peak']:.3f}, 1 K/ps {fast['x_peak']:.3f} (slower heating may reach a higher crystalline ceiling)")
print(f"sdev_z: 0.2 K/ps {slow['sdev_z']:.1f}, 1 K/ps {fast['sdev_z']:.1f} (> 5 in a crystallized run: barostat stress)")
# Kissinger: ln(beta / Tx^2) = -Ea / (R Tx) + c. Two rates -> Ea = R ln[(b1/T1^2) / (b2/T2^2)] / (1/T2 - 1/T1).
# Uncertainty: shift each Tx by +-1 replica std (the 0.2 K/ps run has no replicas; the 1 K/ps std stands in for both).
R = 8.617333e-5                                                     # eV/K
T1, T2 = slow["Tx_xfrac"], fast["Tx_xfrac"]                         # beta1 = 0.2, beta2 = 1 K/ps
txs = [r["Tx_xfrac"] for r in reps if math.isfinite(r["Tx_xfrac"])]
sd = (sum((v - sum(txs) / len(txs)) ** 2 for v in txs) / (len(txs) - 1)) ** 0.5 if len(txs) > 1 else 0.0
ea = lambda t1, t2: R * math.log((0.2 / t1 ** 2) / (1.0 / t2 ** 2)) / (1 / t2 - 1 / t1) if t1 != t2 else math.nan
if math.isfinite(T1) and math.isfinite(T2) and T1 < T2:
    e = ea(T1, T2); lo_hi = sorted(x for x in (ea(T1 + sd, T2 - sd), ea(T1 - sd, T2 + sd)) if math.isfinite(x) and x > 0)
    rng = f" (range {lo_hi[0]:.2f}-{lo_hi[-1]:.2f} eV for +-{sd:.1f} K on each Tx)" if lo_hi and sd > 0 else ""
    print(f"Kissinger, two rates only: Ea ~ {e:.2f} eV{rng}. Rough: two points, one replica at 0.2 K/ps, and MD rates"
          f" far from DSC; compare the order of magnitude with the literature, not the value.")
else:
    print("Kissinger: needs Tx_xfrac finite at both rates and lower at 0.2 K/ps; not computed")
EOF
