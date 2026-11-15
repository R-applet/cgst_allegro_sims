# The potential this project runs with, in one place. Sourced (not executed) by common/defaults.sh,
# common/run_lmp.sh, models/compile_model.sh and the tests; Python tools read the exported variables.
# To add a model (RUNBOOK.md, A): add a block below with its checkpoint and sources, compile
# models/$MODEL_ID{,.G,.N,.K}.nequip.pt2 (one per node type, common/defaults.sh), and register it in
# models/provenance.md. Every run and result directory is named by MODEL_ID (<study>/runs/$MODEL_ID/,
# <study>/results/$MODEL_ID/), so runs of different models never share a directory. Select another registered model
# for one shell or job with MODEL_ID=<id> (e.g. MODEL_ID=run5_ep301 for the archived model's tools).
#   MODEL_ID    name of the model; also the stem of the compiled files in models/
#   CKPT        training checkpoint (eager model: tests/model_check, stress_parity, am_eos; analysis/latent_features.py)
#   MODEL_SRC   modified nequip/allegro sources put on PYTHONPATH to compile and to load CKPT; empty when the
#               container's own nequip/allegro are the versions the model was trained with
#   MODEL_PYTHONPATH  derived from MODEL_SRC (empty without it); scripts pass it to apptainer as PYTHONPATH
#   TRAIN_DIR   folder nequip-compile must run from (the checkpoint's relative dataset path resolves only there)
#   DT          production timestep (ps) for this model, set by tests/dt (an environment DT overrides it)
#   SIF         LAMMPS + libtorch container that runs the compiled model (the compile must use the same libtorch)
#   TESTSET     held-out DFT test set (tests/model_check, stress_parity, glass_relax)
#   DFT_TRAIN   DFT training xyz folder (tests/am_eos, tests/dft_glass)
MODEL_ID=${MODEL_ID:-nozbl_paw}
# Values exported by an earlier source for another model must not leak into this one (CKPT=${CKPT:-...} would keep
# them); environment overrides still apply to the model they were set for.
if [ -n "${MODEL_LOADED:-}" ] && [ "$MODEL_LOADED" != "$MODEL_ID" ]; then
    unset CKPT TRAIN_DIR MODEL_SRC MODEL_PYTHONPATH DT
fi
MODEL_LOADED=$MODEL_ID
_models_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../models" && pwd)
case $MODEL_ID in
    run5_ep301)     # archived (tag run5_ep301-final): Allegro with per-pair ZBL, Rushik's modified sources
        MODEL_SRC=${MODEL_SRC-/depot/prism/data/rushik/zbl_updated}
        TRAIN_DIR=${TRAIN_DIR:-$MODEL_SRC/rushik_zbl_super_short}
        CKPT=${CKPT:-$TRAIN_DIR/md_meltquench/run5_ep301.ckpt}
        _dt=0.002   # tests/RESULTS.md 1c
        ;;
    nozbl_paw)      # Allegro without ZBL, PAW data; trained with stock nequip 0.17.1 / allegro 0.8.2 = the container's
        MODEL_SRC=${MODEL_SRC-}
        TRAIN_DIR=${TRAIN_DIR:-/depot/prism/data/rushik/CGST/nequip_no_zbl}
        CKPT=${CKPT:-$_models_dir/nozbl_paw.ckpt}  # local copy of outputs/2026-11-05/19-04-55/best.ckpt (provenance.md)
        _dt=0.002   # tests/dt job 12358691: 2 fs passes (tests/results/nozbl_paw/RESULTS.md)
        ;;
    *)  # a new model: give its paths here (or in the environment) before running anything
        : "${CKPT:?common/model.sh: set CKPT and TRAIN_DIR (and MODEL_SRC if needed) for MODEL_ID=$MODEL_ID}"
        : "${TRAIN_DIR:?common/model.sh: set TRAIN_DIR for MODEL_ID=$MODEL_ID}"
        MODEL_SRC=${MODEL_SRC-}
        _dt=0.002
        ;;
esac
DT=${DT:-$_dt}
unset _dt _models_dir
MODEL_PYTHONPATH=${MODEL_SRC:+$MODEL_SRC/nequip:$MODEL_SRC/allegro}
SIF=${SIF:-/depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif}
TESTSET=${TESTSET:-/depot/prism/data/rushik/CGST/cgst_test_paw.xyz}
DFT_TRAIN=${DFT_TRAIN:-/depot/prism/data/rapplet/cgst-vasp-data/xyz_files/train}
export MODEL_ID MODEL_LOADED MODEL_SRC MODEL_PYTHONPATH TRAIN_DIR CKPT DT SIF TESTSET DFT_TRAIN
