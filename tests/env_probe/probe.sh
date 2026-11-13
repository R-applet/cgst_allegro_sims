#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH -t 00:15:00
#SBATCH --job-name=cgst-probe
# Environment probe: GPU compute capability, the LAMMPS build of each container (lmp -h: version, packages, styles),
# and the container's torch/nequip versions. Writes lmp_help_<debug|stable>.txt and probe.txt here.
# The original probe (2026-11-06) ran these commands interactively inside `srun bash -lc "..."` on gilbreth-b006.
# Here lmp -h also runs inside an srun step: LAMMPS calls MPI_Init first, and a bare apptainer launch inside a batch
# job aborts there (tests/container, job 12235379).
cd $SLURM_SUBMIT_DIR
module load cuda/12.6.0
source ../../common/model.sh; D=$(dirname $SIF)
nvidia-smi --query-gpu=name,compute_cap --format=csv > probe.txt
for s in debug stable; do
    srun --ntasks=1 apptainer run --nv --bind /depot,/scratch $D/lammps_$s.sif -h > lmp_help_$s.txt 2>&1
done
apptainer exec --nv $D/lammps_debug.sif python -c 'import torch,nequip;print("debug",torch.__version__,nequip.__version__)' >> probe.txt
