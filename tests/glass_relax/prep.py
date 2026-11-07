"""Write held-out DFT frames as LAMMPS data files for in.relax: up to 12 frames per config type, evenly spaced in file
order, from GST_Melt_Quench (DFT glasses), AM_GST_runs (DFT amorphous) and CUB_GST_runs (crystal control).
Also writes frames.txt (frame ids) and start.csv (config type, natoms, DFT-frame density in g/cc)."""
import csv
from ase.io import iread, write
TESTSET = "/depot/prism/data/rushik/CGST/cgst_test_paw.xyz"
TYPES = ["GST_Melt_Quench", "AM_GST_runs", "CUB_GST_runs"]
idx = {t: [] for t in TYPES}
frames = {}
for i, a in enumerate(iread(TESTSET)):
    t = a.info.get("config_type")
    if t in idx:
        idx[t].append(i)
        frames[i] = a
rows = []
for t, ii in idx.items():
    step = max(1, len(ii) // 12)
    for i in ii[::step][:12]:
        a = frames[i]
        write(f"frame_{i}.data", a, format="lammps-data", specorder=["Ge", "Sb", "Te", "C"], masses=True,
              atom_style="atomic")
        rho = a.get_masses().sum() * 1.66053907 / a.get_volume()
        rows.append({"frame": i, "config_type": t, "natoms": len(a), "rho_dft_frame": round(rho, 4)})
with open("start.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
open("frames.txt", "w").write(" ".join(str(r["frame"]) for r in rows) + "\n")
print(len(rows), "frames")
