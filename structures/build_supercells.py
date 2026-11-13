"""Build the NxNxN (production: 3x3x3) supercells from the 512-site rocksalt cells in structures/.

Input cells (8x8x8 rocksalt sites on a 3.015 A grid, Te on the anion sublattice, Ge/Sb/C/vacancy on
the cation sublattice; C sits on former vacancy sites):

    gst_cubic.data   -> x0     461 atoms   0 C
    c1_cubic.data    -> x1     466 atoms   5 C  (1.07 at.%)
    c2_5_cubic.data  -> x2p5   473 atoms  12 C  (2.54 at.%)
    c5_cubic.data    -> x5     486 atoms  25 C  (5.14 at.%)
    c10_cubic.data   -> x10    512 atoms  51 C  (9.96 at.%, every vacancy filled)

Composition series (decided 2026-11-06): x1-x5 put C on some cation vacancies; x10 is deliberately the vacancy-free
endpoint (GST)C, with every vacancy filled. So x10 differs from x5 in both C content and vacancy count; label it
as such on C-trend plots. Its rocksalt cell disorders within ps at 600 K (tests/RESULTS.md, 1a), so it is never
used as a crystal reference.

Two defects in the inputs are repaired here:
  * gst/c1/c2_5 have a 24.62 A box but the 3.015 A grid spans 24.12 A, leaving a 0.5 A gap at the
    periodic boundary. The box is reset to 8 * 3.015 = 24.12 A for every cell (positions are unchanged).
  * gst/c10 have no Masses section. Masses are always written.

The 3x3x3 replica repeats the C/vacancy arrangement every 24 A. That periodicity is removed by the
1500 K melt (see meltquench/README.md, MSD gate); do not use these cells directly as a crystal model.

Usage:  python build_supercells.py [--nrep N]   (default N=3; writes structures/NNN/<tag>.data, prints checks)
        N=1 and N=2 give the cleaned single cell and 2x2x2 cell used by tests/. N=1 also writes
        structures/<tag>_<natoms>.data (x0_461, x1_466, x2p5_473, x5_486, x10_512): the cleaned single cells,
        tracked in git as the reference crystal structures (NNN/ directories are not tracked).
"""
import shutil
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
GRID = 3.015                 # A, half the rocksalt lattice constant used to build the inputs
NSITE = 8                    # sites per edge in the input cell
MASSES = {1: ("Ge", 72.630), 2: ("Sb", 121.760), 3: ("Te", 127.600), 4: ("C", 12.011)}
CELLS = {"x0": "gst_cubic.data", "x1": "c1_cubic.data", "x2p5": "c2_5_cubic.data",
         "x5": "c5_cubic.data", "x10": "c10_cubic.data"}


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


def main(NREP):
    outdir = HERE / f"{NREP}{NREP}{NREP}"
    outdir.mkdir(exist_ok=True)
    a = GRID * NSITE
    print(f"{'tag':6s} {'N_in':>5s} {'N_out':>6s} {'Ge':>5s} {'Sb':>5s} {'Te':>5s} {'C':>4s} "
          f"{'at%C':>6s} {'L_A':>7s} {'dmin_A':>7s}")
    for tag, fname in CELLS.items():
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
        with open(outdir / f"{tag}.data", "w") as f:
            f.write(f"Rocksalt GST + C, {tag}, {NREP}x{NREP}x{NREP} of structures/{fname} (box snapped to {GRID}*{NSITE} A)"
                    f" by build_supercells.py\n\n")
            f.write(f"{n} atoms\n4 atom types\n\n")
            for ax in "xyz":
                f.write(f"0.0 {L:.6f} {ax}lo {ax}hi\n")
            f.write("\nMasses\n\n")
            for t, (el, m) in MASSES.items():
                f.write(f"{t} {m}  # {el}\n")
            f.write("\nAtoms  # atomic\n\n")
            for i, (t, p) in enumerate(zip(big_types, big_pos), start=1):
                f.write(f"{i} {t} {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
        if NREP == 1:                                   # tracked reference copy, named by atom count
            shutil.copyfile(outdir / f"{tag}.data", HERE / f"{tag}_{n}.data")
        print(f"{tag:6s} {len(types):5d} {n:6d} {counts[1]:5d} {counts[2]:5d} {counts[3]:5d} {counts[4]:4d} "
              f"{100 * counts[4] / n:6.2f} {L:7.3f} {dmin:7.3f}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nrep", type=int, default=3, help="replication per direction (default 3)")
    main(ap.parse_args().nrep)
