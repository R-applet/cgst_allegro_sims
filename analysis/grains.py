"""Grain tracking in anneal runs (recryst/), for the rocksalt compositions x0-x2p5 (x5/x10 crystals are too defective).

Grains are found on the Te sublattice, which is fcc in rocksalt GST whatever the cation vacancies and C do: OVITO
polyhedral template matching (FCC only, RMSD cutoff RMSD) gives each Te atom an orientation, and OVITO grain
segmentation groups matched Te atoms into grains of at least MIN_TE atoms, with no orphan adoption (an unmatched Te
atom belongs to no grain, so a partially crystallized frame does not hand amorphous regions to grains).
Validated 2026-11-24 (scratch probe grains_validate.py): the glass (first hold frame) gives no grain at RMSD
0.10-0.35 and min sizes down to 20 Te; at 600-650 K the grain count is steady over RMSD 0.10-0.25 and min size 20-100
(large grains); touching grains have a median disorientation of 43 deg (random cubic texture: ~41), 1 low-angle pair
in 94 and 58, i.e. grains are not split; renders show one lattice orientation per grain. At 500 K the crystal is a
mosaic of small domains (x0: 42 grains >= 30 Te but 7 >= 100; x1 20 vs 2; x2p5 9 vs 0), so MIN_TE is 30, not 100.

Per run, every STRIDE ps of the hold, writes <run>/grains_r<RMSD>_m<MIN_TE>.txt:
  'F' rows  t_ps xfracGST n_grains te_in_grains  C: n_interior n_boundary n_amorphous  GeSb: same three
  'G' rows  t_ps track grain_te_atoms qx qy qz qw  (track = id kept across frames)
  'E' rows  t_ps event track [parents]  event = new (a nucleus appears) | merge (2+ tracks become one) | lost
Tracking: a grain continues the previous frame's grain it shares most Te atoms with (at least half of the smaller of
the two); a grain inheriting two or more previous grains is a merge (it keeps the largest parent's track).
Site class of a C (or Ge/Sb) atom from the grain labels of nearby Te atoms: Te of two or more grains within RC_GB ->
boundary (boundaries hold unmatched Te, so the grains on either side sit a few A apart); else a labelled Te within
RC_SITE -> interior; else amorphous. Ge/Sb sit on the same sites, so they are the reference for
whether C prefers boundaries.

Usage: python analysis/grains.py [--stride 10] RUN_DIR ...    (heavy: run as a Slurm job, recryst/scripts or --wrap)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bondorder import read_dump  # noqa: E402

RMSD = 0.15
MIN_TE = 30            # Te atoms (~55 atoms, d_eq ~1.2 nm); see the validation note above
RC_SITE = 3.6          # A: cation-Te first shell in rocksalt GST is ~3.0 A; the second (Te-Te) shell is at 4.2 A
RC_GB = 6.0            # A: grains within this distance of an atom make it a boundary atom (gaps of unmatched Te)
TE, C = 3, 4


def frames(run, stride):
    """(hold time ps, box lengths, cols) of the hold, frames at least `stride` ps apart, from all traj segments (a step in two files
    is taken from the later file, as recryst_summary.clusters)."""
    from recryst_summary import hold_info, load_dat
    d = load_dat(run / "anneal.dat")
    dt = d["time_ps"][-1] / d["step"][-1]
    t0 = hold_info(run)["hold_start_ps"]
    files = sorted(run.glob("traj.*.lammpstrj.gz"), key=lambda f: int(f.name.split(".")[1]))
    starts = [int(f.name.split(".")[1]) for f in files]
    out = {}
    for k, f in enumerate(files):
        end = starts[k + 1] if k + 1 < len(files) else None          # later file wins from its first step on
        for step, L, c in read_dump(f):
            if end is not None and step >= end:
                break
            t = step * dt - t0
            if t < -1e-9:
                continue
            out[round(t, 6)] = (L, c)
    nxt = -np.inf
    for t in sorted(out):                              # hold starts need not fall on a dump: keep >= stride apart
        if t >= nxt - 1e-6:
            nxt = t + stride
            yield t, *out[t]


def segment(pos, L):
    from ovito.data import DataCollection, SimulationCell
    from ovito.modifiers import GrainSegmentationModifier, PolyhedralTemplateMatchingModifier
    d = DataCollection()
    d.objects.append(SimulationCell(matrix=np.column_stack([np.diag(L), np.zeros(3)]), pbc=(True, True, True)))
    d.create_particles(count=len(pos)).create_property("Position", data=pos)
    ptm = PolyhedralTemplateMatchingModifier(output_orientation=True, rmsd_cutoff=RMSD)
    for s in ptm.structures:
        s.enabled = s.id == PolyhedralTemplateMatchingModifier.Type.FCC
    d.apply(ptm)
    d.apply(GrainSegmentationModifier(min_grain_size=MIN_TE, merging_threshold=0.0, orphan_adoption=False,
                                      color_particles=False))
    gid = np.asarray(d.particles["Grain"]).astype(int)
    tab = d.tables["grains"] if "grains" in d.tables else None
    ori = {} if tab is None else dict(zip(np.asarray(tab["Grain Identifier"]).astype(int),
                                          np.asarray(tab["Orientation"])))
    return gid, ori


def site_class(pos_te, gid, pos_x, L):
    if len(pos_x) == 0:
        return 0, 0, 0
    lab = gid >= 0                                     # OVITO grain ids start at 0; -1 = no grain
    if not lab.any():
        return 0, 0, len(pos_x)
    tree = cKDTree(pos_te[lab] % L, boxsize=L)
    g = gid[lab]
    counts = [0, 0, 0]
    for near, far in zip(tree.query_ball_point(pos_x % L, RC_SITE), tree.query_ball_point(pos_x % L, RC_GB)):
        if len(set(g[far])) > 1:
            counts[1] += 1
        elif near:
            counts[0] += 1
        else:
            counts[2] += 1
    return tuple(counts)


def track_run(run, stride):
    run = Path(run)
    clusters = sorted(run.glob("clusters_q*.txt"))
    xf = {}
    if clusters:
        c = np.loadtxt(clusters[0], skiprows=1)
        xf = dict(zip(np.round(c[:, 0], 6), c[:, 3]))
    lines = [f"# {run.name}: Te-sublattice grains, PTM FCC rmsd {RMSD}, min {MIN_TE} Te, no orphan adoption; "
             f"site radius {RC_SITE} A; every {stride} ps (analysis/grains.py)",
             "# F t_ps xfracGST n_grains te_in_grains C_interior C_boundary C_amorphous GeSb_interior GeSb_boundary GeSb_amorphous",
             "# G t_ps track te_atoms qx qy qz qw",
             "# E t_ps event track parents"]
    prev, next_track = {}, 1                           # prev: track -> set of Te ids
    for t, L, cols in frames(run, stride):
        typ = cols["type"].astype(int)
        ids = cols["id"].astype(int)
        te = typ == TE
        gid, ori = segment(cols["pos"][te], L)
        te_ids = ids[te]
        cur = {g: set(te_ids[gid == g]) for g in ori}
        cur = {g: m for g, m in cur.items() if g >= 0 and len(m) >= MIN_TE}  # OVITO: grains 0, 1, ...; -1 unassigned
        gid = np.where(np.isin(gid, list(cur)), gid, -1)
        # link to previous tracks
        assign, parents_of = {}, {}
        for g, members in cur.items():
            ps = [tr for tr, pm in prev.items() if len(members & pm) >= 0.5 * min(len(members), len(pm))]
            parents_of[g] = sorted(ps, key=lambda tr: -len(prev[tr]))
        used = set()
        for g in sorted(cur, key=lambda g: -len(cur[g])):
            ps = [p for p in parents_of[g] if p not in used]
            if ps:
                assign[g] = ps[0]
                used.update(ps)
                if len(parents_of[g]) > 1:
                    lines.append(f"E {t:g} merge {ps[0]} {' '.join(map(str, parents_of[g]))}")
            else:
                assign[g] = next_track
                lines.append(f"E {t:g} new {next_track}")
                next_track += 1
        for tr in set(prev) - used:
            lines.append(f"E {t:g} lost {tr}")
        sc = site_class(cols["pos"][te], gid, cols["pos"][typ == C], L)
        sg = site_class(cols["pos"][te], gid, cols["pos"][(typ == 1) | (typ == 2)], L)
        lines.append(f"F {t:g} {xf.get(round(t, 6), np.nan):.4f} {len(cur)} {(gid >= 0).sum()} "
                     + " ".join(map(str, sc + sg)))
        for g in sorted(cur, key=lambda g: assign[g]):
            q = ori[g]
            lines.append(f"G {t:g} {assign[g]} {len(cur[g])} {q[0]:.5f} {q[1]:.5f} {q[2]:.5f} {q[3]:.5f}")
        prev = {assign[g]: cur[g] for g in cur}
        print(f"{run.name} t {t:g} ps: {len(cur)} grains, {(gid >= 0).sum()} Te in grains", flush=True)
    out = run / f"grains_r{RMSD}_m{MIN_TE}.txt"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--stride", type=float, default=10.0, help="ps between analysed frames (dumps: every 2 ps)")
    a = ap.parse_args()
    for r in a.runs:
        track_run(r, a.stride)
