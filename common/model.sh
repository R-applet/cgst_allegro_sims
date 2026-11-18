# The potential this project runs with, in one place. Sourced (not executed) by common/defaults.sh,
# common/run_lmp.sh, models/compile_model.sh and the tests; Python tools read the exported variables.
# To add a model (RUNBOOK.md, A): add a block below with its checkpoint and sources, compile
# models/$MODEL_ID{,.G,.N,.K}.nequip.pt2 (one per node type, common/defaults.sh), and register it in
# models/provenance.md. Every run and result directory is named by MODEL_ID (<study>/runs/$MODEL_ID/,
# <study>/results/$MODEL_ID/), so runs of different models never share a directory. Select another registered model
# for one shell or job with MODEL_ID=<id> (e.g. MODEL_ID=nequip_zbl).
#   MODEL_ID    name of the model = its training folder (training/configs/<MODEL_ID>/); also the stem of the compiled
#               files in models/
#   MODEL_ALIASES  earlier names of the same model, accepted where tools check the model a LAMMPS log names
#   CKPT        training checkpoint, training/configs/<MODEL_ID>/best.ckpt (tracked) unless set (eager model:
#               tests/model_check, stress_parity, am_eos; analysis/latent_features.py)
#   MODEL_SRC   modified nequip/allegro sources put on PYTHONPATH to compile and to load CKPT; empty when the
#               container's own nequip/allegro are the versions the model was trained with
#   MODEL_PYTHONPATH  derived from MODEL_SRC (empty without it); scripts pass it to apptainer as PYTHONPATH
#   TRAIN_DIR   folder nequip-compile must run from (the checkpoint's relative dataset path resolves only there)
#   DT          production timestep (ps) for this model, set by tests/dt (an environment DT overrides it)
#   SIF         LAMMPS + libtorch container that runs the compiled model (the compile must use the same libtorch)
#   TESTSET     held-out DFT test set (tests/model_check, stress_parity, glass_relax)
#   DFT_TRAIN   DFT training xyz folder (tests/am_eos, tests/dft_glass)
#   DFT_PHASES  300 K DFT-MD cells and their RDF/ADF/VDOS outputs (phases/structures, phases/dft); not model-specific
MODEL_ID=${MODEL_ID:-nequip_no_zbl}
# Values exported by an earlier source for another model must not leak into this one (CKPT=${CKPT:-...} would keep
# them); environment overrides still apply to the model they were set for.
if [ -n "${MODEL_LOADED:-}" ] && [ "$MODEL_LOADED" != "$MODEL_ID" ]; then
    unset CKPT TRAIN_DIR MODEL_SRC MODEL_PYTHONPATH DT MODEL_ALIASES
fi
MODEL_LOADED=$MODEL_ID
_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MODEL_ALIASES=${MODEL_ALIASES-}
case $MODEL_ID in
    nequip_no_zbl)  # Allegro without ZBL; stock nequip 0.17.1 / allegro 0.8.2 = the container's. Named nozbl_paw until
                    # 2026-11-18 (same checkpoint and compiled files): logs and records written before then use that name
        MODEL_SRC=${MODEL_SRC-}
        TRAIN_DIR=${TRAIN_DIR:-/depot/prism/data/rushik/CGST/nequip_no_zbl}
        MODEL_ALIASES=nozbl_paw
        _dt=0.002   # tests/dt job 12358691: 2 fs passes (tests/results/nequip_no_zbl/RESULTS.md)
        ;;
    nequip_zbl)     # Allegro with ZBL for all pairs to r_max; stock nequip 0.17.1 / allegro 0.8.2 = the container's
        MODEL_SRC=${MODEL_SRC-}
        TRAIN_DIR=${TRAIN_DIR:-/depot/prism/data/rushik/CGST/nequip_zbl}
        _dt=0.002   # PROVISIONAL until tests/dt runs for this model
        ;;
    rushik_zbl_pairwise)  # Allegro with per-pair ZBL at the data edge; trained as rushik_zbl_dataedge with Rushik's
                    # modified nequip 0.18.0 / allegro 0.8.3 (MODEL_SRC), which the container's 0.17.1 lacks
        MODEL_SRC=${MODEL_SRC-/depot/prism/data/rushik/zbl_updated}
        TRAIN_DIR=${TRAIN_DIR:-$MODEL_SRC/rushik_zbl_dataedge}
        _dt=0.002   # PROVISIONAL until tests/dt runs for this model
        ;;
    *)  # a new model: give its paths here (or in the environment) before running anything
        : "${TRAIN_DIR:?common/model.sh: set TRAIN_DIR (and MODEL_SRC if needed) for MODEL_ID=$MODEL_ID}"
        MODEL_SRC=${MODEL_SRC-}
        _dt=0.002
        ;;
esac
CKPT=${CKPT:-$_root/training/configs/$MODEL_ID/best.ckpt}   # training/CHECKPOINTS.sha256
DT=${DT:-$_dt}
unset _dt _root
MODEL_PYTHONPATH=${MODEL_SRC:+$MODEL_SRC/nequip:$MODEL_SRC/allegro}
SIF=${SIF:-/depot/prism/data/rushik/lammps_wallegro/lammps_debug.sif}
TESTSET=${TESTSET:-/depot/prism/data/rushik/CGST/cgst_test_paw.xyz}
DFT_TRAIN=${DFT_TRAIN:-/depot/prism/data/rapplet/cgst-vasp-data/xyz_files/train}
DFT_PHASES=${DFT_PHASES:-/depot/prism/data/rapplet/CGST_ALLEGRO/AllegroMD/phases}
export MODEL_ID MODEL_ALIASES MODEL_LOADED MODEL_SRC MODEL_PYTHONPATH TRAIN_DIR CKPT DT SIF TESTSET DFT_TRAIN DFT_PHASES
