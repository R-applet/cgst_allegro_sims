#!/bin/bash
# Tested on fake run trees only (2026-11-10), not yet on real outputs. Run from anywhere; paths resolve
# from this file's location.
# screening analysis (recryst/README.md section 3, "Choosing Ta", step 1): x0 r1-r3 at each screened Ta, final
# criterion 3.8/0.6/4 (README section 1 "Result").
#   [BARO=iso|aniso] bash scripts/analyze_screen.sh summary [--dry-run]   checks, summaries, ONE perc cluster job
#   [BARO=iso|aniso] bash scripts/analyze_screen.sh verdict                after the cluster job: per-Ta classification
# BARO=aniso analyses the TAG=aniso set (runs/anneal_x0_aniso_T<Ta>_r*, submit_screen.sh BARO=aniso) and prefixes its
# outputs (screen_aniso_T<Ta>*.txt, screen_verdict_aniso.txt); default iso, with the original names. To compare the
# two: rate_compare.py screen_T<Ta>_clusters.txt screen_aniso_T<Ta>_clusters.txt (iso vs aniso rate ratio), and
# recryst_summary.py on both sets for t50.
# Only the Ta that were screened (runs/anneal_x0[_aniso]_T<Ta>_r* exist) are analysed. Stops on a Ta with fewer than
# 3 finished runs, or with a criterion, barostat, XSTOP or final step that differs from the plan (FORCE=1 ->
# warning).
set -uo pipefail
ROOT=$(realpath "$(dirname "$(realpath "$0")")/../..")
cd "${RECRYST:-$ROOT/recryst}"                 # RECRYST: another run tree (tests)
PY=${PY:-$ROOT/env/cgst-ana/bin/python}
die() { echo "STOPPED: $*" >&2; exit 1; }
check() { [ "${FORCE:-0}" = 1 ] && { echo "WARNING (FORCE=1): $*"; return; }; die "$*"; }
STAGE=${1:?summary or verdict}; DRY=0; [ "${2:-}" = "--dry-run" ] && DRY=1
BARO=${BARO:-iso}
case $BARO in iso) TAGP="" ;; aniso) TAGP="_aniso" ;; *) die "BARO must be iso or aniso, not '$BARO'" ;; esac
R=anneal_x0${TAGP}                          # run-name stem of this set; outputs carry the same ${TAGP}
Q="--q-rc 3.8 --q-thr 0.6 --q-nmin 4"
# calibrate.out at 3.8/0.6/4: x0's own crystal reference, --nucleated-size, XSTOP, and the x0 glass xfracGST at Ta.
# Checked against calib/calibrate.out (--choose 3.8 0.6 4, commit 5cfeee0).
declare -A XC=( [500]=0.950 [550]=0.951 [600]=0.950 [650]=0.948 [700]=0.947 )
declare -A NUC=( [500]=230 [550]=250 [600]=260 [650]=210 [700]=130 )
declare -A XSTOP=( [500]=0.75 [550]=0.73 [600]=0.72 [650]=0.70 [700]=0.68 )
declare -A GLASS=( [500]=0.086 [550]=0.090 [600]=0.076 [650]=0.064 [700]=0.048 )
TAS=$(for T in 500 550 600 650 700; do compgen -G "runs/${R}_T${T}_r*" > /dev/null && echo $T; done)
[ -n "$TAS" ] || die "no screening runs (runs/${R}_T<Ta>_r*)"

if [ $STAGE = summary ]; then
    # 0. Per Ta: 3 finished runs, final criterion, the planned XSTOP and final step (5 ns at 2 fs).
    for T in $TAS; do
        d=$(ls runs/${R}_T${T}_r*/anneal_done.txt 2>/dev/null | wc -l)
        [ $d -ge 3 ] || check "T$T: only $d of 3 finished"
        crit=$(cat runs/${R}_T${T}_r*/hold_start.txt | awk '{print $4, $6, $8}' | sort -u)
        [ "$crit" = "3.8 0.6 4" ] || check "T$T criteria: $(echo $crit)"
        want="(stop at xfracGST > ${XSTOP[$T]} or step $(( 5000 + 50 * (T - 300) + 2500000 )))"
        stops=$(grep -ho '(stop at.*)' runs/${R}_T${T}_r*/anneal_done.txt | sort -u)
        [ "$stops" = "$want" ] || check "T$T: $(echo $stops), expected $want"
        for l in runs/${R}_T${T}_r*/log.anneal.1; do   # substituted fix npt line: ' iso 0.0 0.0' or ' aniso 0.0 0.0'
            if [ $BARO = aniso ]; then grep -q ' aniso 0.0 0.0' $l && ! grep -q ' iso 0.0 0.0' $l
            else grep -q ' iso 0.0 0.0' $l && ! grep -q ' aniso 0.0 0.0' $l; fi || check "$l: barostat is not $BARO"
        done
        echo "T$T: $d finished, criterion $crit, $stops"
    done
    grep -l 'stopping the chain' slurm-anneal-*.out 2>/dev/null && check "a chain stopped for no progress (above)"

    # 1. Fraction curves per Ta, x0's own x_c (light: anneal.dat/stress.dat only).
    for T in $TAS; do
        $PY $ROOT/analysis/recryst_summary.py --x-crystal ${XC[$T]} runs/${R}_T${T}_r* > screen${TAGP}_T${T}.txt
    done

    # 2. Clusters, t_nuc, J_surv, MFPT: every frame -> ONE perc job for all screened Ta (values expanded here).
    cmds=""
    for T in $TAS; do
        cmds+="$PY $ROOT/analysis/recryst_summary.py --x-crystal ${XC[$T]} --clusters --nucleated-size ${NUC[$T]} $Q"
        cmds+=" runs/${R}_T${T}_r* > screen${TAGP}_T${T}_clusters.txt 2>&1; "
    done
    echo "$cmds" | tr ';' '\n' | sed '/^ *$/d'
    [ $DRY = 1 ] || sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1 --cpus-per-task=4 --mem=32G \
        -t 04:00:00 -J cgst-screen${TAGP}-cl -o slurm-screen${TAGP}-clusters-%j.out --wrap "$cmds"
