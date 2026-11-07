#!/bin/bash
# Tests 1d/1e: submit one benchmark job per (partition [node type], GPU count, analysis on/off). Run from tests/scaling/.
# Results: python3 summarize.py
set -euo pipefail
cd "$(dirname "$0")"
# optional: ./submit_all.sh <tag-glob> to (re)submit only matching runs, e.g. "a30_g1*"
ONLY=${1:-*}
submit () {   # partition ngpu ana cpus_per_task [extra sbatch args]; env ACCT (default strachan), NODE (tag suffix)
    local p=$1 n=$2 a=$3 c=$4 tag=${1}${NODE:+_$NODE}_g${2}_ana${3}; shift 4
    [[ $tag == $ONLY ]] || return 0
    sbatch -A ${ACCT:-strachan} --qos=normal -p $p -N1 --gpus-per-node=$n --ntasks-per-node=$n --cpus-per-task=$c \
        --mem=32G -t 01:00:00 "$@" -J cgst-bench-$tag -o slurm-$tag.out \
        --wrap "cd $PWD && ../../common/run_lmp.sh $n -in in.bench -log log.$tag -var ana $a -var tag $tag"
}
for n in 1 2; do submit a30 $n 1 4; done   # no 3-GPU run: the group cap (6 A30s, 4 held long-term) never allows 3
submit a30 2 0 4                       # 1e: analysis overhead (compare with a30_g2_ana1)
for n in 1 2; do submit a100-80gb $n 1 8 --constraint=I; done   # k-nodes: Illegal instruction
# perc account: 10 A100-40GB. Each node type is tested separately (the container crashed on an a100-80gb k-node).
for n in 1 2; do ACCT=perc NODE=G submit a100-40gb $n 1 8 --constraint=G; done   # gilbreth-g: 2 GPUs/node
for n in 1 2 4; do ACCT=perc NODE=N submit a100-40gb $n 1 8 --constraint=N; done # gilbreth-n: 4 GPUs/node
ACCT=perc NODE=N submit a100-40gb 2 0 8 --constraint=N                         # 1e on A100 (compare with _g2_ana1)
