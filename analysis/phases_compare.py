"""RDF, bond-angle distribution (ADF) and vibrational DOS of the phases/ runs, compared with the DFT-MD of the same cells.

Stages (env/cgst-ana python; `analyze` is the heavy one, run it through Slurm):
  analyze RUN_DIR... [--exact-v] [--every N]
      per run (runs/<MODEL_ID>/<phase>_r<k>/, traj.lammpstrj from phases/in.phases) -> RUN_DIR/analysis/:
        rdf.txt           r (A) on the phase's DFT grid, total g(r), then the 10 partials (Allegro only: DFT has totals)
        adf.txt           bond angle (deg, the DFT file's bins: 90 of 2 deg, 100 of 1.8 for hex_c1), normalized density, with ADF_CUTOFFS (the DFT's);
                          header: angles per frame. adf_sbte34.txt: the same with Sb-Te 3.4 A (see SBTE_ALT)
        coord.txt         mean bonded neighbours per species with ADF_CUTOFFS
        vdos_species.txt  DoSPT (env/dospt, analysis/build_dospt.sh) with the DFT settings: velocities estimated from
                          the unwrapped positions, one group per atom, hs_formalism lin; nu (THz), total, Ge, Sb, Te, C
        vdos_species_v.txt  (--exact-v) the same from the dumped velocities, to check the estimate
      RDF and ADF use every N-th frame (default 10: 2000 of 20000); DoSPT uses every frame.
  compare [--model-id ID]
      every analysed run in phases/runs/<MODEL_ID>/ against phases/dft/<phase>/ -> phases/results/<MODEL_ID>/:
        phases_runs.txt (one row per run), phases_summary.txt (per phase, mean +- sample std over replicas),
        figures/<group>.png|pdf, figures/summary.png|pdf (the metrics of the untagged groups across phases). A run group is <phase>[_<tag>] (run directory <phase>[_<tag>]_r<k>); a tagged group
        with the same seeds as its untagged one (e.g. am_c10_eq25: EQ_PS=25, the same trajectory 20 ps later) is
        also compared replica by replica -> phases_relaxation.txt and figures/relaxation_pe.png|pdf.
  dft-check XYZ --phase P
      RDF and ADF of a DFT trajectory (extended xyz) with this code, against phases/dft/P/; the validation of the
      definitions here (the hex_gst DFT trajectory is $DFT_PHASES/../../../dospt_example/traj.xyz).

Definitions (the same for Allegro and DFT):
  pairs    every periodic image within rmax, found over the 27 neighbouring images, exact for rmax below the cell's
           smallest perpendicular width (checked)
  g(r)     ordered pairs i != j, normalized by N^2/V and the shell volume (total) or N_a N_b / V (partial a-b), the
           DFT files' convention (dft-check: N(N-1) would read 0.7% high)
  ADF      at every atom, every pair of its bonds (both within ADF_CUTOFFS[type pair]), as OVITO BondAnalysis does
  angles   adf.txt's header and adf_count_ratio give the angles per frame (DFT: the file's summed counts)
  dPE_prod production-window PE drift (eV/atom), thermo.dat: mean of the last 2 ps minus the first 2 ps
  metrics  RDF: R = sqrt(sum (g_A - g_D)^2 / sum g_D^2) on the DFT grid over 1.5-6 A; first peak (max of total g in
           2.4-3.4 A) position and height. ADF: overlap 1 - 0.5 int |p_A - p_D|; peak angle. VDOS: both smoothed with
           the same 5-point boxcar (0.25 THz), each curve normalized to unit area over 0-NU_MAX THz; overlap
           int min(p_A, p_D); mean frequency <nu>, total and per species.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PH = ROOT / "phases"
SPECIES = ("Ge", "Sb", "Te", "C")
MASS = {"Ge": 72.630, "Sb": 121.760, "Te": 127.600, "C": 12.011}
# bond cutoffs (A) of the DFT ADF files. $DFT_PHASES/*/*/coordination/compute_adf.py now say Sb-Te 3.4, but the
# hex_gst DFT ADF was made with 3.2: its own trajectory gives 1245 angles/frame and overlap 0.993 with 3.2 (file: 1240),
# 1584 and 0.952 with 3.4 (dft-check, 2026-11-16). adf_count_ratio (Allegro / DFT angles per frame) checks the others.
ADF_CUTOFFS = {("Ge", "Ge"): 3.0, ("Ge", "Sb"): 3.2, ("Ge", "Te"): 3.2, ("Sb", "Sb"): 3.2, ("Sb", "Te"): 3.2,
               ("Te", "Te"): 3.2, ("Ge", "C"): 2.5, ("Sb", "C"): 2.5, ("Te", "C"): 2.5, ("C", "C"): 2.0}
SBTE_ALT = 3.4              # A, the depot scripts' Sb-Te cutoff: every ADF is also written with it (adf_sbte34.txt),
                            #   and compare uses, per DFT file, the variant whose angles/frame match it (adf_sbte)
def adf_bins(phase):
    """The phase's DFT ADF bins: 0-180 deg in as many bins as its file has rows (90, or 100 for hex_c1)."""
    return np.linspace(0.0, 180.0, len(np.loadtxt(PH / "dft" / phase / "adf.txt")) + 1)
