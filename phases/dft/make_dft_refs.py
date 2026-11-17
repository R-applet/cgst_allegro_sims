"""Build phases/dft/<phase>/ from the DFT outputs of the preliminary phases work (run once; outputs are tracked).

    source common/model.sh && env/cgst-ana/bin/python phases/dft/make_dft_refs.py

Per phase, from $DFT_PHASES/<amorph|cubic|hex>/<gst|c1|c5|c10>/:
  rdf.txt           coordination/*_dft_rdf.txt as is: total g(r), columns r (A), g. Grids differ by phase (bin 0.05 A to
                    10 A for amorphous, 0.03 or 0.006 A to 6 A for the crystals); compare on this grid.
  adf.txt           coordination/*_dft_adf.txt as is: OVITO BondAnalysis histogram (90 bins of 2 deg, frame-averaged
                    counts). Bond cutoffs: compute_adf.py's, except Sb-Te 3.2 A, not its 3.4 (shown for hex_gst
                    from its DFT trajectory; ADF_CUTOFFS in analysis/phases_compare.py).
  dospt_input.txt   vibdos/input, the DoSPT settings the DFT DOS was made with (for the record).
  vdos_species.txt  the DoSPT per-atom DOS (*_dft_dos, one group per atom, 46-51 MB) reduced to nu (THz), total,
                    Ge, Sb, Te, C: the per-atom blocks summed by species, species from phases/structures/<phase>.data
                    (same atom order). The file's own total block is kept as "total" and checked against the sum.
                    The preliminary plot_dos.py scripts sum Sb and Te one block early (Sb = atoms 32-63, Te =
                    64-143); their per-species curves are off by one atom, these are not (checked 2026-11-16).
  SOURCES.txt       source paths and sha256.
"""
import hashlib
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STRUCT = HERE.parent / "structures"
# phase -> (directory under $DFT_PHASES, file stem); the DOS sits in vibdos/ for hex, one level up otherwise
PH = {"am_gst": ("amorph/gst", "gst_am"), "am_c1": ("amorph/c1", "c1_am"), "am_c5": ("amorph/c5", "c5_am"),
      "am_c10": ("amorph/c10", "c10_am"), "cub_gst": ("cubic/gst", "gst_cub"), "cub_c1": ("cubic/c1", "c1_cub"),
      "hex_gst": ("hex/gst", "gst_hex"), "hex_c1": ("hex/c1", "c1_hex")}
SPECIES = ("Ge", "Sb", "Te", "C")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def types_of(phase):
    lines = (STRUCT / f"{phase}.data").read_text().splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith("Atoms"))
    return np.array([int(ln.split()[1]) for ln in lines[i + 1:] if ln.strip()])


def read_dospt_dos(path, natoms):
    """DoSPT 'dos' file: a total block, then one block per group, each '# ...' header + rows nu, dos, ..."""
    blocks, cur = [], None
    for ln in path.open():
        if ln.lstrip().startswith("#"):
            cur = []
            blocks.append(cur)
        elif ln.strip():
            cur.append([float(x) for x in ln.split()[:2]])
    blocks = [np.array(b) for b in blocks]
    assert len(blocks) == natoms + 1, f"{path}: {len(blocks)} blocks for {natoms} atoms"
    assert all(len(b) == len(blocks[0]) and np.allclose(b[:, 0], blocks[0][:, 0]) for b in blocks)
    return blocks[0][:, 0], blocks[0][:, 1], np.array([b[:, 1] for b in blocks[1:]])


def main():
    root = Path(os.environ.get("DFT_PHASES") or sys.exit("DFT_PHASES not set: source common/model.sh"))
    for phase, (d, stem) in PH.items():
        src = root / d
        dos = src / f"{stem}_dft_dos"
        if not dos.exists():
            dos = src / "vibdos" / f"{stem}_dft_dos"
        files = {"rdf.txt": src / "coordination" / f"{stem}_dft_rdf.txt",
                 "adf.txt": src / "coordination" / f"{stem}_dft_adf.txt",
                 "dospt_input.txt": src / "vibdos" / "input"}
        out = HERE / phase
        out.mkdir(exist_ok=True)
        for name, p in files.items():
            (out / name).write_bytes(p.read_bytes())
        t = types_of(phase)
        nu, total, per_atom = read_dospt_dos(dos, len(t))
        sp = np.array([per_atom[t == k + 1].sum(axis=0) for k in range(4)])
        rel = np.abs(sp.sum(axis=0) - total).max() / total.max()
        hdr = (f"{phase}: DFT DoSPT DOS (1/ps) reduced by species from {dos} (phases/dft/make_dft_refs.py)\n"
               f"max |sum of species - file total| / max(total) = {rel:.2e}\nnu_THz total " + " ".join(SPECIES))
        np.savetxt(out / "vdos_species.txt", np.column_stack([nu, total, *sp]), fmt="%.6g", header=hdr)
        (out / "SOURCES.txt").write_text("".join(f"{n:17s} {p}  sha256 {sha(p)}\n"
                                                 for n, p in {**files, "vdos (reduced)": dos}.items()))
        print(f"{phase:8s} nu 0-{nu[-1]:.0f} THz ({len(nu)} pts)  species sum vs total {rel:.1e}"
              f"  rdf rows {len(np.loadtxt(files['rdf.txt']))}")


if __name__ == "__main__":
    main()
