# Validation results: nozbl_paw

Allegro without ZBL, PAW data (`models/provenance.md`). All jobs on perc A100-40GB, 2026-11-13, with the G and N
compiled files (the A30 file is not built yet, so nothing here ran on an A30). The machine-written verdicts are the
`*.txt` files next to this one (`INDEX.txt`: job and time of each); run5_ep301's are in `../run5_ep301/` and its
summary in `../../RESULTS.md`, whose section numbers are used below.

**Verdict: the potential passes every gate test and matches or beats run5_ep301 against DFT.** Its glass is about as
dense as its crystal (run5_ep301: glass denser than its crystal); both differ from experiment, where the glass is
less dense.

| Test | Result | run5_ep301 |
|---|---|---|
| 1b `model_check` (job 12358679, G) | compiled vs checkpoint: max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 3.5e-11 eV/Å, max \|ΔP\| 0.005 bar: PASS. Checkpoint vs DFT on 13 frames: RMS 5.4 meV/atom, max 10.4 | RMS 6.3, max 9.7 |
| `model_select` (12358680 G, 12358681 N) | each node type picks its own file; G and N energies identical (max \|ΔE\| 0): PASS | PASS |
| `compile_check` (12358736, G) | a fresh recompile gives identical energies (max \|ΔE\| 0); bytes differ, as expected for AOTInductor: PASS | PASS |
| 1f `container` (12358739, G) | stable vs debug image: identical energies; 2.92 vs 2.91 ns/day at 333 on 1 A100: PASS | PASS |
| 1a `smoke` (12358690, G) | x0 and x10 1×1×1 finish, no lost atoms, finite output: PASS (after fixing the checker's column count, 13 → 14 since `xfracGST`; the job's outputs unchanged) | PASS |
| 1c `dt` (12358691) | NVE in the 1500 K x10 liquid, drift −0.0001 / −0.0002 / +0.0001 meV/atom/ps at 0.5 / 1 / 2 fs, all pass: **2 fs** (`DT` no longer provisional). No crash or drift from close contacts without ZBL | drift up to −0.0011 at 2 fs |
| 1h `stress_parity` (12358732) | 2403 held-out frames: pressure RMSE 1.65 kbar, mean bias −0.91 kbar, energy MAE 4.8 meV/atom | 2.60, −2.04, 6.6 |
| 1i `am_eos` (12358733) | 14 DFT EOS sets: mean \|Δρ0\| 0.42% (max 1.51%, C10 cubic), mean pressure RMSE 2.2 kbar | 0.56% (1.61%), 4.4 |
| 1g `density` (12358734) | x0 rocksalt 3×3×3 at 300 K, 0 bar: 30.451 Å³/atom, 6.224 g/cc | 30.381, 6.238 |
| `glass_relax` (12358735, N) | DFT melt-quench glasses (5.86 g/cc) relaxed at 300 K, 0 bar: 6.222 g/cc (+6.5%); DFT amorphous 6.234 (+0.8%), cubic 6.238 (+0.3%) | 6.273 (+7.3%), 6.292, 6.272 |
| 1k `dft_glass` | not run yet: needs this potential's own 10 K/ps glass (melt-quench) | CONSISTENT |
| `mq_logic` (12358737) | melt-quench input logic incl. `tmelt`, MSD gate and the gate failure: PASS (33 checks) | PASS |
| `recryst_logic` (12359106) | ramp, **ramp restart** (stop at 600 K, resume to 900 K, resume after the last restart: no gap in `ramp.dat`/`stress.dat`, restarts every 50 K, own trajectory file, read as complete), anneal + resume, halt, calibration, analysis: PASS (46 checks; the job's FAIL was the new check misreading `ramp.<T>K.restart` names, fixed and rechecked on its outputs) | PASS |
| `mq_analysis` (CPU) | analysis code known answers incl. the closest-approach check: PASS | PASS |
| `scaling` size test (12358493–97) | 333 on 1 A100 3.12 ns/day (= run5_ep301); 444 on 1 / 2 / 4 A100s 1.34 / 2.59 / 4.98 ns/day (scaling 96% / 93%), peak 34.3 / 23.3 / 11.9 GB per GPU → `NGPU` = 2 at 444 (`scaling_size.txt`) | 333: 3.13 ns/day |

Not rerun (environment, not the potential): `env_probe`, `tuning`; `a100_model` (superseded by compiling the G and
N files directly, `models/provenance.md`).

**Density of glass vs crystal.** The model's own glass density comes from the melt-quench study
(`meltquench/results/nozbl_paw/`). `glass_relax` already shows the trend: DFT's
melt-quenched glasses relax to 6.22 g/cc, the crystal's density (6.224), where run5_ep301 took them past its
crystal (6.273 vs 6.238). Recheck with `dft_glass` once the 10 K/ps glass exists.