RDF_FIT = (1.5, 6.0)        # A, R-factor window
PEAK = (2.4, 3.4)           # A, first-peak search
NU_MAX = 60.0               # THz, VDOS normalization range (C modes reach ~50 THz)
THZ_TO_CM = 33.356
PROD_PS = 20.0              # ps, the production window (phases/params)
PHASES = ("am_gst", "am_c1", "am_c5", "am_c10", "cub_gst", "cub_c1", "hex_gst", "hex_c1")
PE_EDGE = 2.0               # ps, production PE drift: mean of the last PE_EDGE ps minus the first


def split_name(name):
    """Run directory name <phase>[_<tag>]_r<k> -> (group <phase>[_<tag>], phase, tag or '')."""
    group = name.rsplit("_r", 1)[0]
    phase = max((p for p in PHASES if group == p or group.startswith(p + "_")), key=len)
    return group, phase, group[len(phase) + 1:]


# ---------------------------------------------------------------- input
def read_cell(phase):
    """Rows a, b, c (A), origin and species of phases/structures/<phase>.data."""
    lines = (PH / "structures" / f"{phase}.data").read_text().splitlines()
    b = {"xy": 0.0, "xz": 0.0, "yz": 0.0}
    for ln in lines:
        w = ln.split()
        for d in "xyz":
            if ln.endswith(f"{d}lo {d}hi"):
                b[d] = (float(w[0]), float(w[1]))
        if ln.endswith("xy xz yz"):
            b["xy"], b["xz"], b["yz"] = map(float, w[:3])
    i = next(k for k, ln in enumerate(lines) if ln.startswith("Atoms"))
    types = np.array([int(ln.split()[1]) for ln in lines[i + 1:] if ln.strip()])
    h = np.array([[b["x"][1] - b["x"][0], 0, 0], [b["xy"], b["y"][1] - b["y"][0], 0],
                  [b["xz"], b["yz"], b["z"][1] - b["z"][0]]])
    return h, np.array([SPECIES[t - 1] for t in types])


def read_dump(path, natoms, every=1, vel=False):
    """Positions (and velocities, A/ps) of every `every`-th frame of a sorted custom dump id type xu yu zu vx vy vz."""
    per = natoms + 9
    pos, v = [], []
    with open(path) as f:
        k = 0
        while True:
            block = [f.readline() for _ in range(per)]
            if not block[0]:
                break
            if k % every == 0:
                a = np.array(" ".join(block[9:]).split(), float).reshape(natoms, -1)
                pos.append(a[:, 2:5])
                if vel:
                    v.append(a[:, 5:8])
            k += 1
    return np.array(pos), (np.array(v) if vel else None)


def read_xyz(path, every=1):
    """Positions and species of an extended-xyz trajectory (DFT, from ASE)."""
    pos, sp = [], None
    with open(path) as f:
        k = 0
        while True:
            head = f.readline()
            if not head.strip():
                break
            n = int(head)
            f.readline()
            rows = [f.readline().split() for _ in range(n)]
            if sp is None:
                sp = np.array([r[0] for r in rows])
            if k % every == 0:
                pos.append(np.array([r[1:4] for r in rows], float))
            k += 1
    return np.array(pos), sp


def read_dospt_dos(path, natoms):
    """DoSPT 'dos' file: a total block, then one block per group ('# ...' header + rows nu, dos, ...)."""
    blocks, cur = [], None
    for ln in open(path):
        if ln.lstrip().startswith("#"):
            cur = []
            blocks.append(cur)
        elif ln.strip():
            cur.append([float(x) for x in ln.split()[:2]])
    blocks = [np.array(b) for b in blocks]
    assert len(blocks) == natoms + 1, f"{path}: {len(blocks)} blocks for {natoms} atoms"
    return blocks[0][:, 0], blocks[0][:, 1], np.array([b[:, 1] for b in blocks[1:]])


def species_dos(nu, total, per_atom, species):
    return np.column_stack([nu, total] + [per_atom[species == s].sum(axis=0) for s in SPECIES])


# ---------------------------------------------------------------- structure
def min_width(h):
    v = abs(np.linalg.det(h))
    return min(v / np.linalg.norm(np.cross(h[i], h[j])) for i, j in ((1, 2), (2, 0), (0, 1)))


def pairs(x, h, rmax):
    """All (i, j, r, vector) with 0 < r < rmax over the 27 images, for one frame."""
    hinv = np.linalg.inv(h)
    d = x[None, :, :] - x[:, None, :]                # d[i, j] = x_j - x_i
    s = d @ hinv
    d = (s - np.round(s)) @ h
    shifts = np.array([[a, b, c] for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)]) @ h
    D = d[None] + shifts[:, None, None, :]
    r = np.linalg.norm(D, axis=-1)
    m = (r < rmax) & (r > 1e-6)
    _, i, j = np.nonzero(m)
    return i, j, r[m], D[m]


