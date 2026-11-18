# Validation results: nequip_no_zbl

Allegro without ZBL, PAW data (`models/provenance.md`; named `nozbl_paw` when these tests ran, so their logs and some
`RESULT*.txt` use that name). All jobs on perc A100-40GB, 2026-11-13, with the G and N
compiled files, except the later `model_select` checks of the K (alta) and A30 files. The machine-written verdicts are the
`*.txt` files next to this one (`INDEX.txt`: job and time of each). The test labels and pass criteria are in
`../../RESULTS.md`.

**Verdict: the potential passes every gate test.** Its glass is about as dense as its crystal, unlike experiment,
where the glass is less dense; DFT's own cold glass behaves the same way (1k).

| Test | Result |
|---|---|
| 1b `model_check` (job 12358679, G) | compiled vs checkpoint: max \|ΔE\| 0.0000 meV/atom, max \|ΔF\| 3.5e-11 eV/Å, max \|ΔP\| 0.005 bar: PASS. Checkpoint vs DFT on 13 frames: RMS 5.4 meV/atom, max 10.4 |
| `model_select` (12358680 G, 12358681 N; 12383792 K, alta; 12384204 A30 b-node) | each node type picks its own file; A30, G, N and K energies identical (max \|ΔE\| 0): PASS |
| `compile_check` (12358736, G) | a fresh recompile gives identical energies (max \|ΔE\| 0); bytes differ, as expected for AOTInductor: PASS |
| 1f `container` (12358739, G) | stable vs debug image: identical energies; 2.92 vs 2.91 ns/day at 333 on 1 A100: PASS |
| 1a `smoke` (12358690, G) | x0 and x10 1×1×1 finish, no lost atoms, finite output: PASS (after fixing the checker's column count, 13 → 14 since `xfracGST`; the job's outputs unchanged) |
| 1c `dt` (12358691) | NVE in the 1500 K x10 liquid, drift −0.0001 / −0.0002 / +0.0001 meV/atom/ps at 0.5 / 1 / 2 fs, all pass: **2 fs** (`DT` no longer provisional). No crash or drift from close contacts without ZBL |
| 1h `stress_parity` (12358732) | 2403 held-out frames: pressure RMSE 1.65 kbar, mean bias −0.91 kbar, energy MAE 4.8 meV/atom |
| 1j `am_eos` (12358733) | 14 DFT EOS sets: mean \|Δρ0\| 0.42% (max 1.51%, C10 cubic), mean pressure RMSE 2.2 kbar |
| 1g `density` (12358734) | x0 rocksalt 3×3×3 at 300 K, 0 bar: 30.451 Å³/atom, 6.224 g/cc |
| 1i `glass_relax` (12358735, N) | DFT melt-quench glasses (5.86 g/cc) relaxed at 300 K, 0 bar: 6.222 g/cc (+6.5%); DFT amorphous 6.234 (+0.8%), cubic 6.238 (+0.3%) |
| 1k `dft_glass` (CPU, x0 r1 glass of job 12359216, `make_model_glass.py`) | **CONSISTENT**: model glass 6.236 g/cc vs DFT coldest-20 frames 6.235 (+0.01%), max \|ΔZ\| 0.14 (Z_Sb 3.80 vs 3.93; criterion 0.15) |
| `mq_logic` (12358737) | melt-quench input logic incl. `tmelt`, MSD gate and the gate failure: PASS (33 checks) |
| `recryst_logic` (12359106) | ramp, **ramp restart** (stop at 600 K, resume to 900 K, resume after the last restart: no gap in `ramp.dat`/`stress.dat`, restarts every 50 K, own trajectory file, read as complete), anneal + resume, halt, calibration, analysis: PASS (46 checks; the job's FAIL was the new check misreading `ramp.<T>K.restart` names, fixed and rechecked on its outputs) |
| `mq_analysis` (CPU) | analysis code known answers incl. the closest-approach check; since 2026-11-18 its reference glass is this potential's x0 r1 glass (partial g(r) from the frames vs LAMMPS's: max \|Δg\| ≤ 0.11; Tg 810 K): PASS |
| 1d `scaling` size test (12358493–97) | 333 on 1 A100 3.12 ns/day; 444 on 1 / 2 / 4 A100s 1.34 / 2.59 / 4.98 ns/day (scaling 96% / 93%), peak 34.3 / 23.3 / 11.9 GB per GPU → `NGPU` = 2 at 444 (`scaling_size.txt`) |

Not rerun (environment, not the potential): `env_probe`, `tuning`; `a100_model` (superseded by compiling the G and
N files directly, `models/provenance.md`).

**Density of glass vs crystal (decided here, RUNBOOK B).** This potential's 10 K/ps x0 glass is 6.239 g/cc
(`meltquench/results/nequip_no_zbl/`), its rocksalt crystal 6.224 g/cc: the glass is as dense as the crystal (+0.2%),
unlike experiment (glass 6–7% lighter); `dft_glass` shows
that this matches the DFT reference's own cold glass, so it is a property of the reference. Report densities and
anything sensitive to the glass–crystal density difference (crystallization strain) with that caveat.
