#!/bin/bash -l
#SBATCH -A perc
#SBATCH --qos=normal
#SBATCH --partition=a100-40gb
#SBATCH --constraint=N
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 03:00:00
#SBATCH --job-name=cgst-glassrelax
# Check 1 after 1h: do DFT glasses (about 5.8 g/cc) collapse toward the model's 6.29 g/cc glass when relaxed with the
# model at NPT 300 K, 0 bar? Crystal frames are the control. Pinned to --constraint=N; the model is models/$MODEL_ID.N.nequip.pt2
# (common/defaults.sh). Verdict -> RESULT.txt (analyze.py)
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
module load cuda/12.6.0
source $ROOT/common/defaults.sh             # MODEL (this node); SIF, TESTSET from common/model.sh
apptainer exec --bind /depot,/scratch $SIF python prep.py || exit 1
$ROOT/common/run_lmp.sh 1 -in in.relax -log log.relax -var root $ROOT -var frames "$(cat frames.txt)" \
    -var model $MODEL > screen.txt 2>&1 || echo "LAMMPS FAILED (screen.txt)"
python3 analyze.py | tee RESULT.txt
apptainer exec --bind /depot,/scratch $SIF python to_xyz.py
