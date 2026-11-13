#!/bin/bash -l
#SBATCH -A strachan
#SBATCH --qos=normal
#SBATCH --partition=a30
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 01:00:00
#SBATCH --job-name=cgst-compilechk
# Check that models/compile_model.sh reproduces the production model: recompile into this directory, then evaluate
# the model_check frames with both compiled files, each in its own directory (frames_prod/, frames_recompiled/;
# frames are symlinked, nothing is written to tests/model_check).
# Pass: energies agree to 1e-6 eV/atom. Verdict -> RESULT.txt
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
MC=$ROOT/tests/model_check
source $ROOT/common/defaults.sh             # MODEL_ID; MODEL = the production file for this node
bash $ROOT/models/compile_model.sh $PWD/recompiled.nequip.pt2 > compile.log 2>&1 \
    || { echo "compile FAILED" | tee RESULT.txt; tail compile.log; exit 1; }
for m in prod recompiled; do
    [ $m = prod ] && model=$MODEL || model=$PWD/recompiled.nequip.pt2
    mkdir -p frames_$m && ln -sf $MC/frame_*.data frames_$m/
    (cd frames_$m && $ROOT/common/run_lmp.sh 1 -in $MC/in.model_check -log log.model_check -var root $ROOT \
        -var model $model -var frames "$(cat $MC/frames.txt)" > screen.txt 2>&1) || echo "FAILED: $m (see frames_$m/screen.txt)"
done
{
    python3 $MC/compare_energies.py frames_prod/lammps_energies.txt frames_recompiled/lammps_energies.txt
    sha256sum recompiled.nequip.pt2 $MODEL
} | tee RESULT.txt
