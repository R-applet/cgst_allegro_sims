"""Write a model glass npz for check.py (MODEL_GLASS) from a melt-quench run: the trajectory frames of the final 50 ps
at 300 K (the RDF window of stage 4 of meltquench/in.meltquench), in the format of the frozen run5_ep301 reference
tests/mq_analysis/ref/model_glass_300K.npz: steps, box (N x 3), pos (N x atoms x 3, float32, relative to the box
origin), types (1-4, int8). Use a C-free (x0) run: the DFT glass is Ge2Sb2Te5.

Usage: python make_model_glass.py <melt-quench run dir> <out.npz> [--window-ps 50]
Then:  MODEL_GLASS=<out.npz> python check.py
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "analysis"))
from bondorder import read_dump  # noqa: E402
from runio import load_dat  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--window-ps", type=float, default=50.0)
    a = ap.parse_args()
    d = load_dat(a.run / "mq.dat")
    dt = d["time_ps"][-1] / d["step"][-1]
    t_end = d["time_ps"][-1]
    frames = [(s, L, c) for s, L, c in read_dump(a.run / "traj.lammpstrj.gz") if s * dt >= t_end - a.window_ps - 1e-9]
    if not frames:
        sys.exit(f"{a.run}: no trajectory frames in the last {a.window_ps} ps")
    types = frames[0][2]["type"].astype(np.int8)
    if (types == 4).any():
        print(f"WARNING: {a.run.name} contains C; check.py compares with C-free DFT Ge2Sb2Te5", file=sys.stderr)
    np.savez_compressed(a.out, steps=np.array([s for s, _, _ in frames]), box=np.array([L for _, L, _ in frames]),
                        pos=np.array([c["pos"] for _, _, c in frames], dtype=np.float32), types=types)
    print(f"wrote {a.out}: {len(frames)} frames, {len(types)} atoms, steps {frames[0][0]}-{frames[-1][0]} "
          f"(t >= {t_end - a.window_ps:.0f} ps of {t_end:.0f})")


if __name__ == "__main__":
    main()
