"""Test 1a verdict: check the pass criteria of in.smoke for each cell and write RESULT.txt.

Per cell (x0, x10):
  log       log.smoke_<cell> ends with "Total wall time", contains no "ERROR" and no "Lost atoms"
  dat       smoke_<cell>.dat: >= 2 data rows, every row has 13 finite columns, PE finite
  msdC      x0 (no C): msdC column is exactly 0; x10: msdC > 0 at the end
  rdf       rdf_<cell>.dat: exactly one block of 300 rows x 24 columns, all finite, total g(r) not all zero
  dump      smoke_<cell>.lammpstrj.gz readable, last frame has c_q4[1] and c_ncb columns
Usage: python check_smoke.py [dir]   (default: this script's directory). Exit status 1 on any failure.
"""
import gzip
import sys
from pathlib import Path

import numpy as np

D = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent


def check(cell):
    errs = []
    log = (D / f"log.smoke_{cell}").read_text()
    if "Total wall time" not in log:
        errs.append("log: run did not finish")
    if "ERROR" in log or "Lost atoms" in log:
        errs.append("log: ERROR or Lost atoms")
    dat = np.loadtxt(D / f"smoke_{cell}.dat", skiprows=1, ndmin=2)
    if dat.shape[0] < 2 or dat.shape[1] != 13 or not np.isfinite(dat).all():
        errs.append(f"dat: shape {dat.shape} or non-finite values")
    elif cell == "x0" and np.any(dat[:, 11] != 0):
        errs.append("dat: msdC non-zero without C")
    elif cell != "x0" and not dat[-1, 11] > 0:
        errs.append("dat: msdC not > 0 with C")
    rows = [l.split() for l in (D / f"rdf_{cell}.dat").read_text().splitlines() if l and not l.startswith("#")]
    headers = [r for r in rows if len(r) == 2]
    block = np.array([[float(v) for v in r] for r in rows if len(r) == 24])
    if len(headers) != 1 or block.shape != (300, 24) or not np.isfinite(block).all() or not block[:, 2].any():
        errs.append(f"rdf: {len(headers)} blocks, shape {block.shape}")
    with gzip.open(D / f"smoke_{cell}.lammpstrj.gz", "rt") as f:
        heads = [l for l in f if l.startswith("ITEM: ATOMS")]
    if not heads or "c_q4[1]" not in heads[-1] or "c_ncb" not in heads[-1]:
        errs.append("dump: missing frames or q4 columns")
    return errs


ok = True
lines = []
for cell in ("x0", "x10"):
    try:
        errs = check(cell)
    except (OSError, ValueError) as e:
        errs = [f"unreadable output: {e}"]
    ok &= not errs
    lines.append(f"{cell}: {'PASS' if not errs else 'FAIL: ' + '; '.join(errs)}")
lines.append("PASS" if ok else "FAIL")
print("\n".join(lines))
if len(sys.argv) == 1:
    (D / "RESULT.txt").write_text("\n".join(lines) + "\n")
sys.exit(0 if ok else 1)
