"""Collect relaxed_<frame>.data into relaxed_for_dft.xyz (extended XYZ, one frame per relaxed structure) for DFT
single points. Each frame's info: source_frame (index in cgst_test_paw.xyz), config_type, rho_dft_frame and
rho_model_300K (g/cc, the 10 ps average; the written structure is the final snapshot), P_model_bar (10 ps average)."""
import csv
from ase.io import read, write
start = {int(r["frame"]): r for r in csv.DictReader(open("start.csv"))}
rel = {int(l.split()[0]): [float(x) for x in l.split()[1:]] for l in open("relax.txt")}
out = []
for i, r in start.items():
    a = read(f"relaxed_{i}.data", format="lammps-data", Z_of_type={1: 32, 2: 51, 3: 52, 4: 6}, atom_style="atomic")
    a.info.update(source_frame=i, config_type=r["config_type"], rho_dft_frame=float(r["rho_dft_frame"]),
                  rho_model_300K=rel[i][1], P_model_bar=rel[i][3])
    a.arrays.pop("momenta", None)                     # DFT single points need positions only
    out.append(a)
write("relaxed_for_dft.xyz", out, format="extxyz")
print(len(out), "structures -> relaxed_for_dft.xyz")
