#!/bin/bash
# Build DoSPT (vibrational DOS, Caro's 2PT code; Saswat's fork for non-orthogonal cells) for phases/ (analysis/
# phases_compare.py). The binary on depot needs libgfortran.so.3, which the cluster no longer has, so this copies the
# source and rebuilds it with the system gfortran:
#   bash analysis/build_dospt.sh          -> env/dospt/bin/DoSPT2 (not tracked; env/dospt/ is the build tree)
# Source: $DOSPT_SRC (default below), built by its own build.sh (dfftpack, Voro++, then DoSPT; gfortran -fopenmp).
# Check after building: bash analysis/build_dospt.sh check  reruns the depot example (dospt_example: hexagonal GST, DFT
# trajectory, its input) in a scratch directory and compares the total DOS with the example's own dos file.
# Cell input (keyword cell, nm): three rows, the lattice vectors a, b, c (read_input.f90 reads L(1) Lxy Lxz / Lyx L(2)
# Lyz / Lzx Lzy L(3); restore_replica_traj adds j*a + k*b + m*c). phases_compare.py writes it from the LAMMPS box.
set -euo pipefail
ROOT=$(realpath "$(dirname "$0")/..")
SRC=${DOSPT_SRC:-/depot/prism/data/rapplet/DoSPT-0.2.2_non-ortho_Saswat}
EXAMPLE=${DOSPT_EXAMPLE:-/depot/prism/data/rapplet/dospt_example}
DST=$ROOT/env/dospt
if [ "${1:-}" != check ]; then
    rm -rf $DST && mkdir -p $DST
    cp -r $SRC/src $SRC/build.sh $SRC/LICENSE $DST/
    find $DST/src \( -name '*.o' -o -name '*.mod' -o -name '*.a' \) -delete
    rm -rf $DST/src/voro++/install
    (cd $DST && bash build.sh > build.log 2>&1) || { tail -20 $DST/build.log; exit 1; }
    ldd $DST/bin/DoSPT2 | grep -q "not found" && { ldd $DST/bin/DoSPT2; exit 1; }
    echo "built $DST/bin/DoSPT2 (log $DST/build.log)"
fi
# check: rerun the example and compare total DOS
T=$(mktemp -d)
trap 'rm -rf $T' EXIT
for f in input groups supergroups masses traj.xyz; do ln -s $EXAMPLE/$f $T/$f; done
(cd $T && OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} $DST/bin/DoSPT2 > dospt.log 2>&1) || { tail $T/dospt.log; exit 1; }
python3 - "$T/dos" "$EXAMPLE/dos" <<'EOF'
import sys
def total(p):
    rows = []
    for ln in open(p):
        if ln.lstrip().startswith("#"):
            if rows: break
            continue
        if ln.strip(): rows.append([float(x) for x in ln.split()[:2]])
    return rows
a, b = total(sys.argv[1]), total(sys.argv[2])
assert len(a) == len(b), (len(a), len(b))
d = max(abs(x[1] - y[1]) for x, y in zip(a, b)) / max(y[1] for y in b)
print(f"example total DOS: {len(a)} points, max |new - reference| / max = {d:.2e}", "PASS" if d < 1e-6 else "FAIL")
sys.exit(d >= 1e-6)
EOF
