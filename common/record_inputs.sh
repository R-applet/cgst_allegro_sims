#!/bin/bash
# Record what a LAMMPS run was started with, for human reference: called by common/run_lmp.sh before every run (and
# usable by hand). Writes lmp_inputs/<log name>/ in the current (run) directory:
#   <input file>           a copy of the -in input as it was at start
#   <included files>       a copy of every file it includes (${root} resolved from -var root), e.g. in.potential
#   run_command.sh         the exact command, with every -var value, from this directory (rerunning it re-executes
#                          the run through common/run_lmp.sh; it is a record, not how runs are submitted)
#   run_info.txt           date, host, Slurm job, git commit (and whether the tree had uncommitted changes), MODEL_ID,
#                          the -var model file and its sha256, container, NGPU
# One directory per log name, so the jobs of an anneal or ramp chain (log.anneal.1, .2, ...) and runs sharing a
# directory (calibration) each keep their own record. A failure here only prints a warning; the run goes on.
# Usage: record_inputs.sh NGPU <the run_lmp.sh arguments after NGPU>
record_inputs() {
    local ngpu=$1; shift
    local args=("$@") inp="" log="log.lammps" root="" model="" i
    for ((i = 0; i < ${#args[@]}; i++)); do
        case ${args[i]} in
            -in) inp=${args[i + 1]} ;;
            -log) log=${args[i + 1]} ;;
            -var) case ${args[i + 1]} in root) root=${args[i + 2]} ;; model) model=${args[i + 2]} ;; esac ;;
        esac
    done
    [ -n "$inp" ] && [ -e "$inp" ] || { echo "record_inputs: no -in file ('$inp'), nothing recorded" >&2; return 1; }
    local here proj rec
    here=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
    proj=$(realpath "$here/..")
    root=${root:-$proj}
    rec=lmp_inputs/$(basename "$log")
    mkdir -p "$rec"
    cp -p "$inp" "$rec/"
    local inc p
    for inc in $(grep -oE '^[[:space:]]*include[[:space:]]+[^[:space:]#]+|"include[[:space:]]+[^[:space:]"]+' "$inp" \
                 | awk '{print $NF}' | sort -u); do
        p=${inc//\$\{root\}/$root}
        [ -e "$p" ] && cp -p "$p" "$rec/" || echo "include $inc: not found when recorded" >> "$rec/run_info.txt"
    done
    {
        echo "#!/bin/bash"
        echo "# Recorded $(date '+%Y-%m-%d %H:%M:%S') by common/record_inputs.sh; reference copy, not used to submit."
        echo "# The input as run is $(basename "$inp") in this directory; the command reads the original path."
        printf 'cd %q\n' "$PWD"
        printf '%q ' "$here/run_lmp.sh" "$ngpu" "${args[@]}"; echo
    } > "$rec/run_command.sh"
    local commit dirty
    commit=$(git -C "$proj" rev-parse HEAD 2>/dev/null || echo unknown)
    dirty=$(git -C "$proj" status --porcelain --untracked-files=no 2>/dev/null | grep -v '^.. tests/' | wc -l)
    {
        echo "date        $(date '+%Y-%m-%d %H:%M:%S %Z')"
        echo "host        $(hostname -s)"
        echo "slurm_job   ${SLURM_JOB_ID:-none}${SLURM_ARRAY_JOB_ID:+ (array ${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID})}"
        echo "git_commit  $commit ($dirty modified tracked files outside tests/)"
        echo "MODEL_ID    ${MODEL_ID:-unset}"
        echo "model       ${model:-none} sha256 $([ -n "$model" ] && [ -e "$model" ] && sha256sum "$model" | cut -c1-64)"
        echo "container   ${SIF:-unset}"
        echo "ngpu        $ngpu"
        echo "input       $(realpath "$inp")"
        echo "workdir     $PWD"
    } >> "$rec/run_info.txt"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    source "$(dirname "$(realpath "$0")")/model.sh"
    record_inputs "$@"
fi