def rdf_adf(frames, h, sp, edges, bins, cutoffs=None):
    cutoffs = cutoffs or ADF_CUTOFFS
    rmax = max(edges[-1], max(cutoffs.values()))
    assert rmax < min_width(h), f"rmax {rmax:.2f} A >= smallest cell width {min_width(h):.2f} A"
    n, V = len(sp), abs(np.linalg.det(h))
    idx = {s: np.flatnonzero(sp == s) for s in SPECIES}
    code = np.array([SPECIES.index(s) for s in sp])
    cut = np.zeros((4, 4))
    for (a, b), c in cutoffs.items():
        cut[SPECIES.index(a), SPECIES.index(b)] = cut[SPECIES.index(b), SPECIES.index(a)] = c
    nb = len(edges) - 1
    H = np.zeros((4, 4, nb))
    A = np.zeros(len(bins) - 1)
    Z = np.zeros(4)
    for x in frames:
        i, j, r, D = pairs(x, h, edges[-1] if edges[-1] > rmax - 1e-9 else rmax)
        sel = r < edges[-1]
        np.add.at(H, (code[i[sel]], code[j[sel]], np.clip(np.searchsorted(edges, r[sel]) - 1, 0, nb - 1)), 1)
        b = r < cut[code[i], code[j]]
        bi, bD = i[b], D[b] / r[b][:, None]
        np.add.at(Z, code[bi], 1)
        order = np.argsort(bi, kind="stable")
        bi, bD = bi[order], bD[order]
        starts = np.flatnonzero(np.r_[True, bi[1:] != bi[:-1]])
        ends = np.r_[starts[1:], len(bi)]
        for s0, s1 in zip(starts, ends):
            if s1 - s0 < 2:
                continue
            u = bD[s0:s1]
            cos = u @ u.T
            iu = np.triu_indices(s1 - s0, 1)
            A += np.histogram(np.degrees(np.arccos(np.clip(cos[iu], -1, 1))), bins)[0]
    nf = len(frames)
    shell = 4 / 3 * np.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    g_tot = H.sum(axis=(0, 1)) / (nf * n * n / V * shell)
    parts, names = [], []
    for a in range(4):
        for b in range(a, 4):
            na, nb_ = len(idx[SPECIES[a]]), len(idx[SPECIES[b]])
            norm = na * nb_
            parts.append(H[a, b] / (nf * norm / V * shell) if norm else np.zeros_like(shell))
            names.append(f"{SPECIES[a]}-{SPECIES[b]}")
    adf = A / (A.sum() * np.diff(bins)) if A.sum() else A
    z = {s: Z[k] / (nf * len(idx[s])) if len(idx[s]) else np.nan for k, s in enumerate(SPECIES)}
    return g_tot, parts, names, adf, z, A.sum() / nf


def dft_grid(phase):
    d = np.loadtxt(PH / "dft" / phase / "rdf.txt")
    c = d[:, 0]
    dr = c[1] - c[0]
    return c, c[0] - dr / 2 + dr * np.arange(len(c) + 1)


def write_structure(out, phase, frames, h, sp):
    centres, edges = dft_grid(phase)
    keep = edges[1:] <= min_width(h) - 1e-6
    edges = edges[: keep.sum() + 1]
    bins = adf_bins(phase)
    g, parts, names, adf, z, nang = rdf_adf(frames, h, sp, edges, bins)
    np.savetxt(out / "rdf.txt", np.column_stack([centres[: len(g)], g, *parts]), fmt="%.6g",
               header="r_A total " + " ".join(names))
    mid = 0.5 * (bins[1:] + bins[:-1])
    np.savetxt(out / "adf.txt", np.column_stack([mid, adf]), fmt="%.6g",
               header=f"angles_per_frame {nang:.2f}\nangle_deg density_per_deg (ADF_CUTOFFS in analysis/phases_compare.py)")
    alt = {**ADF_CUTOFFS, ("Sb", "Te"): SBTE_ALT}
    *_, adf2, _, nang2 = rdf_adf(frames, h, sp, np.array([0.0, SBTE_ALT + 0.1]), bins, alt)
    np.savetxt(out / "adf_sbte34.txt", np.column_stack([mid, adf2]), fmt="%.6g",
               header=f"angles_per_frame {nang2:.2f}\nangle_deg density_per_deg (ADF_CUTOFFS with Sb-Te {SBTE_ALT})")
    (out / "coord.txt").write_text("# bonded neighbours per atom (ADF_CUTOFFS)\n"
                                   + "".join(f"{s} {z[s]:.4f}\n" for s in SPECIES))


