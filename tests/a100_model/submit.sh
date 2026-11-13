#!/bin/bash -l
#SBATCH -A perc
#SBATCH --qos=normal
#SBATCH --partition=a100-40gb
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 01:00:00
#SBATCH --job-name=cgst-a100model
# Hypothesis: the production model (compiled on an A30 b-node) dies with 'Illegal instruction' in
# AOTIModelContainerRunnerCuda on A100 nodes because AOTInductor targeted the compile node's CPU.
# Test, per node type (sbatch --constraint=G|N --export=ALL,NODE=G|N submit.sh):
#   1. record this node's CPU model and flags (cpu_$NODE.txt; compare with an A30 b-node by hand)
#   2. recompile the checkpoint here (models/compile_model.sh) -> ${MODEL_ID}.$NODE.nequip.pt2
#   3. energies on the model_check frames vs the production model's (tests/model_check/lammps_energies.txt)
#   4. 1-GPU bench (tests/scaling/in.bench) with the recompiled model
# Verdict -> RESULT_$NODE.txt
cd $SLURM_SUBMIT_DIR
ROOT=$(realpath ../..)
MC=$ROOT/tests/model_check
NODE=${NODE:?set NODE=G or N}
{ hostname; lscpu | grep -E "Model name|Flags" | cut -c1-2000; } > cpu_$NODE.txt
source $ROOT/common/model.sh                # MODEL_ID
bash $ROOT/models/compile_model.sh $PWD/${MODEL_ID}.$NODE.nequip.pt2 > compile_$NODE.log 2>&1 \
    || { echo "compile FAILED (compile_$NODE.log)" | tee RESULT_$NODE.txt; exit 1; }
mkdir -p frames_$NODE && ln -sf $MC/frame_*.data frames_$NODE/
(cd frames_$NODE && $ROOT/common/run_lmp.sh 1 -in $MC/in.model_check -log log.model_check -var root $ROOT \
    -var model $SLURM_SUBMIT_DIR/${MODEL_ID}.$NODE.nequip.pt2 -var frames "$(cat $MC/frames.txt)" > screen.txt 2>&1) \
    || echo "FAILED energies ($NODE): frames_$NODE/screen.txt" >> failures_$NODE.txt
$ROOT/common/run_lmp.sh 1 -in ../scaling/in.bench -log log.bench_$NODE -var ana 1 -var tag a100_$NODE \
    -var model $PWD/${MODEL_ID}.$NODE.nequip.pt2 > screen_bench_$NODE.txt 2>&1 \
    || echo "FAILED bench ($NODE): screen_bench_$NODE.txt" >> failures_$NODE.txt
{
    head -2 cpu_$NODE.txt | cut -c1-120
    cat failures_$NODE.txt 2>/dev/null
    python3 $MC/compare_energies.py $MC/lammps_energies.txt frames_$NODE/lammps_energies.txt
    p=$(grep "^Performance:" log.bench_$NODE 2>/dev/null | sed -n 2p); echo "bench 1 GPU: ${p:-no timed run}"
} | tee RESULT_$NODE.txt