elif [ $STAGE = verdict ]; then
    # 3. Per Ta, from the cluster output's per-run rows and nucleation line:
    #    TOO HOT  any run with x_a > glass + 0.05, t_nuc < 20 ps, or t_inc < 50 ps; or n_base >= --nucleated-size
    #             (it crystallized during the heating, or the glass already holds a nucleus-sized cluster)
    #    TOO COLD no run nucleated within 5 ns
    #    USABLE   otherwise; also reports how many of 3 nucleated and n_base / --nucleated-size (> 0.5: aging)
    for T in $TAS; do
        f=screen${TAGP}_T${T}_clusters.txt; [ -e $f ] || die "$f missing (cluster job not run or not finished)"
        grep -q "^${R}_T${T} .*nucleation:" $f || check "$f: no nucleation line"
        awk -v T=$T -v g=${GLASS[$T]} -v N=${NUC[$T]} '
            $1 ~ /_r[0-9]+$/ { delete v; for (i = 2; i < NF; i += 2) v[$i] = $(i + 1); n++
                               if (v["t_nuc"] != "nan") { k++; if (v["t_nuc"] + 0 < 20) hot = hot " t_nuc<20ps:" $1 }
                               if (v["x_a"] + 0 > g + 0.05) hot = hot " x_a>glass+0.05:" $1
                               if (v["t_inc"] != "nan" && v["t_inc"] + 0 < 50) hot = hot " t_inc<50ps:" $1
                               if (v["sdev_z"] != "nan" && v["sdev_z"] + 0 > 5 && v["t50"] != "nan") st = st " " $1 }
            $2 == "nucleation:" { for (i = 3; i < NF; i += 2) if ($i == "n_base") nb = $(i + 1) }
            END { if (nb + 0 >= N) hot = hot " n_base>=N"
                  verdict = hot != "" ? "TOO HOT" : (k == 0 ? "TOO COLD" : "USABLE")
                  printf "T%s: %-8s nucleated %d of %d; n_base %s / N %d (%.2f)%s%s\n", T, verdict, k, n, nb, N,
                         nb / N, (hot != "" ? ";" hot : ""), (st != "" ? "; sdev_z>5:" st : "") }' $f
    done | tee screen_verdict${TAGP}.txt
    # Suggestion only (the production Ta is the user's call at the README review checkpoint): the hottest USABLE Ta,
    # since C is expected to slow nucleation and x0 nucleating early leaves the C-rich cells time inside 5 ns. It must
    # also pass the production script's ramp-Tx check (scripts/submit_production.sh).
    awk '{ t = substr($1, 2, length($1) - 2) + 0 }
         $2 == "USABLE" { if (t > best) best = t }
         $2 == "TOO" && $3 == "COLD" { if (t > cold) cold = t }
         $2 == "TOO" && $3 == "HOT" { if (!hot || t < hot) hot = t }
         END { if (best) print "hottest USABLE Ta: " best " K (suggestion; check n_base ratio and sdev_z above)"
               else if (cold && hot && cold < hot) print "no USABLE Ta: " cold " K too cold, " hot " K too hot -> screen between them"
               else if (hot) print "no USABLE Ta: all too hot (coldest " hot " K) -> screen colder"
               else print "no USABLE Ta: all too cold (hottest " cold " K) -> a hotter Ta below Tx, or a longer MAX_NS" }' \
        screen_verdict${TAGP}.txt
else
    die "stage must be summary or verdict"
fi
# Notes: MFPT n_star / tau_J will mostly be NaN with 3 replicas, and J_surv from 3 runs is +-58% at best: screening
# picks Ta, it does not measure rates. In the clusters files, the largest cluster should jump from glass-like (~100) to
# far above N within a few hundred ps around t_nuc (one growing nucleus), not drift across N.
