#!/bin/bash
# Throughput and GPU memory at the 4x4x4 cell (x10, 32768 atoms) vs 3x3x3 (13824) for the current MODEL_ID, on perc
# A100-40GB: is 4x4x4 affordable for the melt-quench and recrystallization runs, and how many GPUs per run?
#   n-nodes (4 GPUs/node): 444 on 1, 2 and 4 GPUs; 333 on 1 GPU (this potential's cost at the old size)
#   g-node (2 GPUs/node):  444 on 1 GPU
# Each job samples nvidia-smi memory.used every 2 s (mem_<tag>.txt; peak per GPU = the memory needed).
# Usage, from tests/scaling: bash submit_size.sh [--dependency=afterok:<job>[:<job>]]   (after the model is compiled)
# Results: python3 summarize.py (Performance) and the max of each mem_<tag>.txt.
set -euo pipefail
cd "$(dirname "$0")"
DEP=${1:-}
source ../../common/model.sh                # MODEL_ID: tags carry it, so other potentials' logs are kept
run () {   # node ngpu size
    local node=$1 n=$2 size=$3 tag=${MODEL_ID}_s$3_$1_g$2
    ${SBATCH:-sbatch} -A perc --qos=normal -p a100-40gb --constraint=$node -N1 --gpus-per-node=$n --ntasks-per-node=$n \
        --cpus-per-task=8 --mem=64G -t 01:00:00 $DEP -J cgst-size-$tag -o slurm-$tag.out \
        --wrap "cd $PWD && source ../../common/defaults.sh && \
            { nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader -l 2 > mem_$tag.txt & } ; \
            NV=\$!; ../../common/run_lmp.sh $n -in in.bench -log log.$tag -var ana 1 -var size $size -var tag $tag \
            -var model \$MODEL; kill \$NV"
}
for n in 1 2 4; do run N $n 444; done
run N 1 333
run G 1 444