# ---------------------------------------------------------------- VDOS
def dospt(work, frames, h, sp, dt_ps, vel=None):
    """Run DoSPT on frames (A; vel in A/ps -> exact velocities) with the DFT settings; returns species DOS."""
    exe = ROOT / "env/dospt/bin/DoSPT2"
    if not exe.exists():
        sys.exit(f"{exe} missing: bash analysis/build_dospt.sh")
    work.mkdir(parents=True, exist_ok=True)
    n, nf = len(sp), len(frames)
    lat = " ".join(f"{x:.8f}" for x in h.ravel())
    with open(work / "traj.xyz", "w") as f:
        for k in range(nf):
            f.write(f"{n}\nLattice=\"{lat}\"\n")
            if vel is None:
                f.write("".join(f"{s} {a:.8f} {b:.8f} {c:.8f}\n" for s, (a, b, c) in zip(sp, frames[k])))
            else:
                v = vel[k] / 1000.0                       # A/ps -> A/fs (DoSPT xyz convention)
                f.write("".join(f"{s} {a:.8f} {b:.8f} {c:.8f} {p:.10f} {q:.10f} {r:.10f}\n"
                                for s, (a, b, c), (p, q, r) in zip(sp, frames[k], v)))
    cell = " ".join(f"{x:.8f}" for x in (h / 10.0).ravel())      # rows a, b, c in nm (analysis/build_dospt.sh)
    (work / "input").write_text(
        f"# written by analysis/phases_compare.py\npoints = {nf}\ntau = {nf * dt_ps:g}\ncell = {cell}\n"
        f"temperature = 300\nformat = xyz\nestimate_velocities = {'.true.' if vel is None else '.false.'}\n"
        f"hs_formalism = \"lin\"\nf_opt = .false.\n")
    (work / "groups").write_text(f"{n} {n}\n" + "".join(f"1 1\n{i + 1}\n" for i in range(n)))
    (work / "supergroups").write_text(f"1-{n}\n")
    (work / "masses").write_text("".join(f"{s} {MASS[s]}\n" for s in SPECIES))
    with open(work / "dospt.log", "w") as log:
        subprocess.run([str(exe)], cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True,
                       env={**os.environ, "OMP_NUM_THREADS": os.environ.get("SLURM_CPUS_PER_TASK", "4")})
    # DoSPT prints the cell diagonal it read (L(1), L(2), L(3), nm, 3 decimals); the cell is lower triangular, so a
    # matching diagonal means the same volume, and a transposed or misread cell fails here
    line = next(ln for ln in (work / "dospt.log").read_text().splitlines() if "Cell =" in ln)
    L = np.array([float(x) for x in line.split("[")[1].split("]")[0].split(",")])
    if not np.allclose(L, np.diag(h) / 10.0, atol=6e-4):
        sys.exit(f"{work}: DoSPT read cell diagonal {L} nm, box {np.diag(h) / 10.0} nm")
    nu, total, per_atom = read_dospt_dos(work / "dos", n)
    (work / "traj.xyz").unlink()
    return species_dos(nu, total, per_atom, sp), L


def analyze(run, every, exact_v):
    phase = split_name(run.name)[1]
    h, sp = read_cell(phase)
    dt_ps = float(next(ln.split()[1] for ln in (run / "log.phases").open()     # the substituted line, not the echo
                       if ln.startswith("timestep") and "$" not in ln))
    out = run / "analysis"
    out.mkdir(exist_ok=True)
    frames, vel = read_dump(run / "traj.lammpstrj", len(sp), 1, vel=exact_v)
    write_structure(out, phase, frames[::every], h, sp)
    hdr = "nu_THz total " + " ".join(SPECIES)
    dos, vol = dospt(out / "dospt", frames, h, sp, dt_ps)
    np.savetxt(out / "vdos_species.txt", dos, fmt="%.6g", header=f"{phase} DoSPT, estimated velocities\n{hdr}")
    msg = f"{run.name}: {len(frames)} frames, dt {dt_ps} ps; DoSPT cell diagonal {vol} nm = box"
    if exact_v:
        dos_v, _ = dospt(out / "dospt_v", frames, h, sp, dt_ps, vel)
        np.savetxt(out / "vdos_species_v.txt", dos_v, fmt="%.6g", header=f"{phase} DoSPT, dumped velocities\n{hdr}")
        o = overlap(dos[:, 0], dos[:, 1], dos_v[:, 0], dos_v[:, 1])
        msg += f"; VDOS overlap estimated vs exact velocities {o:.4f}"
    print(msg, flush=True)


# ---------------------------------------------------------------- comparison
def smooth(y, k=5):
    return np.convolve(y, np.ones(k) / k, mode="same")


def unit(nu, y):
    m = nu <= NU_MAX
    y = np.where(m, smooth(y), 0.0)
    a = np.trapezoid(y, nu)
    return y / a if a > 0 else y


def overlap(nu1, y1, nu2, y2):
    p, q = unit(nu1, y1), unit(nu2, np.interp(nu1, nu2, y2))
    return float(np.trapezoid(np.minimum(p, q), nu1))


def mean_nu(nu, y):
    p = unit(nu, y)
    return float(np.trapezoid(nu * p, nu))


