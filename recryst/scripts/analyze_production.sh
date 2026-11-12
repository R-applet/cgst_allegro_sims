#!/bin/bash
# Tested on fake run trees only (2026-11-10), not yet on real outputs. Run from anywhere; paths resolve
# from this file's location.
# production analysis (recryst/README.md section 3, "Choosing Ta", step 2): 5 compositions x 10 replicas at one
# Ta, final criterion 3.8/0.6/4 (README section 1 "Result").
#   TA=<Ta> bash scripts/analyze_production.sh summary [--dry-run]   checks, fraction summaries, submits cluster jobs
#   TA=<Ta> bash scripts/analyze_production.sh compare                 after the 5 cluster jobs: rate comparison
# Stops on: an uncalibrated Ta; fewer than 10 finished runs in a composition; more than one criterion, XSTOP or final
# step among the runs (FORCE=1 to analyse anyway, e.g. a deliberately partial set).
set -uo pipefail
ROOT=$(realpath "$(dirname "$(realpath "$0")")/../..")
cd "${RECRYST:-$ROOT/recryst}"                 # RECRYST: another run tree (tests)
PY=${PY:-$ROOT/env/cgst-ana/bin/python}
die() { echo "STOPPED: $*" >&2; exit 1; }
TA=${TA:?set TA}; STAGE=${1:?summary or compare}; DRY=0; [ "${2:-}" = "--dry-run" ] && DRY=1
CELLS="x0 x1 x2p5 x5 x10"
Q="--q-rc 3.8 --q-thr 0.6 --q-nmin 4"
# calibrate.out at 3.8/0.6/4 (--choose run, job 12309345): per-composition crystal reference (x10: none -> the run's
# plateau, else XSTOP) and --nucleated-size (2 x the largest glass cluster at TA); checked for commit 5cfeee0.
case $TA in
    550) declare -A XC=( [x0]=0.951 [x1]=0.956 [x2p5]=0.923 [x5]=0.862 ); NUC=250 ;;
    600) declare -A XC=( [x0]=0.950 [x1]=0.951 [x2p5]=0.916 [x5]=0.842 ); NUC=260 ;;
    650) declare -A XC=( [x0]=0.948 [x1]=0.947 [x2p5]=0.904 [x5]=0.822 ); NUC=210 ;;
    *) die "no calibrated values for TA=$TA (550/600/650)" ;;
esac
xc() { [ -n "${XC[$1]:-}" ] && echo "--x-crystal ${XC[$1]}"; }
check() { [ "${FORCE:-0}" = 1 ] && { echo "WARNING (FORCE=1): $*"; return; }; die "$*"; }

if [ $STAGE = summary ]; then
    # 0. Completeness and consistency, over the untagged runs only (TAG=aniso runs are anneal_<cell>_aniso_T..).
    for c in $CELLS; do
        n=$(ls -d runs/anneal_${c}_T${TA}_r* 2>/dev/null | wc -l)
        d=$(ls runs/anneal_${c}_T${TA}_r*/anneal_done.txt 2>/dev/null | wc -l)
        echo "$c: $d of $n finished"; [ $d -ge 10 ] || check "$c: only $d finished runs at $TA K"
    done
    crit=$(cat runs/anneal_{x0,x1,x2p5,x5,x10}_T${TA}_r*/hold_start.txt | awk '{print $4, $6, $8}' | sort -u)
    [ "$crit" = "3.8 0.6 4" ] || check "criteria found: $(echo $crit)"
    stops=$(grep -ho '(stop at.*)' runs/anneal_{x0,x1,x2p5,x5,x10}_T${TA}_r*/anneal_done.txt | sort -u)
    [ $(echo "$stops" | wc -l) = 1 ] || check "XSTOP/final step differ: $(echo $stops)"
    echo "criterion $crit; $stops"
    grep -l 'stopping the chain' slurm-anneal-*.out 2>/dev/null && check "a chain stopped for no progress (above)"

    # 1. Fraction curves, one call per composition with its own x_c (light: anneal.dat/stress.dat only).
    #    CAUTION: group lines say n=10 but their means skip NaN (runio.mean_std): t50/t_inc means are over the runs
    #    that got there. Count finite t50 per composition from the per-run rows.
    for c in $CELLS; do
        $PY $ROOT/analysis/recryst_summary.py $(xc $c) runs/anneal_${c}_T${TA}_r* > prod_${c}.txt
        awk -v c=$c '$1 ~ /_r[0-9]+$/ { delete v; for (i = 2; i < NF; i += 2) v[$i] = $(i + 1); n++
                                        if (v["t50"] != "nan") k++; if (v["sdev_z"] + 0 > 5 && v["t50"] != "nan") s++
                                        x[v["x_c_from"]]++ }
             END { printf "%-5s t50 reached %d of %d; crystallized with sdev_z > 5: %d; x_c from:", c, k, n, s
                   for (f in x) printf " %s %d", f, x[f]; print "" }' prod_${c}.txt
    done | tee prod_overview.txt

    # 2. Clusters, t_nuc, v_growth, J_surv, MFPT: every frame of 50 runs -> one perc job per composition (values
    #    expanded at submission; limit ~ screening cluster job time x 10/3). Run after the anneals, so no competition
    #    for the perc GPUs.
    for c in $CELLS; do
        cmd="$PY $ROOT/analysis/recryst_summary.py $(xc $c) --clusters --nucleated-size $NUC $Q runs/anneal_${c}_T${TA}_r* > prod_${c}_clusters.txt 2>&1"
        echo "$cmd"
        [ $DRY = 1 ] || sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1 --cpus-per-task=4 --mem=32G \
            -t 08:00:00 -J cgst-prod-cl-$c -o slurm-prod-clusters-$c-%j.out --wrap "$cmd"
    done
