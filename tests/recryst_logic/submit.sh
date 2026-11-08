#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH -t 01:30:00
#SBATCH --job-name=cgst-rclogic
# Logic test of recryst/in.ramp and recryst/in.anneal on the 1x1x1 x0 sample (461 atoms) from tests/mq_logic
# (dt = 1 fs):
#   ramp_x0_h10_r1:    ramp at 10 K/ps (60 ps)
#   anneal_x0_T600_r1: anneal tscale 0.1, hold 10 ps (max_ns 0.1), then resume from the newest restart with
#                      max_ns 0.2, so anneal.dat and stress.dat continue to the new end
#   halt_x0:           anneal with xstop 0.0, so fix halt stops the hold at its first check; run with the
#                      anisotropic barostat (baro aniso) to exercise that path
#   continuation:      submit_anneal.sh submitted with its continuation's resource flags, sbatch --test-only
#   calib:             recryst/calib/in.calib on two C-containing references, the x10 glass from tests/mq_logic
#                      (300 K) and the minimized 1x1x1 x5 rocksalt (structures/111, 600 K), then calibrate.py on them;
#                      checks xfracGST (Ge/Sb/Te only) against a recount from the dumps
# Pass criteria: check.py (run at the end; writes RESULT.txt).
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
source $ROOT/common/defaults.sh             # MODEL (per node type); this test sets its own dt
SRC=$ROOT/tests/mq_logic/x0/amorphous_300K.data
L="$ROOT/common/run_lmp.sh 1"
common="-var root $ROOT -var cell x0 -var rep 1 -var src $SRC -var dt 0.001 -var model $MODEL"
rm -rf ramp_x0_h10_r1 anneal_x0_T600_r1 halt_x0 calib && mkdir ramp_x0_h10_r1 anneal_x0_T600_r1 halt_x0 calib
run() {   # run() <dir> <status file> <lammps args...>: run LAMMPS in <dir>, record its exit status, never abort
    local d=$1 f=$2; shift 2
    (cd $d && $L "$@") && echo 0 > $d/$f || echo $? > $d/$f
}
run ramp_x0_h10_r1 exit_status.txt -in $ROOT/recryst/in.ramp -log log.ramp $common -var seed 11 -var hrate 10
run anneal_x0_T600_r1 exit_status.1.txt -in $ROOT/recryst/in.anneal -log log.anneal.1 $common -var seed 12 \
    -var Ta 600 -var max_ns 0.1 -var tscale 0.1
if [ -e anneal_x0_T600_r1/anneal_done.txt ]; then
    rm anneal_x0_T600_r1/anneal_done.txt
    latest=$(cd anneal_x0_T600_r1 && ls anneal.*.restart | sort -t. -k2,2n | tail -1)
    run anneal_x0_T600_r1 exit_status.2.txt -in $ROOT/recryst/in.anneal -log log.anneal.2 $common -var seed 12 \
        -var Ta 600 -var max_ns 0.2 -var tscale 0.1 -var resume 1 -var rfile $latest
fi
run halt_x0 exit_status.txt -in $ROOT/recryst/in.anneal -log log.anneal $common -var seed 13 -var Ta 600 \
    -var max_ns 0.2 -var tscale 0.1 -var xstop 0.0 -var baro aniso
cal="-in $ROOT/recryst/calib/in.calib -var root $ROOT -var dt 0.001 -var model $MODEL"
run calib exit_status.amor.txt $cal -log log.amor -var src $ROOT/tests/mq_logic/x10/amorphous_300K.data -var T 300 \
    -var tag amor_x10_300K -var seed 14 -var minimize 0
run calib exit_status.crys.txt $cal -log log.crys -var src $ROOT/structures/111/x5.data -var T 600 \
    -var tag crys_x5_600K -var seed 15 -var minimize 1
(cd calib && $ROOT/env/cgst-ana/bin/python $ROOT/recryst/calib/calibrate.py --crystal crys_x5_600K.lammpstrj.gz \
    --amorphous amor_x10_300K.lammpstrj.gz > calibrate.out 2>&1) && echo 0 > calib/exit_status.calibrate.txt \
    || echo $? > calib/exit_status.calibrate.txt
# the continuation submission of recryst/submit_anneal.sh (same script, same inherited resource flags; no
# dependency), validated by Slurm without queueing anything
(cd $ROOT/recryst && sbatch --test-only --array=0 -A $SLURM_JOB_ACCOUNT -p $SLURM_JOB_PARTITION \
    --qos=$SLURM_JOB_QOS --gpus-per-node=$SLURM_GPUS_ON_NODE --ntasks-per-node=$SLURM_NTASKS_PER_NODE \
    --export=ALL,TA=600,CHAIN=2 submit_anneal.sh) > continuation_test.txt 2>&1 \
    && echo "exit 0" >> continuation_test.txt || echo "exit $?" >> continuation_test.txt
$ROOT/env/cgst-ana/bin/python check.py
