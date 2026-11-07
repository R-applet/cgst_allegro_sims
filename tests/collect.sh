#!/bin/bash
# Print every test's machine-written verdict (tests/**/RESULT.txt) with the Slurm job that wrote it, so the verdict
# lines in tests/RESULTS.md can be checked against (or copied from) this output instead of being retyped.
# The job ID comes from the newest slurm-*.out next to the RESULT.txt ("-" if there is none).
# Usage: tests/collect.sh
cd "$(dirname "$0")"
for r in $(find . -name RESULT.txt | sort); do
    d=$(dirname "$r")
    job=$(ls -t "$d"/slurm-*.out 2>/dev/null | head -1 | sed -E 's/.*slurm-([0-9_]+)\.out/\1/')
    echo "== ${d#./}  (job ${job:--}, $(date -r "$r" '+%Y-%m-%d %H:%M'))"
    cat "$r"
done
