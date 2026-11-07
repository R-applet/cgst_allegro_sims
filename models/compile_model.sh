#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 01:00:00
#SBATCH --job-name=cgst-compile
# Recompile run5_ep301.ckpt for pair_allegro on the GPU architecture of the allocated node.
# Only needed for a non-sm_80 GPU; the copy in models/ already serves A30 and A100.
# Usage: sbatch -p <partition> compile_model.sh <output.nequip.pt2>   (from models/)
#
# nequip-compile must run from the training folder: it loads a sample frame through the checkpoint's relative
# dataset path (../../CGST/cgst_train_paw.xyz), which only resolves from there.
module load cuda/12.6.0
OUT=$(realpath -m "${1:?output path required}")
SIF=/depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif
SRC=/depot/prism/data/rushik/zbl_updated
CKPT=$SRC/rushik_zbl_super_short/md_meltquench/run5_ep301.ckpt
export NEQUIP_FLOAT64_MODEL_TOL=1e-10
cd $SRC/rushik_zbl_super_short
apptainer exec --nv --bind /depot,/scratch --env PYTHONPATH=$SRC/nequip:$SRC/allegro $SIF \
    nequip-compile $CKPT $OUT --mode aotinductor --device cuda --target pair_allegro
sha256sum $OUT
