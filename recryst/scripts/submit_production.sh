#!/bin/bash
# Tested on fake run trees only (2026-11-10), not yet on real outputs. Run from anywhere; paths resolve
# from this file's location.
# Production anneals (recryst/README.md, section 3, "Choosing Ta", step 2): every composition at
# ONE Ta, NREP=10 -> array 0-49: x0 r1-10 (0-9), x1 (10-19), x2p5 (20-29), x5 (30-39), x10 (40-49). Replica r starts
# from glass ((r-1) mod 3)+1 with its own velocity seed. Final criterion 3.8/0.6/4 (README section 1 "Result").
#
# Usage, after the ramp analysis (ramp_tx.txt in recryst/) and the screening analysis, and after the README's
# "Review checkpoint before scaling the anneals":
#   REVIEWED=1 TA=<screening pick> bash scripts/submit_production.sh [--dry-run]
# Refuses to submit unless:
#   - REVIEWED=1 (the checkpoint) and TA has calibrated values (550/600/650);
#   - TA < (lowest Tx_xfrac of any composition that crystallized in ramp_tx.txt) - max(25 K, 2 x its std): the
#     C-rich cells must not crystallize during the heating either;
#   - the x0 screening runs at TA, reused as x0 r1-r3 (same seed and glass for array 0-2), all finished with the
#     final criterion (hold_start.txt), this XSTOP and MAX_NS 5 (anneal_done.txt: "or step N_END");
#   - no other production directory at TA exists yet (no double submission).
set -euo pipefail
ROOT=$(realpath "$(dirname "$(realpath "$0")")/../..")
cd "${RECRYST:-$ROOT/recryst}"                 # RECRYST: another run tree (tests)
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
die() { echo "REFUSED: $*" >&2; exit 1; }
[ "${REVIEWED:-0}" = 1 ] || die "set REVIEWED=1 after the screening review (README: review checkpoint)"
TA=${TA:?set TA from the screening}
declare -A XSTOP_AT=( [550]=0.73 [600]=0.72 [650]=0.70 )   # calibrate.out: 0.85 x lowest crystal reference (x5)
XSTOP=${XSTOP_AT[$TA]:-}; [ -n "$XSTOP" ] || die "no calibrated XSTOP for TA=$TA (550/600/650)"
export EXTRA_VARS="-var q_rc 3.8 -var q_thr 0.6 -var q_nmin 4"
N_END=$(( 5000 + 50 * (TA - 300) + 2500000 ))     # in.anneal at dt 2 fs: 10 ps + heating at 10 K/ps + 5 ns

# 1. Ta below every crystallizing composition's 1 K/ps Tx (ramp_tx.txt from the ramp analysis).
[ -e ramp_tx.txt ] || die "ramp_tx.txt missing: run the ramp analysis first"
lim=$(awk '/crystallized [1-9]/ { split($0, a, "Tx_xfrac "); split(a[2], b, " "); sd = (b[3] == "n/a") ? 0 : b[3]
                                  m = 2 * sd; if (m < 25) m = 25; l = b[1] - m
                                  if (!f || l < lo) { lo = l; who = $1 }; f = 1 }
           END { if (f) printf "%.1f %s", lo, who }' ramp_tx.txt)
[ -n "$lim" ] || die "no composition crystallized in the ramps: no Tx limit"
read limit who <<< "$lim"
awk -v t=$TA -v l=$limit 'BEGIN { exit !(t < l) }' || die "TA $TA not below $limit K (set by $who)"
echo "TA $TA < $limit K (tightest: $who)"

# 2. Screening runs reused as x0 r1-r3: finished, same criterion, XSTOP and MAX_NS.
for r in 1 2 3; do
    d=runs/anneal_x0_T${TA}_r$r
    [ -d $d ] || { echo "$d absent: production will run it"; continue; }
    [ -e $d/anneal_done.txt ] || die "$d exists but is not finished (its chain may still be running)"
    read -r _ _ k1 v1 k2 v2 k3 v3 < $d/hold_start.txt
    [ "$k1 $v1 $k2 $v2 $k3 $v3" = "q_rc 3.8 q_thr 0.6 q_nmin 4" ] || die "$d criterion: $k1 $v1 $k2 $v2 $k3 $v3"
    grep -q "(stop at xfracGST > $XSTOP or step $N_END)" $d/anneal_done.txt \
        || die "$d: $(grep -o '(stop at.*)' $d/anneal_done.txt), expected XSTOP $XSTOP, step $N_END"
    echo "$d: reused (criterion, XSTOP $XSTOP, step $N_END match)"
done

# 3. No double submission: any production directory other than the screening x0 r1-r3.
# untagged runs only: TAG=aniso reruns (anneal_<cell>_aniso_T..) are separate and must not block production
other=$(ls -d runs/anneal_{x0,x1,x2p5,x5,x10}_T${TA}_r* 2>/dev/null | grep -v -E "^runs/anneal_x0_T${TA}_r[123]$" || true)
[ -z "$other" ] || die "production directories already exist: $(echo $other | head -c 200)"

# 4. Submit: one perc A100-40GB per run, at most 10 at a time (%10 throttles the initial tasks; continuation jobs are
#    separate submissions). A non-halting run is ~40 h (2 chain links); worst case ~5 waves x 40 h ~ 8 days.
#    (strachan A30s: ~5-day backlog on 2026-11-10, so not used.)
cmd=(sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1
     --array=0-49%10 --export=ALL,TA=$TA,NREP=10,XSTOP=$XSTOP submit_anneal.sh)
echo "${cmd[*]}  (EXTRA_VARS=$EXTRA_VARS)"
[ $DRY = 1 ] || "${cmd[@]}"

# Analysis: scripts/analyze_production.sh (per-composition --x-crystal at TA from calibrate.out; --nucleated-size
# 250 / 260 / 210 at 550 / 600 / 650 K, to confirm against job 12309345's calibrate.out).
# More replicas for two close compositions: NREP=20 remaps indices (x0 -> --array=10-19); submit only the new ones.
