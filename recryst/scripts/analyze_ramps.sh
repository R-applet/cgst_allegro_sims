#!/bin/bash
# Ramp analysis (RUNBOOK.md, Part 3 step 2): the HRATE ramps of params/<MODEL_ID>.sh (0.2 K/ps for run5_ep301), any
# composition and replica that ran. recryst_summary.py reads only ramp.dat and stress.dat here (no dumps), so this
# runs in seconds on a login node.
#   bash scripts/analyze_ramps.sh       -> results/<MODEL_ID>/ramp_h<HRATE>.txt and ramp_tx_h<HRATE>.txt
# What it is for: where crystallization is fast (Tx_xfrac at a slow rate, to centre the anneal grid) and whether the
# model crystallizes at all below TMAX. It is not the Ta guard: a slow ramp's Tx is lower than the 10 K/ps heat of an
# anneal can reach without crystallizing (params TX_GUARD, and analyze_grid.sh's TOO HOT verdict, do that).
set -uo pipefail
hr=${HRATE:-}
source "$(dirname "$(realpath "$0")")/common.sh"
HRATE=${hr:-$HRATE}
G=ramp_*_h${HRATE}_r*
compgen -G "$RUNS/$G" > /dev/null || die "no ramps $RUNS/$G"

# 0. Finished (ramp_done.txt), clean logs, the calibrated criterion and this model in every run.
for r in $RUNS/$G; do
    l=$r/log.ramp
    [ -e $r/ramp_done.txt ] || { [ -e $r/snap_900K.data ] && ! grep -q tmax $l; } \
        || check "$r: not finished (no ramp_done.txt; ramps from before tmax end with snap_900K.data)"
    grep -l -i 'error\|nan' $l && check "$l mentions error/nan: read it before trusting its row"
    grep -q "cutoff $Q_RC components" $l && grep -q "orientorder q4 $Q_THR\$" $l && grep -q "c_ncb>=$Q_NMIN\$" $l \
        || check "$r: criterion is not $Q_RC/$Q_THR/$Q_NMIN"
    grep -Eq "^pair_coeff +\* \* \S*/$MODEL_ID(\.[GN])?\.nequip\.pt2 " $l || check "$r: model is not $MODEL_ID"
done

# 1. One row per run, then mean +- sample std per group. CAUTION: group means skip NaN (a replica that did not
#    crystallize), while n counts every run: read the per-run rows (step 2 does).
out=$RESULTS/ramp_h$HRATE.txt
{ header; MODEL_ID=$MODEL_ID $PY $ROOT/analysis/recryst_summary.py $RUNS/$G; } | tee $out

# 2. Tx per composition from the per-run rows: crystallized replicas, mean and sample std of Tx_xfrac, max sdev_z.
{ header
awk '$1 ~ /^ramp_.*_r[0-9]+$/ {
         delete v; for (i = 2; i < NF; i += 2) v[$i] = $(i + 1)
         g = $1; sub(/_r[0-9]+$/, "", g); n[g]++
         if (v["Tx_xfrac"] != "nan") { k[g]++; s[g] += v["Tx_xfrac"]; q[g] += v["Tx_xfrac"]^2
                                       if (v["sdev_z"] != "nan" && v["sdev_z"] + 0 > z[g]) z[g] = v["sdev_z"] + 0 } }
     END { for (g in n) {
             if (!k[g]) { printf "%-16s crystallized 0 of %d: no Tx below the ramp ceiling\n", g, n[g]; continue }
             m = s[g] / k[g]; sd = (k[g] > 1) ? sqrt((q[g] - k[g] * m * m) / (k[g] - 1)) : -1
             printf "%-16s crystallized %d of %d: Tx_xfrac %.1f +- %s K, max sdev_z %.1f\n",
                    g, k[g], n[g], m, (sd < 0 ? "n/a" : sprintf("%.1f", sd)), z[g] } }' $out | sort; } \
    | tee $RESULTS/ramp_tx_h$HRATE.txt
# Reading: Tx_H and Tx_rho only where Tx_xfrac is finite. drho_x is negative for run5_ep301 (its glass is denser than
# its crystal, tests/RESULTS.md 1g/1k); check its sign for a new model. A ramp that crystallized nothing by TMAX means
# slow kinetics in this model: the anneal grid may be TOO COLD everywhere (RUNBOOK.md).
