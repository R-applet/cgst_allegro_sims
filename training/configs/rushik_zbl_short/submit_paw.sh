#!/bin/sh -l
#SBATCH -A strachan          
#SBATCH --qos=normal         
#SBATCH --partition=a100-80gb    
#SBATCH --nodes=1
#SBATCH --gpus-per-node=2
#SBATCH --mem=240G
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=32
#SBATCH -t 3-00:00:00
#SBATCH --job-name=rushik_zbl_short_paw

# module load conda
# conda activate allegro
source /depot/prism/data/rushik/zbl_updated/venv/bin/activate
# Critical distributed training environment variables
export NCCL_DEBUG=INFO
# Try different network interface options
export NCCL_SOCKET_IFNAME=^docker0,lo
# Alternative: let NCCL auto-detect
# unset NCCL_SOCKET_IFNAME

export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC=3600
export NCCL_TIMEOUT=1800
export CUDA_LAUNCH_BLOCKING=1

# Prevent file I/O conflicts
export HDF5_USE_FILE_LOCKING=FALSE
export PYTHONUNBUFFERED=1

# Fix PyTorch distributed issues
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1  # Updated variable name
export TORCH_DISTRIBUTED_DEBUG=DETAIL

# Disable problematic NCCL optimizations for debugging
export NCCL_IB_DISABLE=1
export NCCL_P2P_DISABLE=1
export TORCH_DYNAMO_DISABLE_AGGRESSIVE_RECOMPILATION=1
export TORCH_COMPILE_DEBUG=1

srun nequip-train -cn config_paw.yaml

# wandb agent <enter what you get when you run wandb sweep sweeps.yaml>

