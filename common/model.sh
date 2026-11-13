# The potential this project runs with, in one place. Sourced (not executed) by common/defaults.sh,
# common/run_lmp.sh, models/compile_model.sh and the tests; Python tools read the exported variables.
# To switch models (RUNBOOK.md, step 1): set MODEL_ID and add a block below with its checkpoint and sources, compile
# models/$MODEL_ID{,.G,.N}.nequip.pt2 (one per node type, common/defaults.sh), and document it in
# models/provenance.md. Every run and result directory is named by MODEL_ID (runs/$MODEL_ID/, results/$MODEL_ID/),
# so runs of different models never share a directory.
#   MODEL_ID    name of the model; also the stem of the compiled files in models/
#   CKPT        training checkpoint (eager model: tests/model_check, stress_parity, am_eos; analysis/latent_features.py)
#   MODEL_SRC   modified nequip/allegro sources, put on PYTHONPATH to compile and to load CKPT
#   TRAIN_DIR   folder nequip-compile must run from (the checkpoint's relative dataset path resolves only there)
#   SIF         LAMMPS + libtorch container that runs the compiled model (the compile must use the same libtorch)
#   TESTSET     held-out DFT test set (tests/model_check, stress_parity, glass_relax)
#   DFT_TRAIN   DFT training xyz folder (tests/am_eos, tests/dft_glass)
MODEL_ID=${MODEL_ID:-run5_ep301}
case $MODEL_ID in
    run5_ep301)
        MODEL_SRC=${MODEL_SRC:-/depot/prism/data/rushik/zbl_updated}
        TRAIN_DIR=${TRAIN_DIR:-$MODEL_SRC/rushik_zbl_super_short}
        CKPT=${CKPT:-$TRAIN_DIR/md_meltquench/run5_ep301.ckpt}
        ;;
    *)  # a new model: give its paths here (or in the environment) before running anything
        : "${CKPT:?common/model.sh: set CKPT (and MODEL_SRC, TRAIN_DIR) for MODEL_ID=$MODEL_ID}"
        : "${MODEL_SRC:?common/model.sh: set MODEL_SRC for MODEL_ID=$MODEL_ID}"
        : "${TRAIN_DIR:?common/model.sh: set TRAIN_DIR for MODEL_ID=$MODEL_ID}"
        ;;
esac
SIF=${SIF:-/depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif}
TESTSET=${TESTSET:-/depot/prism/data/rushik/CGST/cgst_test_paw.xyz}
DFT_TRAIN=${DFT_TRAIN:-/depot/prism/data/rapplet/cgst-vasp-data/xyz_files/train}
export MODEL_ID MODEL_SRC TRAIN_DIR CKPT SIF TESTSET DFT_TRAIN
