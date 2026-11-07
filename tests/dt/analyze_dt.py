"""Test 1c analysis: total-energy drift and fluctuation in NVE for each timestep (files nve_dt*.dat).

Usage: python analyze_dt.py [dir]   (default: this script's directory; e.g. seed2/ for the repeat)

Thresholds were fixed before the test ran. They are conventional choices, not derived from a requirement:
  DRIFT_MAX  0.05 meV/atom/ps: 5 meV/atom per 100 ps with no thermostat, about 4% of kT at 1500 K (129 meV).
             Production is thermostatted (Tdamp = 100 dt), so this bounds how hard the thermostat must work.
  RATIO_MAX  std(E_tot, detrended) / std(PE) <= 0.01: integration error at least 100x smaller than the physical
             potential-energy fluctuation (the usual Verlet stability rule of thumb).
Margins are reported as threshold / observed (larger = safer); dt passes when both margins are >= 1.
"""
import sys
from pathlib import Path

import numpy as np

DRIFT_MAX = 0.05     # meV/atom/ps
RATIO_MAX = 0.01

HERE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
print(f"{'dt_fs':>6s} {'T_mean':>7s} {'drift_meV/at/ps':>16s} {'margin':>7s} {'std(Etot)/std(PE)':>18s} "
      f"{'margin':>7s} {'pass':>5s}")
for f in sorted(HERE.glob("nve_dt*.dat"), key=lambda p: float(p.stem[6:])):
    t, T, pe, et = np.loadtxt(f, skiprows=1, unpack=True)
    fit = np.polyfit(t, et, 1)
    drift = 1e3 * fit[0]
    ratio = np.std(et - np.polyval(fit, t)) / np.std(pe)
    m_drift, m_ratio = DRIFT_MAX / max(abs(drift), 1e-12), RATIO_MAX / ratio
    ok = m_drift >= 1 and m_ratio >= 1
    print(f"{1e3 * float(f.stem[6:]):6.1f} {T.mean():7.1f} {drift:16.4f} {m_drift:7.1f} {ratio:18.4f} "
          f"{m_ratio:7.1f} {'yes' if ok else 'no':>5s}")
