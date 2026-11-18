# Shared setup for the recryst workflow scripts (sourced, not run). After sourcing:
#   ROOT, MODEL_ID      project root; the model (common/model.sh)
#   MODEL_RE            MODEL_ID|MODEL_ALIASES, for checking the model file a LAMMPS log names
#   cwd = RECRYST       recryst/ (or $RECRYST, a fake tree for tests)
#   RUNS, RESULTS       runs/$MODEL_ID and results/$MODEL_ID, relative to recryst/ (RESULTS is created)
#   PY                  the cgst-ana python (or $PY)
#   params              everything in recryst/params/$MODEL_ID.sh and its calib_params.sh (criterion, NUC, XC_*, GLASS_*,
#                       XSTOP, X_END, TX_GUARD, BARO, RUNTAG, TAS, NREP, MAX_NS, ...)
#   CELLS_ALL, CI       the composition order of submit_anneal.sh / submit_ramp.sh and each cell's index in it
#   die, check          stop; stop unless FORCE=1 (then warn)
#   n_end TA            the final step of a MAX_NS hold at TA (dt 2 fs; 10 ps at 300 K + 10 K/ps heat in in.anneal)
#   check_anneal_set CELL TA RUN...  the checks every analysis repeats on a finished anneal set (see below)
#   header              '#' lines naming the model, criterion and end point, for the top of every output file
# Stops when recryst/params/$MODEL_ID.sh or the calibration (calib_params.sh) is missing: every number the scripts use comes
# from those two files, so no script carries a model's values.
ROOT=$(realpath "$(dirname "${BASH_SOURCE[0]}")/../..")
source "$ROOT/common/model.sh"
MODEL_RE=$MODEL_ID${MODEL_ALIASES:+|${MODEL_ALIASES// /|}}   # the model and its earlier names, as logs may name them
cd "${RECRYST:-$ROOT/recryst}"
PY=${PY:-$ROOT/env/cgst-ana/bin/python}
die() { echo "STOPPED: $*" >&2; exit 1; }
check() { [ "${FORCE:-0}" = 1 ] && { echo "WARNING (FORCE=1): $*"; return 0; }; die "$*"; }
[ -e "$ROOT/recryst/params/$MODEL_ID.sh" ] || die "no recryst/params/$MODEL_ID.sh (copy recryst/params/nequip_no_zbl.sh and set every value, RUNBOOK.md)"
[ -e "$ROOT/meltquench/params/$MODEL_ID.sh" ] || die "no meltquench/params/$MODEL_ID.sh (the glasses' QRATE)"
source "$ROOT/recryst/params/$MODEL_ID.sh"
[ -n "${Q_ARGS:-}" ] || die "no recryst/calib/$MODEL_ID/calib_params.sh: run the calibration first (RUNBOOK.md)"
RUNS=runs/$MODEL_ID
RESULTS=results/$MODEL_ID
mkdir -p "$RESULTS"
CELLS_ALL=(x0 x1 x2p5 x5 x10)
declare -A CI=( [x0]=0 [x1]=1 [x2p5]=2 [x5]=3 [x10]=4 )
STEM=${RUNTAG:+_$RUNTAG}                    # anneal_<cell>${STEM}_T<Ta>_r<rep>

n_end() { echo $(( 5000 + 50 * ($1 - 300) + MAX_NS * 500000 )); }

header() {
    echo "# MODEL_ID $MODEL_ID, criterion $Q_RC/$Q_THR/$Q_NMIN, XSTOP $XSTOP, X_END $X_END, BARO $BARO, MAX_NS $MAX_NS"
}

# check_anneal_set CELL TA RUN...: every run finished, with the calibrated criterion (hold_start.txt), one halt line for
# the set with XSTOP >= X_END and the MAX_NS final step, the barostat BARO (substituted fix npt line of log.anneal.1),
# and the model MODEL_ID (substituted pair_coeff line). Prints one line per set; check() on every mismatch.
check_anneal_set() {
    local c=$1 T=$2; shift 2
    local n=$# d=0 r crit stops xs l
    for r in "$@"; do [ -e $r/anneal_done.txt ] && d=$((d + 1)); done
    [ $d = $n ] || check "$c T$T: only $d of $n finished"
    crit=$(cat "${@/%//hold_start.txt}" 2>/dev/null | awk '{print $4, $6, $8}' | sort -u)
    [ "$crit" = "$Q_RC $Q_THR $Q_NMIN" ] || check "$c T$T criteria: $(echo $crit), expected $Q_RC $Q_THR $Q_NMIN"
    stops=$(cat "${@/%//anneal_done.txt}" 2>/dev/null | grep -o '(stop at.*)' | sort -u)
    [ $(echo "$stops" | wc -l) = 1 ] || check "$c T$T: runs differ: $(echo $stops)"
    echo "$stops" | grep -q "or step $(n_end $T))$" || check "$c T$T: not a $MAX_NS ns hold: $stops"
    xs=$(echo "$stops" | head -1 | sed 's/.*> \([0-9.]*\) or.*/\1/')
    awk -v x="$xs" -v e=$X_END 'BEGIN { exit !(x + 0 >= e) }' || check "$c T$T: XSTOP $xs below X_END $X_END"
    for r in "$@"; do
        l=$r/log.anneal.1
        [ -e $l ] || { check "$l missing"; continue; }
        if [ $BARO = aniso ]; then grep -q ' aniso 0.0 0.0' $l && ! grep -q ' iso 0.0 0.0' $l
        else grep -q ' iso 0.0 0.0' $l && ! grep -q ' aniso 0.0 0.0' $l; fi || check "$l: barostat is not $BARO"
        grep -Eq "^pair_coeff +\* \* \S*/($MODEL_RE)(\.[GNK])?\.nequip\.pt2 " $l || check "$l: model is not $MODEL_ID"
    done
    echo "$c T$T: $d of $n finished, criterion $crit, $stops, $BARO, $MODEL_ID"
}
