#!/bin/bash
# Tested on fake run trees (2026-11-10); run on the real ramps 2026-11-11 (RESULTS.md sections 2-3).
# Run from anywhere; paths resolve from this file's location.
# ramp analysis (recryst/README.md section 2), for after jobs 12308688 (1 K/ps, 15 runs) and 12308689
# (0.2 K/ps, x0 r1). Final criterion 3.8/0.6/4 (README section 1 "Result"), which the ramps were submitted with, so
# Tx_xfrac from ramp.dat needs no recount. recryst_summary.py on ramps reads only ramp.dat and stress.dat (no dumps),
# so it runs on the login node with the cgst-ana python -- unless the node is overloaded (load ~88 on 2026-11-10).
# Ends by printing the TX_X0 / TX_X0_STD line for scripts/submit_screen.sh.
set -uo pipefail
ROOT=$(realpath "$(dirname "$(realpath "$0")")/../..")
cd "${RECRYST:-$ROOT/recryst}"                 # RECRYST: another run tree (tests)
PY=${PY:-$ROOT/env/cgst-ana/bin/python}

# 0. Did every task finish? The summary skips runs without snap_900K.data; list them here.
sacct -j 12308688,12308689 -X -n -o JobID,State,ExitCode,Elapsed
for r in runs/ramp_*; do [ -e $r/snap_900K.data ] || echo "INCOMPLETE: $r"; done
grep -l -i 'error\|nan' runs/ramp_*/log.ramp       # anything here -> read that log before trusting its row

# 1. Criterion of every run. LAMMPS logs each line twice, raw and substituted, so the substituted values are visible
#    (checked on the running ramp_x0_h1_r1: "cutoff 3.8", "orientorder q4 0.6", "c_ncb>=4").
for r in runs/ramp_*; do
    l=$r/log.ramp
    grep -q 'cutoff 3.8 components' $l && grep -q 'orientorder q4 0.6$' $l && grep -q 'c_ncb>=4$' $l \
        && echo "criterion ok: $r" || echo "CRITERION MISMATCH: $r"
done

# 2. Summary: one row per run, then mean +- sample std per group (ramp_<cell>_h1, n=3; ramp_x0_h0.2 is n=1).
#    CAUTION: the group line's n is the number of runs, but its means skip NaN (runio.mean_std). If a replica did not
#    crystallize (Tx_xfrac nan), its group's Tx_xfrac mean is over fewer runs. Read the per-run rows.
$PY $ROOT/analysis/recryst_summary.py runs/ramp_{x0,x1,x2p5,x5,x10}_h1_r* | tee ramp_summary_h1.txt   # untagged (no aniso)
[ -e runs/ramp_x0_h0.2_r1/snap_900K.data ] \
    && $PY $ROOT/analysis/recryst_summary.py runs/ramp_x0_h0.2_r1 runs/ramp_x0_h1_r1 | tee ramp_summary_rate.txt \
    || echo "0.2 K/ps ramp not finished: rate check later"

# 3. Tx per composition from the per-run rows: crystallized replicas, mean and sample std of Tx_xfrac, mean Tx_H
#    over those replicas, and the max sdev_z among them.
awk '$1 ~ /^ramp_.*_h1_r[0-9]+$/ {
         delete v; for (i = 2; i < NF; i += 2) v[$i] = $(i + 1)
         g = $1; sub(/_r[0-9]+$/, "", g); n[g]++
         if (v["Tx_xfrac"] != "nan") { k[g]++; s[g] += v["Tx_xfrac"]; q[g] += v["Tx_xfrac"]^2; h[g] += v["Tx_H"]
                                       if (v["sdev_z"] != "nan" && v["sdev_z"] + 0 > z[g]) z[g] = v["sdev_z"] + 0 } }
     END { for (g in n) {
             if (!k[g]) { printf "%-14s crystallized 0 of %d: no Tx (did not crystallize by 900 K)\n", g, n[g]; continue }
             m = s[g] / k[g]; sd = (k[g] > 1) ? sqrt((q[g] - k[g] * m * m) / (k[g] - 1)) : -1
             printf "%-14s crystallized %d of %d: Tx_xfrac %.1f +- %s K, Tx_H %.1f K, max sdev_z %.1f\n",
                    g, k[g], n[g], m, (sd < 0 ? "n/a" : sprintf("%.1f", sd)), h[g] / k[g], z[g] } }' \
    ramp_summary_h1.txt | sort | tee ramp_tx.txt

# 4. Input for the screening script, only when all 3 x0 replicas crystallized (otherwise decide by hand).
awk '$1 == "ramp_x0_h1" && $3 == 3 && $4 == "of" && $5 == "3:" {
         split($0, a, "Tx_xfrac "); split(a[2], b, " "); print "TX_X0=" b[1] " TX_X0_STD=" b[3] " bash scripts/submit_screen.sh --dry-run"; f = 1 }
     END { if (!f) print "x0: not all 3 replicas crystallized -> no automatic TX_X0; decide the screening Ta by hand" }' ramp_tx.txt

# 5. What to read off:
#  - Tx_H should agree with Tx_xfrac within about the replica spread; read Tx_H/Tx_rho only where Tx_xfrac is finite.
#    drho_x is expected NEGATIVE (the model's glass is denser than its crystal; tests/RESULTS.md 1g/1k).
#  - x5/x10 may not crystallize by 900 K (x10 rocksalt is unstable; the crystal ceiling falls with C).
#  - max sdev_z > 5 in a crystallized run -> barostat stress; rerun that composition with TAG=aniso and
#    EXTRA_VARS="-var q_rc 3.8 -var q_thr 0.6 -var q_nmin 4 -var baro aniso" (submit_ramp.sh).
#  - Rate check: Tx(0.2 K/ps) - Tx(1 K/ps) for x0 r1 (same glass and seed index); slower heating -> lower Tx.
#  - Production Ta (one for all compositions) must also be below the LOWEST Tx of any composition that crystallized.
