#!/bin/bash -l
#SBATCH -A perc
#SBATCH --qos=normal
#SBATCH --partition=a100-40gb
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH -t 00:20:00
#SBATCH --job-name=cgst-modelsel
# End-to-end check of the per-node model selection in common/defaults.sh: resolve MODEL on this node, then evaluate
# the model_check frames with it (in frames_<host>/) and compare energies with the production model's.
#   sbatch --constraint=G submit.sh ; sbatch --constraint=N submit.sh      Verdict -> RESULT_<host>.txt
set -euo pipefail
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
MC=$ROOT/tests/model_check
source $ROOT/common/defaults.sh
H=$(hostname -s)
mkdir -p frames_$H && ln -sf $MC/frame_*.data frames_$H/
(cd frames_$H && $ROOT/common/run_lmp.sh 1 -in $MC/in.model_check -log log.model_check -var root $ROOT \
    -var model $MODEL -var frames "$(cat $MC/frames.txt)" > screen.txt 2>&1) || echo "LAMMPS FAILED (frames_$H/screen.txt)"
{ echo "$H: MODEL=$(basename $MODEL)"; python3 $MC/compare_energies.py $MC/lammps_energies.txt frames_$H/lammps_energies.txt; } \
    | tee RESULT_$H.txt
