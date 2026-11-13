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
# Compile the checkpoint of the current model (common/model.sh: MODEL_ID, CKPT) for pair_allegro on this node.
# Run once per node type for every new MODEL_ID (RUNBOOK.md, Part 0): AOT host code runs only on the CPU type it was
# compiled on (common/defaults.sh).
# Usage: sbatch -p <partition> compile_model.sh <output.nequip.pt2>   (from models/; output models/$MODEL_ID[.G|.N].nequip.pt2)
#
# nequip-compile must run from the training folder: it loads a sample frame through the checkpoint's relative
# dataset path (../../CGST/cgst_train_paw.xyz), which only resolves from there.
module load cuda/12.6.0
OUT=$(realpath -m "${1:?output path required}")
source "${SLURM_SUBMIT_DIR:-$(dirname "$(realpath "$0")")}/../common/model.sh"   # MODEL_ID, CKPT, MODEL_SRC, TRAIN_DIR, SIF
echo "compiling $MODEL_ID: $CKPT"
export NEQUIP_FLOAT64_MODEL_TOL=1e-10
cd $TRAIN_DIR
apptainer exec --nv --bind /depot,/scratch --env PYTHONPATH=$MODEL_SRC/nequip:$MODEL_SRC/allegro $SIF \
    nequip-compile $CKPT $OUT --mode aotinductor --device cuda --target pair_allegro
sha256sum $OUT
