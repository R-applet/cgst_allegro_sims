#!/bin/bash
# Analysis of the anneal grid (submit_grid.sh; RUNBOOK.md, recryst steps 3-4), per composition and Ta that has runs.
#   [CELLS="x0"] bash scripts/analyze_grid.sh summary [--dry-run]   checks, fraction summaries, ONE perc cluster job
#   [CELLS="x0"] bash scripts/analyze_grid.sh verdict                after the cluster job: verdicts and growth table
# Every number (criterion, NUC, GLASS_<cell>, X_END/X_END_CELL, XSTOP, MAX_NS, BARO, RUNTAG) is from recryst/params/<MODEL_ID>.sh and its
# calib_params.sh. Outputs in results/<MODEL_ID>/, each starting with '#' lines naming the model and criterion:
#   grid_<cell>[_<RUNTAG>]_T<Ta>.txt            recryst_summary.py --x-end <the cell's X_END> (t_inc, t50, stress)
#   grid_<cell>[_<RUNTAG>]_T<Ta>_clusters.txt   the same with --clusters (t_nuc, v_growth, single_grain, J_surv, MFPT)
#   grid_verdict.txt                            per (cell, Ta): TOO HOT / TOO COLD / USABLE, nucleated k of n
#   growth_table.csv                            per run: cell, Ta, rep, t_nuc, t50, v_growth, single_grain, sdev_z
# summary stops on a set with unfinished runs or a criterion, barostat, model, XSTOP or hold that differs from the
# params (FORCE=1 -> warning; common.sh check_anneal_set).
# v_growth with single_grain < 0.8 mixes two grains for over 20% of its window: read it as an upper bound.
set -uo pipefail
source "$(dirname "$(realpath "$0")")/common.sh"
STAGE=${1:?summary or verdict}; DRY=0; [ "${2:-}" = "--dry-run" ] && DRY=1
CELLS=${CELLS:-${CELLS_ALL[*]}}
SETS=()                                     # "cell Ta" pairs with runs
for c in $CELLS; do
    [ -n "${CI[$c]:-}" ] || die "unknown cell $c"
    for T in $CALIB_TS; do compgen -G "$RUNS/anneal_${c}${STEM}_T${T}_r*" > /dev/null && SETS+=("$c $T"); done
done
[ ${#SETS[@]} -gt 0 ] || die "no anneal runs for CELLS '$CELLS' in $RUNS (name stem anneal_<cell>${STEM}_T<Ta>)"
out() { echo "$RESULTS/grid_$1${STEM}_T$2$3"; }

if [ $STAGE = summary ]; then
    for s in "${SETS[@]}"; do set -- $s
        check_anneal_set $1 $2 $RUNS/anneal_$1${STEM}_T$2_r*
    done
    grep -l 'stopping the chain' slurm-anneal-*.out 2>/dev/null && check "a chain stopped for no progress (above)"
    cmds=""
    for s in "${SETS[@]}"; do set -- $s
        { header $1; MODEL_ID=$MODEL_ID $PY $ROOT/analysis/recryst_summary.py --x-end $(x_end $1) $RUNS/anneal_$1${STEM}_T$2_r*; } \
            > $(out $1 $2 .txt)
        cmds+="{ $(header $1 | sed 's/^/echo "/; s/$/"/'); $PY $ROOT/analysis/recryst_summary.py --x-end $(x_end $1) --clusters"
        cmds+=" --nucleated-size ${NUC[$2]} $Q_ARGS $RUNS/anneal_$1${STEM}_T$2_r*; } > $(out $1 $2 _clusters.txt) 2>&1; "
    done
    echo "$cmds" | tr ';' '\n' | sed '/^ *$/d'
    [ $DRY = 1 ] || sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1 --cpus-per-task=4 --mem=32G \
        -t 08:00:00 -J cgst-grid-cl -o slurm-grid-clusters-%j.out --export=ALL,MODEL_ID=$MODEL_ID --wrap "$cmds"
elif [ $STAGE = verdict ]; then
    # Per (cell, Ta), from the cluster output's per-run rows and nucleation line:
    #   TOO HOT  any run with x_a > glass + 0.05, t_nuc < 20 ps, or t_inc < 50 ps; or n_base >= NUC (it crystallized
    #            during the 10 K/ps heat, or the glass already holds a nucleus-sized cluster)
    #   TOO COLD no run nucleated within MAX_NS
    #   USABLE   otherwise; also how many nucleated, n_base / NUC (> 0.5: the glass is close to nucleus size)
    { header
    for s in "${SETS[@]}"; do set -- $s
        f=$(out $1 $2 _clusters.txt); [ -e $f ] || die "$f missing (cluster job not run or not finished)"
        grep -q "^WARNING" $f && check "$f: $(grep -m1 '^WARNING' $f)"
        grep -q "nucleation:" $f || check "$f: no nucleation line"
        declare -n G=GLASS_$1
        awk -v c=$1 -v T=$2 -v g=${G[$2]} -v N=${NUC[$2]} '
            $1 ~ /_r[0-9]+$/ { delete v; for (i = 2; i < NF; i += 2) v[$i] = $(i + 1); n++
                               if (v["t_nuc"] != "nan") { k++; if (v["t_nuc"] + 0 < 20) hot = hot " t_nuc<20ps:" $1 }
                               if (v["x_a"] + 0 > g + 0.05) hot = hot " x_a>glass+0.05:" $1
                               if (v["t_inc"] != "nan" && v["t_inc"] + 0 < 50) hot = hot " t_inc<50ps:" $1 }
            $2 == "nucleation:" { for (i = 3; i < NF; i += 2) if ($i == "n_base") nb = $(i + 1) }
            END { if (nb + 0 >= N) hot = hot " n_base>=N"
                  verdict = hot != "" ? "TOO HOT" : (k == 0 ? "TOO COLD" : "USABLE")
                  printf "%-5s T%s: %-8s nucleated %d of %d; n_base %s / N %d (%.2f)%s\n", c, T, verdict, k, n, nb, N,
                         nb / N, (hot != "" ? ";" hot : "") }' $f
        unset -n G
    done; } | tee $RESULTS/grid_verdict.txt
    { header; echo "cell,Ta,rep,t_nuc_ps,t50_ps,v_growth_m_s,single_grain,sdev_z"
    for s in "${SETS[@]}"; do set -- $s
        awk -v c=$1 -v T=$2 '$1 ~ /_r[0-9]+$/ { delete v; for (i = 2; i < NF; i += 2) v[$i] = $(i + 1)
                 r = $1; sub(/.*_r/, "", r)
                 print c "," T "," r "," v["t_nuc"] "," v["t50"] "," v["v_growth"] "," v["single_grain"] "," v["sdev_z"] }' \
            $(out $1 $2 _clusters.txt)
    done; } > $RESULTS/growth_table.csv
    echo "wrote $RESULTS/grid_verdict.txt, $RESULTS/growth_table.csv ($(($(wc -l < $RESULTS/growth_table.csv) - 2)) runs)"
else
    die "stage must be summary or verdict"
fi
# Notes: J_surv from 3 runs is +-58% at best, and MFPT n_star / tau_J are mostly NaN with 3 replicas: the grid
# measures v_growth and t50; rates need more replicas where they matter. In the cluster files the largest cluster
# should jump from glass-like (n_base) to far above N within a few hundred ps of t_nuc (one growing nucleus).