def metrics(phase, a_rdf, a_adf, a_dos, dft):
    r, gD = dft["rdf"][:, 0], dft["rdf"][:, 1]
    gA = np.interp(r, a_rdf[:, 0], a_rdf[:, 1], right=np.nan)
    w = (r >= RDF_FIT[0]) & (r <= RDF_FIT[1]) & np.isfinite(gA)
    pk = (a_rdf[:, 0] >= PEAK[0]) & (a_rdf[:, 0] <= PEAK[1])
    i = np.argmax(np.where(pk, a_rdf[:, 1], -1))
    wb = 180.0 / len(dft["adf"])                  # ADF bin width (deg)
    pD, aD = dft["adf"][:, 1] / (dft["adf"][:, 1].sum() * wb), a_adf[:, 1]
    assert len(aD) == len(pD), f"{phase}: ADF bins {len(aD)} vs DFT {len(pD)}: rerun analyze"
    m = {"R_rdf": float(np.sqrt(np.sum((gA[w] - gD[w]) ** 2) / np.sum(gD[w] ** 2))),
         "r1": float(a_rdf[i, 0]), "g1": float(a_rdf[i, 1]),
         "adf_overlap": float(1 - 0.5 * np.sum(np.abs(aD - pD)) * wb),
         "adf_count_ratio": float(a_adf_count(a_adf) / dft["adf"][:, 1].sum()),
         "adf_peak": float(a_adf[np.argmax(aD), 0])}
    nuA, nuD = a_dos[:, 0], dft["dos"][:, 0]
    for k, s in enumerate(("total",) + SPECIES):
        if a_dos[:, 1 + k].sum() == 0:
            continue
        m[f"S_{s}"] = overlap(nuA, a_dos[:, 1 + k], nuD, dft["dos"][:, 1 + k])
        m[f"nu_{s}"] = mean_nu(nuA, a_dos[:, 1 + k])
    return m


def a_adf_count(a_adf):
    return a_adf.angles_per_frame


class Table(np.ndarray):
    """adf.txt as an array, with angles_per_frame from its header."""


def load_adf(path):
    t = np.loadtxt(path).view(Table)
    t.angles_per_frame = float(open(path).readline().split()[-1])
    return t


def dft_metrics(phase, dft):
    r, g = dft["rdf"][:, 0], dft["rdf"][:, 1]
    pk = (r >= PEAK[0]) & (r <= PEAK[1])
    i = np.argmax(np.where(pk, g, -1))
    m = {"R_rdf": 0.0, "r1": float(r[i]), "g1": float(g[i]), "adf_overlap": 1.0, "adf_count_ratio": 1.0,
         "adf_peak": float(dft["adf"][np.argmax(dft["adf"][:, 1]), 0])}
    for k, s in enumerate(("total",) + SPECIES):
        if dft["dos"][:, 1 + k].sum() > 0:
            m[f"S_{s}"], m[f"nu_{s}"] = 1.0, mean_nu(dft["dos"][:, 0], dft["dos"][:, 1 + k])
    return m


def load_dft(phase):
    d = PH / "dft" / phase
    return {"rdf": np.loadtxt(d / "rdf.txt"), "adf": np.loadtxt(d / "adf.txt", comments="#"),
            "dos": np.loadtxt(d / "vdos_species.txt")}


def sbte_of(phase, model_id):
    """Sb-Te cutoff (3.2 or SBTE_ALT) the phase's DFT ADF file was made with: the variant whose angles per frame,
    over this model's analysed untagged runs of the phase, come closest to the file's (adf_sbte in the outputs)."""
    dft_n = load_dft(phase)["adf"][:, 1].sum()
    runs = [r for r in (PH / "runs" / model_id).glob(f"{phase}_r*") if (r / "analysis/adf_sbte34.txt").exists()]
    if not runs:
        return 3.2
    n = {v: np.mean([load_adf(r / "analysis" / f).angles_per_frame for r in runs])
         for v, f in ((3.2, "adf.txt"), (SBTE_ALT, "adf_sbte34.txt"))}
    return min(n, key=lambda v: abs(np.log(n[v] / dft_n)))


def pe_drift(run, prod_ps):
    """Production-window PE drift (eV/atom) from thermo.dat: last PE_EDGE ps minus first PE_EDGE ps."""
    t, pe = np.loadtxt(run / "thermo.dat", skiprows=1, usecols=(0, 2)).T
    t0 = t[-1] - prod_ps
    return float(pe[t > t[-1] - PE_EDGE].mean() - pe[(t >= t0) & (t < t0 + PE_EDGE)].mean())


