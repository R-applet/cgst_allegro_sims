#!/bin/bash -l
#SBATCH -A perc
#SBATCH --qos=normal
#SBATCH --partition=a100-40gb
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -t 00:45:00
#SBATCH --job-name=cgst-eos
# Model vs DFT equations of state on the training EOS frames (eos_check.py). Eager checkpoint, so no AOT model file is
# involved and any sm_80 node works.
cd $SLURM_SUBMIT_DIR
module load cuda/12.6.0
S=/depot/prism/data/rushik/zbl_updated
export NEQUIP_FLOAT64_MODEL_TOL=1e-10
apptainer exec --nv --bind /depot,/scratch --env PYTHONPATH=$S/nequip:$S/allegro \
    /depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif python eos_check.py