elif [ $STAGE = compare ]; then
    # 3. Every composition's cluster output must be complete: 10 per-run rows and its nucleation line.
    for c in $CELLS; do
        f=prod_${c}_clusters.txt; [ -e $f ] || die "$f missing (cluster job not run or not finished)"
        rows=$(grep -c "^anneal_${c}_T${TA}_r[0-9]* .*t_nuc" $f); nuc=$(grep -c "^anneal_${c}_T${TA} .*nucleation:" $f)
        [ "$rows" -ge 10 ] && [ "$nuc" = 1 ] || check "$f: $rows run rows, $nuc nucleation lines"
        grep -h "nucleation:" $f | awk -v N=$NUC '{ for (i = 3; i < NF; i += 2) if ($i == "n_base" && $(i+1) * 2 > N)
            print "  " $1 ": n_base " $(i+1) " is more than half of --nucleated-size " N " (glass aging?)" }'
    done
    $PY $ROOT/analysis/rate_compare.py prod_*_clusters.txt | tee prod_rates.txt
else
    die "stage must be summary or compare"
fi

# 4. Reading it:
#  - Per composition (nucleation: line): n_nucleated of 10, J_surv +- J_surv_rel_err (1/sqrt(n)); MFPT n_base,
#    n_star, tau_J, J. n_star NaN = critical size hidden in the glass's order or never reached; then use J_surv only.
#  - n_base above half of --nucleated-size (flagged by 'compare') -> glass aging; t_nuc and J_surv suspect there.
#  - v_growth (m/s) per composition; t50/t_inc from prod_<c>.txt as cross-checks, with prod_overview.txt's counts.
#    x_c_from should be 'plateau' or 'x-crystal' (x10: 'plateau' or 'xstop' -- its X is the least certain).
#  - Few or zero events (x10, maybe x5): J_surv error 1/sqrt(n), 58% at 3 events; 0 events -> "no nucleation in
#    10 x 5 ns" (rate_compare.py skips zero-event compositions in the pairwise tests).
#  - Crystallized runs with sdev_z > 5 (prod_overview.txt) -> aniso rerun of that composition (scripts/submit_aniso.sh,
#    TAG=aniso).
#  - Composition pairs (prod_rates.txt): rate ratio, ~95% interval, Bonferroni p over the pairs. Rates within ~2x or
#    an interval spanning 1 -> replicas 11-20 for those two (NREP=20 remaps indices). Pairwise test ~6% at 5%.
#  - Glass test per composition: p < 0.05 -> rates depend on the source glass (more melt-quench samples needed).
#    Low power (~36% for a 6x slower glass), so p > 0.05 does not show the glasses agree.
#  - Deliverable: J_surv and v_growth vs C content, with the ramp Tx vs C alongside.
