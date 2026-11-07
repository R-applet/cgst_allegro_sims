#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH -t 01:00:00
#SBATCH --job-name=cgst-mqlogic
# Logic test of meltquench/in.meltquench: 1x1x1 x0 (461 atoms) and x10 (512) cells, every duration x0.1
# (tscale), dt = 1 fs.
# x0_gatefail: x0 with an unreachable MSD gate (gate_A2 1e9): the run must stop with exit 1 after the hold.
# Pass criteria: check.py (run at the end; writes RESULT.txt).
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
source $ROOT/common/defaults.sh             # MODEL (per node type); this test sets its own dt
rc=0
for run in x0 x10 x0_gatefail; do
    cell=${run%_gatefail}
    extra=()
    [ $run = x0_gatefail ] && extra=(-var gate_A2 1e9)
    rm -rf $run && mkdir $run && cd $run                # fresh directory: no outputs left from an earlier run
    status=0
    $ROOT/common/run_lmp.sh 1 -in $ROOT/meltquench/in.meltquench -log log.mq -var root $ROOT -var cell $cell \
        -var size 111 -var seed 12345 -var qrate 10 -var dt 0.001 -var tscale 0.1 -var model $MODEL "${extra[@]}" \
        || status=$?
    echo "$status" > exit_status.txt                    # check.py: 0 expected, except x0_gatefail (non-zero)
    cd ..
done
# verdict: checks the pass criteria above and runs both analysis scripts on the outputs -> RESULT.txt
$ROOT/env/cgst-ana/bin/python check.py || rc=1
exit $rc
