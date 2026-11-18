#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -t 00:45:00
#SBATCH --job-name=cgst-modelcheck
# Test 1b: compiled model (LAMMPS) vs training checkpoint (nequip, Python) on DFT test-set frames.
# A model trained with modified nequip/allegro (MODEL_SRC in common/model.sh, e.g. per-pair ZBL cutoffs the
# container's nequip lacks) gets them on PYTHONPATH (MODEL_PYTHONPATH); otherwise the container's own are used.
cd $SLURM_SUBMIT_DIR
module load cuda/12.6.0
source ../../common/defaults.sh             # MODEL; from common/model.sh: SIF, MODEL_SRC, CKPT, TESTSET (exported)
export NEQUIP_FLOAT64_MODEL_TOL=1e-10
apptainer exec --nv --bind /depot,/scratch --env PYTHONPATH=$MODEL_PYTHONPATH $SIF \
    python model_check.py prepare || exit 1
../../common/run_lmp.sh 1 -in in.model_check -log log.model_check -var frames "$(cat frames.txt)" -var model $MODEL || exit 1
apptainer exec --bind /depot,/scratch $SIF python model_check.py compare | tee RESULT.txt