def compare(model_id):
    runs = sorted(p for p in (PH / "runs" / model_id).glob("*_r*") if (p / "analysis/vdos_species.txt").exists())
    if not runs:
        sys.exit(f"no analysed runs in phases/runs/{model_id}/ (run the analyze stage)")
    res = PH / "results" / model_id
    (res / "figures").mkdir(parents=True, exist_ok=True)
    keys = (["dPE_prod", "adf_sbte", "R_rdf", "r1", "g1", "adf_overlap", "adf_count_ratio", "adf_peak"]
            + [f"{p}_{s}" for s in ("total",) + SPECIES for p in ("S", "nu")])
    rows, by_phase = [], {}
    for run in runs:
        group, phase, _ = split_name(run.name)
        a = run / "analysis"
        dft = load_dft(phase)
        adfs = {3.2: load_adf(a / "adf.txt"), SBTE_ALT: load_adf(a / "adf_sbte34.txt")}
        sbte = sbte_of(phase, model_id)
        data = (np.loadtxt(a / "rdf.txt"), adfs[sbte], np.loadtxt(a / "vdos_species.txt"))
        m = {"dPE_prod": pe_drift(run, PROD_PS), "adf_sbte": sbte, **metrics(phase, *data, dft)}
        rows.append((run.name, m))
        by_phase.setdefault(group, []).append((run.name, m, data))
    order = sorted(by_phase, key=lambda g: (PHASES.index(split_name(g + "_r1")[1]), g))
    head = f"# MODEL_ID {model_id}; analysis/phases_compare.py (definitions in its docstring); nu in THz\n"
    fmt = lambda m: "  ".join(f"{k} {m[k]:.4g}" for k in keys if k in m)  # noqa: E731
    (res / "phases_runs.txt").write_text(head + "".join(f"{n:16s} {fmt(m)}\n" for n, m in rows)
                                         + "".join(f"{'DFT_' + p:16s} {fmt(dft_metrics(p, load_dft(p)))}\n"
                                                   for p in order if p in PHASES))
    lines = [head]
    for p in order:
        ms = [m for _, m, _ in by_phase[p]]
        d = dft_metrics(split_name(p + "_r1")[1], load_dft(split_name(p + "_r1")[1]))
        parts = []
        for k in keys:
            v = np.array([m[k] for m in ms if k in m])
            if len(v):
                parts.append(f"{k} {v.mean():.4g} +- {v.std(ddof=1) if len(v) > 1 else np.nan:.2g}"
                             + (f" (DFT {d[k]:.4g})" if k in d and k[:2] in ("r1", "g1", "ad", "nu")
                                and k != "adf_overlap" else ""))
        lines.append(f"{p:12s} n={len(ms)}  " + "  ".join(parts) + "\n")
    (res / "phases_summary.txt").write_text("".join(lines))
    print("".join(lines))
    relaxation(res, keys, by_phase)
    figures(res / "figures", order, by_phase)
    summary_figure(res / "figures", by_phase)


def relaxation(res, keys, by_phase):
    """Each tagged group (e.g. am_c10_eq25: the same seeds, a later production window) against its untagged one,
    replica by replica: mean +- std of (tagged - untagged) per metric, and the untagged replica spread (std) for
    scale. Writes phases_relaxation.txt and figures/relaxation_pe.png|pdf (PE vs time of the tagged runs)."""
    tagged = [g for g in by_phase if split_name(g + "_r1")[2] and split_name(g + "_r1")[1] in by_phase]
    if not tagged:
        return
    lines = ["# tagged run group minus its untagged group, paired by replica (same seed): mean +- std of the"
             " difference; [spread] = sample std of the untagged replicas\n"]
    for g in tagged:
        base = split_name(g + "_r1")[1]
        A = {n.rsplit("_r", 1)[1]: m for n, m, _ in by_phase[base]}
        B = {n.rsplit("_r", 1)[1]: m for n, m, _ in by_phase[g]}
        reps = sorted(set(A) & set(B))
        parts = []
        for k in keys:
            if all(k in A[r] and k in B[r] for r in reps):
                d = np.array([B[r][k] - A[r][k] for r in reps])
                sp = np.std([A[r][k] for r in A], ddof=1) if len(A) > 1 else np.nan
                parts.append(f"{k} {d.mean():+.3g} +- {d.std(ddof=1) if len(d) > 1 else np.nan:.2g} [{sp:.2g}]")
        lines.append(f"{g} - {base} (replicas {','.join(reps)}): " + "  ".join(parts) + "\n")
    (res / "phases_relaxation.txt").write_text("".join(lines))
    print("".join(lines))
    plt = _style()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ramp = ["#86b6ef", "#5598e7", "#1c5cab", "#104281"]
    for c, g in zip(ramp, tagged):
        runs = sorted((PH / "runs" / res.name).glob(f"{g}_r*"))
        curves = [np.loadtxt(r / "thermo.dat", skiprows=1, usecols=(0, 2)) for r in runs]
        n = min(len(x) for x in curves)
        t = curves[0][:n, 0]
        pe = np.mean([x[:n, 1] for x in curves], axis=0)
        ax.plot(t, pe - pe[-50:].mean(), color=c, label=TITLE.get(split_name(g + "_r1")[1], g))
    ax.axvspan(5, 25, color=GRID, alpha=0.5, lw=0)
    ax.axvspan(25, 45, color=GRID, alpha=0.25, lw=0)
    ax.text(15, ax.get_ylim()[1] * 0.9, "standard window", ha="center", color=INK2)
    ax.text(35, ax.get_ylim()[1] * 0.9, "after 25 ps", ha="center", color=INK2)
    ax.set(ylim=(-0.01, 0.05), xlabel="time (ps)", ylabel="PE − final PE (eV/atom)",
           title="Relaxation of the amorphous DFT cells (mean of seeds)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(res / "figures" / f"relaxation_pe.{ext}", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- figures
# dataviz conventions (as meltquench/results/<MODEL_ID>/report/make_figures.py): light surface, recessive grid;
# Allegro solid in categorical slot 1 (or the species slots), DFT dashed in ink. Species: categorical slots 1-4.
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
ALLEGRO = "#2a78d6"
SPC = {"Ge": "#2a78d6", "Sb": "#eb6834", "Te": "#1baf7a", "C": "#eda100"}
TITLE = {"am_gst": "amorphous GST", "am_c1": "amorphous GST + 1.4% C", "am_c5": "amorphous GST + 5.3% C",
         "am_c10": "amorphous GST + 10% C", "cub_gst": "rocksalt GST", "cub_c1": "rocksalt GST + 1.4% C",
         "hex_gst": "trigonal GST", "hex_c1": "trigonal GST + 1.4% C"}


def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "font.size": 9,
        "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK, "axes.titlesize": 10,
        "axes.titleweight": "bold", "axes.titlelocation": "left", "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
        "lines.linewidth": 1.4, "legend.frameon": False, "legend.labelcolor": INK2})
    return plt


