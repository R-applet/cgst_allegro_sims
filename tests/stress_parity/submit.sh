#!/bin/bash -l
#SBATCH -A perc
#SBATCH --qos=normal
#SBATCH --partition=a100-40gb
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -t 02:00:00
#SBATCH --job-name=cgst-stress
# Model vs DFT pressure on the held-out test set (stress_parity.py). Eager checkpoint, so no AOT model file is
# involved and any sm_80 node works.
cd $SLURM_SUBMIT_DIR
module load cuda/12.6.0
source ../../common/model.sh                # CKPT, MODEL_SRC, SIF, TESTSET, DFT_TRAIN (exported into the container)
export NEQUIP_FLOAT64_MODEL_TOL=1e-10
apptainer exec --nv --bind /depot,/scratch --env PYTHONPATH=$MODEL_PYTHONPATH \
    $SIF python stress_parity.py
