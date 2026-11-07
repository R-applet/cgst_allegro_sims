"""Tests 1d/1e: tabulate timed-run throughput from log.<partition>_g<n>_ana<0|1>."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
pat = re.compile(r"Performance: ([\d.]+) ns/day.*?([\d.]+) timesteps/s, ([\d.]+) katom-step/s")
print(f"{'run':22s} {'ns/day':>8s} {'steps/s':>8s} {'katom-step/s':>13s}")
for log in sorted(HERE.glob("log.*")):
    perf = pat.findall(log.read_text())
    if len(perf) >= 2:                       # second Performance line = the timed run
        nsd, sps, kas = perf[1]
        print(f"{log.name[4:]:22s} {float(nsd):8.2f} {float(sps):8.1f} {float(kas):13.1f}")
    else:
        print(f"{log.name[4:]:22s} incomplete")
