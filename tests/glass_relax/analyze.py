"""Summarize in.relax: per config type, density of the DFT frame vs density after the model's NPT relaxation."""
import csv
import numpy as np
start = {int(r["frame"]): r for r in csv.DictReader(open("start.csv"))}
rel = {int(l.split()[0]): [float(x) for x in l.split()[1:]] for l in open("relax.txt")}
print(f"{'config_type':16s} {'n':>3s} {'rho_DFTframe':>13s} {'rho_model_300K':>15s} {'change_%':>9s} {'<P>_bar':>8s}")
for t in ("GST_Melt_Quench", "AM_GST_runs", "CUB_GST_runs"):
    ids = [i for i, r in start.items() if r["config_type"] == t and i in rel]
    r0 = np.array([float(start[i]["rho_dft_frame"]) for i in ids])
    r1 = np.array([rel[i][1] for i in ids])
    p = np.array([rel[i][3] for i in ids])
    print(f"{t:16s} {len(ids):3d} {r0.mean():8.3f}+-{r0.std():.3f} {r1.mean():10.3f}+-{r1.std():.3f} "
          f"{100 * (r1 / r0 - 1).mean():9.2f} {p.mean():8.1f}")
missing = [i for i in start if i not in rel]
print("frames without a result:", missing if missing else "none")
