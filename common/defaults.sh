# Production defaults, sourced (not executed) by the Part 2/3 submit scripts and tests/density, tests/model_select.
# The Part 2/3 logic tests use only MODEL and set dt themselves. Override per job via the environment,
# e.g. sbatch --export=ALL,DT=0.001 ...  Change a value here only together with the test that justifies it.
#   DT  timestep (ps). 2 fs passes NVE energy conservation in the hottest, most C-rich state (tests/RESULTS.md, 1c).
#       Every run in a chain (melt-quench -> ramp/anneal, and anneal resumes) must use the same DT.
DT=${DT:-0.002}

#   MODEL  compiled model file for the node this job runs on, resolved from the hostname when the job starts. An
#          AOT-compiled model's host code only runs on the CPU type it was compiled on; elsewhere it dies with
#          'Illegal instruction' in the model loader (tests/RESULTS.md, environment probe). All three files are the
#          same model (identical energies on the model_check frames), so a chain may switch node types, e.g. an
#          anneal resumed on another partition. Pass it to LAMMPS as -var model $MODEL. Override with MODEL=<file>.
#          Nodes with no compatible file abort here, before LAMMPS starts.
if [ -z "${MODEL:-}" ]; then
    _models=$(cd "$(dirname "${BASH_SOURCE[0]}")/../models" && pwd)
    case "$(hostname -s)" in
        gilbreth-b*) MODEL=$_models/run5_ep301.nequip.pt2 ;;     # a30 b-nodes (compiled there)
        gilbreth-d*) MODEL=$_models/run5_ep301.nequip.pt2 ;;     # a30 d-nodes (ran there: tests/RESULTS.md, 1d)
        gilbreth-g*) MODEL=$_models/run5_ep301.G.nequip.pt2 ;;   # a100-40gb g-nodes, AMD EPYC 7662
        gilbreth-n*) MODEL=$_models/run5_ep301.N.nequip.pt2 ;;   # a100-40gb n-nodes, AMD EPYC 7413
        *) echo "common/defaults.sh: no compiled model for node $(hostname -s); build one there with" \
                "models/compile_model.sh and add it here" >&2
           return 1 ;;
    esac
    unset _models
fi
