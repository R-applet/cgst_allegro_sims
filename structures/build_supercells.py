"""Build the NxNxN supercells (melt-quench and recrystallization: 4x4x4 from 2026-11-13; 3x3x3 for run5_ep301) from the
cleaned single rocksalt cells in structures/, named by atom count:

    x0_461.data     0 C               x5_486.data    25 C  (5.14 at.%)
    x1_466.data     5 C  (1.07 at.%)  x10_512.data   51 C  (9.96 at.%, every vacancy filled)
    x2p5_473.data  12 C  (2.54 at.%)

Each is 8x8x8 rocksalt sites on a 3.015 A grid, Te on the anion sublattice, Ge/Sb/C/vacancy on the cation sublattice
(C on former vacancy sites). They are the tracked reference crystal structures; NNN/<tag>.data (111/, 222/, 333/,
444/, ...) are generated and not tracked.

Composition series (decided 2026-11-06): x1-x5 put C on some cation vacancies; x10 is deliberately the vacancy-free
endpoint (GST)C, with every vacancy filled. So x10 differs from x5 in both C content and vacancy count; label it
as such on C-trend plots. Its rocksalt cell disorders within ps at 600 K (tests/RESULTS.md, 1a), so it is never
used as a crystal reference.

The cleaned cells were made from the ASE-written originals in structures/original/ (gst_cubic, c1_cubic, c2_5_cubic,
c5_cubic, c10_cubic), repairing two defects: gst/c1/c2_5 have a 24.62 A box although the 3.015 A grid spans 24.12 A
(a 0.5 A gap at the periodic boundary), so the box is reset to 8 * 3.015 = 24.12 A (positions unchanged); gst/c10
have no Masses section, so masses are always written. --from-original redoes that and rewrites the cleaned cells.

The NxNxN replica repeats the C/vacancy arrangement every 24 A. That periodicity is removed by the melt
(meltquench/README.md, MSD gate); do not use these cells directly as a crystal model.

Usage:  python build_supercells.py [--nrep N]          writes structures/NNN/<tag>.data from the cleaned cells (default
                                                        N=3), prints checks; N=1, 2 give the cells tests/ use
        python build_supercells.py --from-original     rebuild the cleaned cells x*_<natoms>.data from original/
"""
import shutil
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
GRID = 3.015                 # A, half the rocksalt lattice constant used to build the inputs
NSITE = 8                    # sites per edge in the input cell
MASSES = {1: ("Ge", 72.630), 2: ("Sb", 121.760), 3: ("Te", 127.600), 4: ("C", 12.011)}
ORIGINAL = {"x0": "original/gst_cubic.data", "x1": "original/c1_cubic.data", "x2p5": "original/c2_5_cubic.data",
            "x5": "original/c5_cubic.data", "x10": "original/c10_cubic.data"}
NATOMS = {"x0": 461, "x1": 466, "x2p5": 473, "x5": 486, "x10": 512}
CLEANED = {tag: f"{tag}_{n}.data" for tag, n in NATOMS.items()}


def read_atoms(path):
    """Return (types, positions) from the Atoms section of an atomic-style LAMMPS data file."""
    lines = path.read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip().startswith("Atoms")) + 1
    rows = [l.split() for l in lines[start:] if len(l.split()) >= 5]
    arr = np.array([[float(v) for v in r[:5]] for r in rows])
    order = np.argsort(arr[:, 0])
    return arr[order, 1].astype(int), arr[order, 2:5]


def min_distance(pos, box):
    """Minimum-image minimum pair distance (O(N^2) on the input cell, which is small)."""
    d = pos[:, None, :] - pos[None, :, :]
    d -= box * np.round(d / box)
    r = np.sqrt((d ** 2).sum(-1))
    np.fill_diagonal(r, np.inf)
    return r.min()


def main(NREP, from_original=False):
    sources = ORIGINAL if from_original else CLEANED
    if from_original:
        NREP = 1
    outdir = HERE / f"{NREP}{NREP}{NREP}"
    outdir.mkdir(exist_ok=True)
    a = GRID * NSITE
    print(f"{'tag':6s} {'N_in':>5s} {'N_out':>6s} {'Ge':>5s} {'Sb':>5s} {'Te':>5s} {'C':>4s} "
          f"{'at%C':>6s} {'L_A':>7s} {'dmin_A':>7s}")
    for tag, fname in sources.items():
        types, pos = read_atoms(HERE / fname)
        on_grid = np.abs(pos / GRID - np.round(pos / GRID)).max() < 1e-6
        if not on_grid or pos.min() < -1e-9 or pos.max() > a - GRID + 1e-6:
            raise ValueError(f"{fname}: atoms are not on the {GRID} A grid inside [0, {a})")
        dmin = min_distance(pos, a)
        shifts = np.array([[i, j, k] for i in range(NREP) for j in range(NREP) for k in range(NREP)]) * a
        big_pos = (pos[None, :, :] + shifts[:, None, :]).reshape(-1, 3)
        big_types = np.tile(types, len(shifts))
        L = a * NREP
        counts = {t: int((big_types == t).sum()) for t in MASSES}
        n = len(big_types)
        if NREP == 1 and n != NATOMS[tag]:
            raise ValueError(f"{fname}: {n} atoms, expected {NATOMS[tag]}")
        src = f"structures/{fname}" + (f" (box snapped to {GRID}*{NSITE} A)" if from_original else "")
        with open(outdir / f"{tag}.data", "w") as f:
            f.write(f"Rocksalt GST + C, {tag}, {NREP}x{NREP}x{NREP} of {src} by build_supercells.py\n\n")
            f.write(f"{n} atoms\n4 atom types\n\n")
            for ax in "xyz":
                f.write(f"0.0 {L:.6f} {ax}lo {ax}hi\n")
            f.write("\nMasses\n\n")
            for t, (el, m) in MASSES.items():
                f.write(f"{t} {m}  # {el}\n")
            f.write("\nAtoms  # atomic\n\n")
            for i, (t, p) in enumerate(zip(big_types, big_pos), start=1):
                f.write(f"{i} {t} {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
        if from_original:                               # the tracked cleaned cell, named by atom count
            shutil.copyfile(outdir / f"{tag}.data", HERE / CLEANED[tag])
        print(f"{tag:6s} {len(types):5d} {n:6d} {counts[1]:5d} {counts[2]:5d} {counts[3]:5d} {counts[4]:4d} "
              f"{100 * counts[4] / n:6.2f} {L:7.3f} {dmin:7.3f}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nrep", type=int, default=3, help="replication per direction (default 3)")
    ap.add_argument("--from-original", action="store_true",
                    help="rebuild the cleaned single cells x*_<natoms>.data from structures/original/ (implies --nrep 1)")
    a = ap.parse_args()
    main(a.nrep, a.from_original)