def _band(ax, x, ys, color, label):
    ys = np.array(ys)
    ax.plot(x, ys.mean(axis=0), color=color, label=label)
    if len(ys) > 1:
        ax.fill_between(x, ys.min(axis=0), ys.max(axis=0), color=color, alpha=0.2, lw=0)


def figures(out, order, by_phase):
    plt = _style()
    for p in order:
        group, phase, tag = split_name(p + "_r1")
        dft = load_dft(phase)
        runs = by_phase[p]
        n = len(runs)
        has_c = dft["dos"][:, 5].sum() > 0
        fig, ax = plt.subplots(2, 2, figsize=(9, 6.2))
        a = ax[0, 0]
        r = runs[0][2][0][:, 0]
        L = min(len(x[2][0]) for x in runs)
        _band(a, r[:L], [x[2][0][:L, 1] for x in runs], ALLEGRO, f"Allegro ({n} seed{'s' if n > 1 else ''}, band = range)")
        a.plot(dft["rdf"][:, 0], dft["rdf"][:, 1], "--", color=INK, label="DFT-MD")
        a.set(xlim=(1.5, 6), xlabel="r (Å)", ylabel="g(r)", title="Radial distribution (total)")
        a.set_ylim(top=1.35 * max(dft["rdf"][:, 1].max(), np.max([x[2][0][:L, 1] for x in runs])))
        a.legend(loc="upper right")
        a = ax[0, 1]
        ang = runs[0][2][1][:, 0]
        a.text(0.98, 0.95, f"Sb–Te bond < {runs[0][1]['adf_sbte']:g} Å (as the DFT file)", transform=a.transAxes,
               ha="right", va="top", color=INK2, fontsize=8)
        _band(a, ang, [x[2][1][:, 1] for x in runs], ALLEGRO, "Allegro")
        a.plot(dft["adf"][:, 0], dft["adf"][:, 1] / (dft["adf"][:, 1].sum() * 180.0 / len(dft["adf"])), "--", color=INK, label="DFT-MD")
        a.set(xlim=(40, 180), xlabel="bond angle (°)", ylabel="probability density (1/°)",
              title="Bond-angle distribution")
        a = ax[1, 0]
        nu = runs[0][2][2][:, 0]
        for k, s in enumerate(("Ge", "Sb", "Te")):
            _band(a, nu, [unit(nu, x[2][2][:, 2 + k]) for x in runs], SPC[s], s)
            a.plot(dft["dos"][:, 0], unit(dft["dos"][:, 0], dft["dos"][:, 2 + k]), "--", color=SPC[s], lw=1.1)
        a.plot([], [], "--", color=INK2, label="DFT-MD (dashed)")
        a.set(xlim=(0, 10), xlabel="frequency (THz)", ylabel="VDOS (normalized, 1/THz)",
              title="Vibrational DOS by species")
        a.legend(loc="upper right")
        sec = a.secondary_xaxis("top", functions=(lambda x: x * THZ_TO_CM, lambda x: x / THZ_TO_CM))
        sec.set_xlabel("cm⁻¹", color=INK2)
        a = ax[1, 1]
        if has_c:
            _band(a, nu, [unit(nu, x[2][2][:, 5]) for x in runs], SPC["C"], "C, Allegro")
            a.plot(dft["dos"][:, 0], unit(dft["dos"][:, 0], dft["dos"][:, 5]), "--", color=INK, label="C, DFT-MD")
            a.set(xlim=(0, 50), xlabel="frequency (THz)", ylabel="VDOS (normalized, 1/THz)",
                  title="Vibrational DOS of C")
            a.legend(loc="upper right")
        else:
            _band(a, nu, [unit(nu, x[2][2][:, 1]) for x in runs], ALLEGRO, "Allegro")
            a.plot(dft["dos"][:, 0], unit(dft["dos"][:, 0], dft["dos"][:, 1]), "--", color=INK, label="DFT-MD")
            a.set(xlim=(0, 10), xlabel="frequency (THz)", ylabel="VDOS (normalized, 1/THz)",
                  title="Vibrational DOS (total)")
            a.legend(loc="upper right")
        fig.suptitle(TITLE.get(phase, phase) + ", 300 K NVT, DFT cell"
                     + (f" ({tag.replace('eq', '')} ps equilibration)" if tag else ""),
                     x=0.01, ha="left", fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        for ext in ("png", "pdf"):
            fig.savefig(out / f"{p}.{ext}", dpi=200)
        plt.close(fig)


def summary_figure(out, by_phase):
    """The metrics across the phases (untagged groups): RDF R, ADF overlap, VDOS overlap (total and C) and the
    mean-frequency deviation from DFT per species; each seed a small dot, the mean a larger one."""
    plt = _style()
    groups = [p for p in PHASES if p in by_phase]
    y = np.arange(len(groups))[::-1]
    panels = [("RDF misfit R (0 = DFT)", [("R_rdf", ALLEGRO, None)], None),
              ("ADF overlap (1 = DFT)", [("adf_overlap", ALLEGRO, None)], None),
              ("VDOS overlap (1 = DFT)", [("S_total", ALLEGRO, "total"), ("S_C", SPC["C"], "C")], None),
              ("mean frequency vs DFT (%)", [(f"nu_{s}", SPC[s], s) for s in SPECIES], 0.0)]
    fig, ax = plt.subplots(1, 4, figsize=(11, 3.6), sharey=True)
    for a, (title, series, ref) in zip(ax, panels):
        k = len(series)
        for j, (key, color, label) in enumerate(series):
            off, labelled = (j - (k - 1) / 2) * 0.16, False
            for yi, g in zip(y, groups):
                ms = [m for _, m, _ in by_phase[g] if key in m]
                if not ms:
                    continue
                v = np.array([m[key] for m in ms])
                if ref is not None:
                    v = 100.0 * (v / dft_metrics(g, load_dft(g))[key] - 1.0)
                a.scatter(v, np.full(len(v), yi + off), s=9, color=color, alpha=0.45, lw=0)
                a.scatter([v.mean()], [yi + off], s=34, color=color, edgecolor=SURF, lw=1.0,
                          label=label if (label and not labelled) else None)
                labelled = True
        if ref is not None:
            a.axvline(ref, color=AXIS, lw=1.0, zorder=0)
        a.set_title(title)
        a.grid(axis="y", visible=False)
        if any(lab for *_, lab in series):
            a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=len(series), fontsize=8,
                     handletextpad=0.2, columnspacing=1.0)
    ax[0].set_yticks(y, [TITLE.get(g, g).replace("GST + ", "+") for g in groups])
    fig.suptitle("Allegro vs DFT-MD at 300 K, DFT cells (small dots: seeds; large: mean)", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    for ext in ("png", "pdf"):
        fig.savefig(out / f"summary.{ext}", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- DFT check
def dft_check(xyz, phase, every):
    h, sp_ref = read_cell(phase)
    frames, sp = read_xyz(xyz, every)
    assert (sp == sp_ref).all(), "species order differs from phases/structures"
    lat = open(xyz).readlines()[1]
    out = Path(os.environ.get("TMPDIR", "/tmp")) / f"phases_dftcheck_{phase}"
    out.mkdir(exist_ok=True)
    write_structure(out, phase, frames, h, sp)
    dft = load_dft(phase)
    mine, adf = np.loadtxt(out / "rdf.txt"), load_adf(out / "adf.txt")
    m = metrics(phase, mine, adf, dft["dos"], dft)
    print(f"{phase}: {len(frames)} frames of {xyz} ({lat.split('Properties')[0].strip()})")
    print(f"  RDF R vs DFT file {m['R_rdf']:.4f}; first peak {m['r1']:.3f} A, g {m['g1']:.3f}"
          f" (DFT file {dft_metrics(phase, dft)['r1']:.3f} A, {dft_metrics(phase, dft)['g1']:.3f})")
    print(f"  ADF overlap vs DFT file {m['adf_overlap']:.4f}; angles/frame ratio {m['adf_count_ratio']:.4f};"
          f" peak {m['adf_peak']:.0f} deg; outputs in {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="stage", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("runs", nargs="+", type=Path)
    a.add_argument("--every", type=int, default=10, help="frame stride for RDF/ADF (DoSPT uses every frame)")
    a.add_argument("--exact-v", action="store_true", help="also DoSPT from the dumped velocities")
    c = sub.add_parser("compare")
    c.add_argument("--model-id", default=os.environ.get("MODEL_ID", "nequip_no_zbl"))
    d = sub.add_parser("dft-check")
    d.add_argument("xyz", type=Path)
    d.add_argument("--phase", required=True)
    d.add_argument("--every", type=int, default=10)
    args = ap.parse_args()
    if args.stage == "analyze":
        for run in args.runs:
            analyze(run.resolve(), args.every, args.exact_v)
    elif args.stage == "compare":
        compare(args.model_id)
    else:
        dft_check(args.xyz, args.phase, args.every)


if __name__ == "__main__":
    main()
