#!/bin/bash
# Print every test's machine-written verdict (tests/**/RESULT*.txt) with the Slurm job that wrote it, so the verdict
# lines in a model's RESULTS.md can be checked against (or copied from) this output instead of being retyped.
# The job ID comes from the newest slurm-*.out next to the file ("-" if there is none).
# Usage: tests/collect.sh                      print
#        tests/collect.sh --save MODEL_ID      also copy each file to tests/results/MODEL_ID/<test>[_<suffix>].txt,
#                                              with this listing as INDEX.txt. Tests rewrite their RESULT*.txt in
#                                              place, so save a model's results before testing the next model.
cd "$(dirname "$0")"
SAVE=""; [ "${1:-}" = "--save" ] && SAVE=results/${2:?--save needs a MODEL_ID}
[ -n "$SAVE" ] && mkdir -p "$SAVE"
for r in $(find . -path ./results -prune -o -name 'RESULT*.txt' -print | sort); do
    d=$(dirname "$r"); t=${d#./}
    job=$(ls -t "$d"/slurm-*.out 2>/dev/null | head -1 | sed -E 's/.*slurm-([0-9_]+)\.out/\1/')
    echo "== $t/$(basename $r)  (job ${job:--}, $(date -r "$r" '+%Y-%m-%d %H:%M'))"
    cat "$r"
    [ -n "$SAVE" ] && cp -p "$r" "$SAVE/${t//\//_}$(basename $r .txt | sed 's/^RESULT//').txt"
done | { [ -n "$SAVE" ] && tee "$SAVE/INDEX.txt" || cat; }
