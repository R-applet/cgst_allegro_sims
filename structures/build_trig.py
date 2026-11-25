"""Trigonal Ge2Sb2Te5 supercell for the trigonal melting runs (meltquench/, PHASE=trig).

Source: phases/structures/hex_gst.data, the 144-atom DFT trigonal cell (Kooi stacking Te-Sb-Te-Ge-Te-Ge-Te-Sb-Te,
one 9-layer block along c; 4x4 hexagonal in-plane cell, a = 4.23 A, from a 300 K DFT-MD frame). Its hexagonal box
(a1 = (Lx, 0, 0), a2 = (xy, Ly, 0), a3 = (0, 0, Lz)) is converted to the orthohexagonal cell A = a1, B = a1 + 2 a2,
C = a3 (twice the atoms, 288, orthogonal), so the anisotropic barostat can relax a, b and c independently without
tilt factors; then replicated NA x NB x NC (default 6 x 3 x 6: 31104 atoms, ~102 x 88 x 103 A, near the 444 rocksalt
cells' 29.5k-32.8k atoms and 96.5 A).
Writes structures/trig/x0.data (4 types: Ge Sb Te C, C absent). Carbon-containing trigonal cells: not built yet.

Usage (repository root): env/cgst-ana/bin/python structures/build_trig.py [--rep 6 3 6]
"""
import argparse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "phases" / "structures" / "hex_gst.data"
MASSES = {1: 72.63, 2: 121.76, 3: 127.6, 4: 12.011}


def read(path):
    lines = path.read_text().splitlines()
    box = {}
    for l in lines:
        w = l.split()
        if l.endswith("xlo xhi"):
            box["x"] = float(w[1]) - float(w[0])
        elif l.endswith("ylo yhi"):
            box["y"] = float(w[1]) - float(w[0])
        elif l.endswith("zlo zhi"):
            box["z"] = float(w[1]) - float(w[0])
        elif l.endswith("xy xz yz"):
            box["xy"], box["xz"], box["yz"] = map(float, w[:3])
    n = int(next(l for l in lines if l.strip().endswith(" atoms")).split()[0])
    i = next(k for k, l in enumerate(lines) if l.startswith("Atoms"))
    a = np.array([[float(x) for x in l.split()[:5]] for l in lines[i + 2:i + 2 + n]])
    return box, a[:, 1].astype(int), a[:, 2:5]


def min_distance(pos, L):
    from scipy.spatial import cKDTree
    d, _ = cKDTree(pos % L, boxsize=L).query(pos % L, k=2)
    return d[:, 1].min()


def main(rep):
    box, types, pos = read(SRC)
    if box["xz"] or box["yz"]:
        raise SystemExit("expected a hexagonal cell with only an xy tilt")
    a1 = np.array([box["x"], 0, 0])
    a2 = np.array([box["xy"], box["y"], 0])
    A, B, C = box["x"], np.linalg.norm(a1 + 2 * a2), box["z"]
    if abs((a1 + 2 * a2)[0]) > 1e-3 * A:
        raise SystemExit(f"a1 + 2 a2 is not along y ({a1 + 2 * a2}): not a 60/120-degree hexagonal cell")
    L0 = np.array([A, B, C])
    p = np.vstack([pos, pos + a2]) % L0                                      # 2 hexagonal cells fill the ortho cell
    t = np.concatenate([types, types])
    if min_distance(p, L0) < 1.5:
        raise SystemExit("duplicate atoms in the orthohexagonal cell")
    shifts = np.array([[i, j, k] for i in range(rep[0]) for j in range(rep[1]) for k in range(rep[2])]) * L0
    P = (p[None, :, :] + shifts[:, None, :]).reshape(-1, 3)
    T = np.tile(t, len(shifts))
    L = L0 * np.array(rep)
    dmin = min_distance(P, L)
    out = ROOT / "structures" / "trig" / "x0.data"
    out.parent.mkdir(exist_ok=True)
    counts = {s: int((T == k).sum()) for k, s in zip(range(1, 5), ("Ge", "Sb", "Te", "C"))}
    with open(out, "w") as f:
        f.write(f"# trigonal GST (Kooi), orthohexagonal {rep[0]}x{rep[1]}x{rep[2]} of {SRC.name} "
                f"(structures/build_trig.py); " + " ".join(f"{s} {n}" for s, n in counts.items()) + "\n\n")
        f.write(f"{len(P)} atoms\n4 atom types\n\n")
        for ax, l in zip("xyz", L):
            f.write(f"0.0 {l:.8f} {ax}lo {ax}hi\n")
        f.write("\nMasses\n\n" + "".join(f"{k} {m}\n" for k, m in MASSES.items()))
        f.write("\nAtoms  # atomic\n\n")
        for i, (ty, (x, y, z)) in enumerate(zip(T, P), 1):
            f.write(f"{i} {ty} {x:.8f} {y:.8f} {z:.8f}\n")
    print(f"wrote {out}: {len(P)} atoms {counts}, box {L.round(2)} A, V/atom {np.prod(L) / len(P):.3f} A^3 "
          f"(source {np.prod([box['x'], box['y'], box['z']]) / len(pos):.3f}), closest pair {dmin:.2f} A")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rep", type=int, nargs=3, default=[6, 3, 6], metavar=("NA", "NB", "NC"))
    main(ap.parse_args().rep)
