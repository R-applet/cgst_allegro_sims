# Production defaults, sourced (not executed) by the study submit scripts and the tests that need a compiled model.
# Override per job via the environment, e.g. sbatch --export=ALL,DT=0.001 ...
#   DT  timestep (ps), per model in common/model.sh (set by tests/dt for that model). Every run in a chain
#       (melt-quench -> ramp/anneal, and anneal resumes) must use the same DT.

#   MODEL_ID and the model's paths come from common/model.sh (sourced here).
#   MODEL  compiled model file models/$MODEL_ID[.G|.N].nequip.pt2 for the node this job runs on, resolved from the hostname when the job starts. An
#          AOT-compiled model's host code only runs on the CPU type it was compiled on; elsewhere it dies with
#          'Illegal instruction' in the model loader (tests/RESULTS.md, environment probe). All three files are the
#          same model (identical energies on the model_check frames), so a chain may switch node types, e.g. an
#          anneal resumed on another partition. Pass it to LAMMPS as -var model $MODEL. Override with MODEL=<file>.
#          Nodes with no compatible file abort here, before LAMMPS starts.
source "$(dirname "${BASH_SOURCE[0]}")/model.sh"
if [ -z "${MODEL:-}" ]; then
    _models=$(cd "$(dirname "${BASH_SOURCE[0]}")/../models" && pwd)
    case "$(hostname -s)" in
        gilbreth-b*) MODEL=$_models/$MODEL_ID.nequip.pt2 ;;      # a30 b-nodes (compiled there)
        gilbreth-d*) MODEL=$_models/$MODEL_ID.nequip.pt2 ;;      # a30 d-nodes (ran there: tests/RESULTS.md, 1d)
        gilbreth-g*) MODEL=$_models/$MODEL_ID.G.nequip.pt2 ;;    # a100-40gb g-nodes, AMD EPYC 7662
        gilbreth-n*) MODEL=$_models/$MODEL_ID.N.nequip.pt2 ;;    # a100-40gb n-nodes, AMD EPYC 7413
        gilbreth-k*) MODEL=$_models/$MODEL_ID.K.nequip.pt2 ;;    # a100-80gb k-nodes (alta account)
        *) echo "common/defaults.sh: no compiled model for node $(hostname -s); build one there with" \
                "models/compile_model.sh and add it here" >&2
           return 1 ;;
    esac
    unset _models
    [ -e "$MODEL" ] || { echo "common/defaults.sh: $MODEL does not exist (compile it: models/compile_model.sh)" >&2; return 1; }
fi
