"""Q4 bond-order crystallinity, matching common/in.analysis, for post-processing and calibration.

LAMMPS (common/in.analysis):
  compute q4  all orientorder/atom degrees 1 4 nnn NULL cutoff q_rc components 4
  compute ncb all coord/atom orientorder q4 q_thr
  crystalline atom: ncb >= q_nmin
Here: q4m(i) = mean over neighbours j within rc of Y_4m(r_ij); a bond i-j is crystal-like if
Re[sum_m q4m(i) q4m(j)*] / (|q4(i)| |q4(j)|) > thr. Crystalline clusters are connected components of crystalline
atoms joined by bonds shorter than rc. Requires an orthogonal periodic box (isotropic NPT keeps it cubic).

Library use:  frames = read_dump(path); ncb = crystal_bonds(pos, L, rc, thr); cluster_sizes(mask, pos, L, rc) (all
              crystalline cluster sizes, largest first); largest_cluster(mask, pos, L, rc)
CLI check:    python bondorder.py traj.lammpstrj.gz [rc thr nmin]   -> per frame: xfrac (python), xfrac (LAMMPS,
              from the dumped c_ncb column, if present), largest crystalline cluster
"""
import gzip
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

try:
    from scipy.special import sph_harm_y                  # scipy >= 1.15: sph_harm_y(l, m, polar, azimuth)

    def _ylm(l, m, polar, azim):
        return sph_harm_y(l, m, polar, azim)
except ImportError:                                       # older scipy: sph_harm(m, l, azimuth, polar)
    from scipy.special import sph_harm

    def _ylm(l, m, polar, azim):
        return sph_harm(m, l, azim, polar)


def read_dump(path):
    """Yield (timestep, box_lengths[3], columns dict) for each frame of a (gzipped) LAMMPS custom dump, sorted by id.
    A gzip file cut off by a killed job (no end-of-stream marker) ends at its last complete frame, with a warning."""
    op = gzip.open if str(path).endswith(".gz") else open
    try:
        yield from _read_frames(op, path)
    except (EOFError, _Truncated):
        print(f"note: {path} is truncated (killed job); read up to its last complete frame", file=sys.stderr)


class _Truncated(Exception):
    pass


def _read_frames(op, path):
    with op(path, "rt") as f:
        while True:
            line = f.readline()
            if not line:
                return
            if not line.startswith("ITEM: TIMESTEP"):
                continue
            step = int(f.readline())
            f.readline()
            n = int(f.readline())
            hdr = f.readline()
            if "xy" in hdr:
                raise ValueError("triclinic boxes are not supported")
            bounds = np.array([[float(v) for v in f.readline().split()[:2]] for _ in range(3)])
            names = f.readline().split()[2:]
            lines = [f.readline() for _ in range(n)]
            if not lines or not lines[-1].endswith("\n"):
                raise _Truncated
            data = np.loadtxt(lines, ndmin=2)
            data = data[np.argsort(data[:, names.index("id")])]
            cols = {k: data[:, i] for i, k in enumerate(names)}
            cols["pos"] = np.stack([cols["x"], cols["y"], cols["z"]], 1) - bounds[:, 0]
            yield step, bounds[:, 1] - bounds[:, 0], cols


def _pairs(pos, L, rc):
    tree = cKDTree(np.mod(pos, L), boxsize=L)
    p = tree.query_pairs(rc, output_type="ndarray")
    d = np.mod(pos, L)[p[:, 1]] - np.mod(pos, L)[p[:, 0]]
    d -= L * np.round(d / L)
    return p, d


def q4_vectors(pos, L, rc, pairs=None):
    """Per-atom normalized complex q4m vectors (N x 9) and neighbour count."""
    p, d = pairs if pairs is not None else _pairs(pos, L, rc)
    r = np.linalg.norm(d, axis=1)
    polar = np.arccos(np.clip(d[:, 2] / r, -1, 1))
    azim = np.arctan2(d[:, 1], d[:, 0])
    n = len(pos)
    q = np.zeros((n, 9), complex)
    for k, m in enumerate(range(-4, 5)):
        y = _ylm(4, m, polar, azim)
        # Y_lm(-r) = (-1)^l Y_lm(r) and l = 4 is even, so i and j both get +y
        np.add.at(q[:, k], p[:, 0], y)
        np.add.at(q[:, k], p[:, 1], y)
    nn = np.bincount(p.ravel(), minlength=n)
    norm = np.linalg.norm(q, axis=1)
    q[norm > 0] /= norm[norm > 0, None]
    return q, nn


def crystal_bonds(pos, L, rc, thr):
    """Number of crystal-like bonds per atom (the LAMMPS c_ncb column)."""
    pairs = _pairs(pos, L, rc)
    q, _ = q4_vectors(pos, L, rc, pairs)
    p = pairs[0]
    dot = np.real(np.sum(q[p[:, 0]] * np.conj(q[p[:, 1]]), axis=1))
    good = p[dot > thr]
    return np.bincount(good.ravel(), minlength=len(pos))


def bond_dots(pos, L, rc):
    """(pairs, normalized q4 dot product per pair), for scanning thr/nmin without recomputing q4."""
    pairs = _pairs(pos, L, rc)
    q, _ = q4_vectors(pos, L, rc, pairs)
    p = pairs[0]
    return p, np.real(np.sum(q[p[:, 0]] * np.conj(q[p[:, 1]]), axis=1))


def cluster_sizes(mask, pos, L, rc):
    """Sizes of the connected clusters of atoms in mask (bonds shorter than rc), largest first."""
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return np.zeros(0, int)
    p, _ = _pairs(pos[idx], L, rc)
    g = coo_matrix((np.ones(len(p)), (p[:, 0], p[:, 1])), shape=(len(idx), len(idx)))
    _, lab = connected_components(g, directed=False)
    return np.sort(np.bincount(lab))[::-1]


def largest_cluster(mask, pos, L, rc):
    """Size of the largest connected cluster of atoms in mask (bonds shorter than rc)."""
    s = cluster_sizes(mask, pos, L, rc)
    return int(s[0]) if len(s) else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rc, thr, nmin = (float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (3.6, 0.5, 4)
    print("step xfrac_py xfrac_lammps max|ncb_py-ncb_lammps| largest_cluster")
    for step, L, c in read_dump(sys.argv[1]):
        ncb = crystal_bonds(c["pos"], L, rc, thr)
        mask = ncb >= nmin
        ref = c.get("c_ncb")
        print(step, f"{mask.mean():.4f}",
              f"{(ref >= nmin).mean():.4f}" if ref is not None else "-",
              int(np.abs(ncb - ref).max()) if ref is not None else "-",
              largest_cluster(mask, c["pos"], L, rc))
