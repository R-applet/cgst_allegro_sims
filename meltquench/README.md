# Part 2: Melt-quench

`in.meltquench` takes a 3×3×3 rocksalt cell (`structures/333/<cell>.data`) through melt and quench to an amorphous
sample at 300 K. Every stage is NPT, isotropic, 0 bar, with Nosé–Hoover damping Tdamp = 100 dt and Pdamp = 1000 dt.

**Reference limitation: the glass is as dense as the crystal.** run5_ep301 quenches amorphous GST to 6.29 g/cc,
slightly denser than its own rocksalt (6.24 at 300 K), whereas experimental a-GST is ~6–7% less dense than the
cubic phase. The model inherits this from its DFT reference: DFT's own cold melt-quenched glass in the training set
sits at 6.24 g/cc at zero pressure, with the same coordination, and the model matches it within 0.85% (about half
of that is its −2 kbar pressure bias). See `tests/RESULTS.md` 1g and 1k. Report densities, and anything that depends
on the glass–crystal density difference (crystallization strain, pressure-sensitive kinetics), as properties of
this DFT reference.

## Protocol

| Stage | T (K) | Duration | Purpose / output |
|---|---|---|---|
| 0 | minimize, then 300 | 20 ps | equilibrate the crystal |
| 1 | 300 → 1500 | 120 ps (10 K/ps) | apparent Tm from the enthalpy jump (superheated, an upper bound) |
| 2 | 1500 | `hold_ps` = 100 ps, the same for every run | **MSD gate**, checked 20 ps before the end: every species, C included, must have MSD ≥ 100 Å² within the hold (about 10 Å travelled). This erases memory of the crystal and of the C pattern repeated by the 3×3×3 replication. A run that fails stops with an ERROR before the quench; rerun *every* composition with a longer hold (`HOLD_PS`). Gate result → `gate.txt`. Liquid RDF over the last 20 ps → `rdf_1500K.dat`, `liquid_1500K.data` |
| 3 | 1500 → 300 | 1200/qrate ps, in 100 K segments | `snap_<T>K.data` at 1400 … 300 K |
| 4 | 300 | 100 ps | 50 ps relaxation, then RDF and coordination averaged over 50 ps → `rdf_300K.dat`, `amorphous_300K.data` (input to Part 3) |

**Why these choices**
- **1500 K melt.** The model's perfect crystal melts at about 1090 K when heated at 2 K/ps (reference run
  `md_npt_cubic_gst`). Experimental Tm is about 900 K. At 1500 K the liquid is fast: MSD grows at 7.5–9 Å²/ps for Ge/Sb/Te in
  the reference `md_meltquench` run (380–450 Å² after 50 ps), so the gate is normally met well within 80 ps.
  C diffusion is not known in advance, which is why the gate includes it.
- **A fixed hold, not one extended until the gate passes.** An adaptive hold would give a slow composition a
  longer melt than the others, and anything that evolves in the melt (C clustering, for one) would then differ
  between compositions for a reason that is not composition. So every run has the same hold, and the gate is a
  check that it was long enough.
- **10 K/ps quench.** This is the usual MLP/AIMD rate for GST and matches the reference run. The **1 K/ps
  sensitivity runs** (x0 and x10, one replica each) show how much the amorphous structure, density and Tg depend
  on rate. The 10 K/ps glasses already read `xfrac` ≈ 0.15 at 300 K, from persistent crystal-like patches
  (`recryst/README.md`, "Crystal-like order already in the glass"). A 1 K/ps glass well above that baseline, with a
  crystalline fraction that rises during the quench, means partial crystallization, which is itself a result for
  the C-free composition.
- **3 replicas per composition**, each with a different velocity seed, give error bars that cover sample-to-sample
  variation of the glass.

## On-the-fly output
| File | Interval | Contents |
|---|---|---|
| `mq.dat` | 1 ps | T, P, V/atom, ρ, PE/atom, H/atom, per-species MSD (from step 0), crystalline fraction (`common/in.analysis`) |
| `traj.lammpstrj.gz` | every 10 K on the ramps (1 ps heating; 10/qrate ps quench), 5 ps on the holds | id, type, x, y, z, per-atom q4 and crystal-like bond count |
| `rdf_1500K.dat`, `rdf_300K.dat` | one averaged block each | total g(r) and 10 partials with running coordination, 0–6 Å in 0.02 Å bins |
| `gate.txt` | once | `hold_ps`, the smallest per-species MSD in the hold, the gate it was compared with, and `passed` (0: the run stopped there with an ERROR in `log.mq`) |
| `mq.restart.a`, `.b` | every 50 ps, alternating | rolling restart files, for manual recovery only |
| `stages.txt` | once | actual heating and quench start and end times (ps). Each RDF window is preceded by up to one window of padding (`common/in.rdf`), so stages 2 and 4 can run up to 20 and 50 ps longer than the table above |

Coordination numbers use fixed bond cutoffs: 3.2 Å between Ge/Sb/Te (the common a-GST choice), 2.5 Å for C–Ge/Sb/Te
and 1.9 Å for C–C. Each C cutoff sits in the empty gap after its bonding peak. The first g(r) minimum is not used:
in the 10 K/ps glass, Te–Te has no bonding peak, and Ge–Te and Sb–Te tail off with no minimum before the second
shell, so first-minimum CNs come out at 6–11. Override with `--rc PAIR=R` (both analysis scripts).

Per-atom coordination is not dumped. One `coord/atom` cutoff cannot serve both bond families, so
`analysis/mq_structure.py` computes it from the dumped positions, with the same cutoff table.

**C cutoffs, checked on the production x10 glasses** (they were set on the small, 12 ps logic-test glass): kept.
In all three 10 K/ps x10 glasses and the 1 K/ps one, g_CC(1.9 Å) = 0.000. At 2.5 Å, g is 0.05–0.09 for Ge–C and
Sb–C and ≤ 0.007 for Te–C, on the tail of peaks at 2.0 and 2.2 Å. Moving the cutoff to 2.4 or 2.6 Å changes the
C coordination of Ge by ≤ 2% and of Sb by 4–6%.

## Running
```
cd meltquench
sbatch --array=0-14 submit.sh                         # 10 K/ps: 5 cells x 3 replicas
sbatch --array=0,12 --export=ALL,QRATE=1 submit.sh    # 1 K/ps: x0 r1, x10 r1
# the same on one perc A100-40GB per run instead of 2 A30s (sbatch options override the #SBATCH lines):
sbatch -A perc -p a100-40gb --gpus-per-node=1 --ntasks-per-node=1 --array=0-14 submit.sh
python ../analysis/mq_summary.py --out summary runs/*      # with env/cgst-ana active
python ../analysis/mq_structure.py --out summary runs/*
```
Array index i → cell `(x0 x1 x2p5 x5 x10)[i/3]`, replica `i%3+1`; runs go to `runs/<cell>_q<qrate>_r<rep>/`.
strachan's 6-GPU A30 cap runs at most 3 of these jobs at once. One A100 gives 2.9–3.1 ns/day, close to the 3.35
ns/day of 2 A30s (`tests/RESULTS.md` 1d), so the perc queue roughly doubles throughput. `common/defaults.sh`
picks the right compiled model on either node type, and `submit.sh` passes `$SLURM_NTASKS` GPUs to LAMMPS.
Each run fits in one wall-time window: about 3–5 h at 10 K/ps and 11–13 h at 1 K/ps for 13.8k atoms on 2 A30s
(3.35 ns/day, `tests/RESULTS.md` 1d), against a 1-day limit. So a failed run is normally rerun from scratch. For
manual recovery, `snap_<T>K.data` marks each 100 K of the quench, and `mq.restart.a/b` hold the last two 50 ps
points of any stage. Resuming from them needs a hand-edited input that starts at the right stage.

`analysis/mq_summary.py` reports, per run and as replica mean ± sample std (NaN for a single replica):
- apparent Tm;
- liquid and amorphous density;
- Tg (bilinear V(T) fit on the quench);
- the crystalline fraction left at 300 K;
- the hold length, with a WARNING if the runs do not all share one;
- partial coordination numbers (CN_ij, j atoms around an i atom) and each species' total coordination Z_i;
- with `--out`: `<group>_curves.dat`, ρ(T) and H(T) on the heating ramp and the quench, in 10 K bins.

`analysis/mq_structure.py` analyses the trajectory frames of the final 50 ps at 300 K and writes, per group, the
replica mean ± sample std of:
- `_zdist.dat`: the distribution of each species' total coordination Z;
- `_angles.dat`: the bond-angle distribution per centre species;
- `_sq.dat`: Faber–Ziman partial S_ij(q) and Bhatia–Thornton S_NN(q), from g(r) out to 15 Å with a Lorch window;
- `_cmotifs.dat`: each C atom's bonded-neighbour formula (e.g. Ge2Te1C1);
- `_cclusters.dat`: the fraction of C atoms in C–C clusters of each size.

## Results (production, 2026-11-10)
Written up with figures in `report/`: `part2_results.md`, `part2_report.pdf` (LaTeX source alongside) and
`part2_slides.pptx`, all rebuilt from `results/` and `runs/` by the scripts there.

17 runs, all past the MSD gate with `hold_ps` = 100: 3 replicas at 10 K/ps for each composition, and one at 1 K/ps
for x0 and x10. `python analysis/mq_summary.py --out meltquench/results meltquench/runs/*_q*_r*` (output in
`meltquench/results/`). Mean ± sample std over the 3 replicas at 10 K/ps:

| x (at.% C) | ρ_liquid, 1500 K (g/cc) | ρ_glass, 300 K (g/cc) | Tm_app (K) | Tg (K) | xfracGST, 300 K |
|---|---|---|---|---|---|
| 0 | 5.524 ± 0.001 | 6.289 ± 0.004 | 1129 ± 2 | 807 ± 26 | 0.155 ± 0.006 |
| 1 | 5.524 ± 0.001 | 6.277 ± 0.003 | 1128 ± 13 | 780 ± 22 | 0.144 ± 0.008 |
| 2.5 | 5.514 ± 0.001 | 6.260 ± 0.001 | 1117 ± 5 | 833 ± 53 | 0.139 ± 0.002 |
| 5 | 5.493 ± 0.000 | 6.221 ± 0.002 | 1077 ± 26 | 757 ± 45 | 0.133 ± 0.009 |
| 10 | 5.444 ± 0.002 | 6.148 ± 0.002 | 984 ± 35 | 815 ± 57 | 0.143 ± 0.010 |

- **Density falls with C**, in the liquid by 1.4% and in the glass by 2.2% from x0 to x10, steadily and well outside
  the replica spread. The x0 glass (6.29) is denser than the model's own crystal (6.24), the reference limitation at
  the top of this file.
- **The apparent melting point falls with C** above 2.5%: 1129 K for x0, 1077 K for x5 and 984 K for x10. It is a
  superheating limit on a 10 K/ps ramp, an upper bound on Tm, and its replica spread grows with C (± 26–35 K).
- **Tg shows no trend.** The bilinear fit scatters by 20–60 K between replicas, more than any difference between
  compositions. A 10 K/ps quench with 3 replicas does not resolve the effect of C on Tg.
- **Crystal-like order in the glass** (`xfracGST`, Ge/Sb/Te atoms, default criterion 3.6/0.5/4) falls slightly with C,
  from 0.155 to 0.133 at x5. x10 reads 0.143, but it is the vacancy-free endpoint, so it differs in more than C. The
  all-atom `xfrac` that `mq_summary.py` prints as `xfrac_a` reads x10 at 0.194, because C atoms add false positives
  (`recryst/README.md`, "What is counted"). Use `xfracGST`.
- **Coordination** at 300 K (cutoffs above): Ge 4.49 → 4.43, Sb 3.86 → 3.80, Te 3.03 → 2.90 from x0 to x10. C is
  3.70-coordinated in x1 and 3.02 in x10. C–C bonds per C rise from 0.34 (x1) to 1.84 (x10): at 10% C most C atoms
  bond to other C. Per Ge atom there are 0.40 C neighbours in x10, against 0.12 per Sb and 0.03 per Te.
- **1 K/ps partially crystallizes.** `xfracGST` at 300 K is 0.28 (x0) and 0.26 (x10), against 0.13–0.16 at 10 K/ps,
  and it rises during the quench: x0 at 1 K/ps goes from 0.12 at 600 K to 0.27 at 400 K, while at 10 K/ps it goes
  from 0.085 to 0.13. So the 1 K/ps runs are partly crystallized glasses, not more relaxed ones, and Part 3 starts
  from the 10 K/ps glasses. Slower quenching also clusters C further: C–C bonds per C 2.32 at 1 K/ps against 1.84.
  Glass density barely moves with rate (x0 6.283 against 6.289; x10 6.151 against 6.148).

**Structure** (`analysis/mq_structure.py --out meltquench/results meltquench/runs/*_q*_r*`, job 12309964, last 50 ps
at 300 K; per-group tables in `meltquench/results/`). Coordination agrees with `mq_summary.py` to ±0.01.
- **C clusters with C content.** The fraction of C atoms bonded to another C rises from 0.30 (x1) through 0.63 (x2p5)
  and 0.80 (x5) to 0.91 (x10). Sizes grow with it: in x1 the largest C cluster has 4 atoms; in x10, 75% of C sits in
  clusters of 10 or more, up to 129 atoms. So at 10% C, carbon forms an extended network inside the glass, not
  dispersed dopant atoms.
- **C motifs.** In x1 the most common C environments are Ge- and Sb-rich (Ge₃Sb 19%, Ge₂C 13%, Ge₂Sb₂ 12%). In x10
  they are C-rich: C₃ 22%, GeC₂ 21%, C₂ 15%.
- **Ge bond angles stay mostly octahedral-like.** The distribution peaks at 91–93° for every composition. The share
  between 100 and 120° (tetrahedral-like) rises with C, from 0.19 in x0 to 0.25 in x10, while 80–100° falls from 0.54
  to 0.48.
- **Rate.** The 1 K/ps glasses are more octahedral (x0: 0.57 in 80–100°) and more C-clustered (x10: 95% of C in
  clusters of 10 or more, the largest 286 atoms), consistent with their partial crystallization and further C
  segregation.

## Validation
Both tests write a `RESULT.txt` with one PASS/FAIL line per check (`tests/collect.sh` prints them).

**`tests/mq_logic`: PASS** (job 12278869, with the `xfracGST` column). The full input runs on the 1×1×1 x0 (461 atoms) and x10 (512) cells with
every duration ×0.1, plus `x0_gatefail`: x0 with an unreachable gate (`gate_A2 1e9`). `check.py` runs at the end of
the job and verifies:
- every output file, including both restart files;
- 12 quench snapshots, and one RDF block per file;
- the four `stages.txt` times in order, with the temperature at each matching the schedule;
- `gate.txt` (`passed 1`) and exit status 0;
- that `mq_summary.py` and `mq_structure.py` run on the outputs, and that their two independent Z_i (RDF running
  coordination; bond counting on the trajectory) agree within 0.15 (measured: within 0.06);
- x0_gatefail: exit status non-zero, `passed 0`, the gate ERROR in `log.mq`, no quench, and the analysis scripts
  skip it naming the failed gate.

The 12 ps ramps on these small cells make Tm_app, Tg (NaN: under 20 quench points) and the structure numbers
meaningless; the test checks the logic only. With the uncalibrated default Q4 criterion, the glasses read
xfrac ≈ 0.1, the false-positive level the Part 3 calibration has to remove.

**`tests/mq_analysis`: PASS.** Independent checks of the analysis code:
- against Rushik's 10 K/ps reference glass (`md_meltquench`, 7200 atoms): partial g(r) matches his own g(r) from
  the same frames (peak shifts ≤ 0.11 Å, g → 1 at 14–15 Å); S_NN(q) peaks at 2.14 and 3.26 Å⁻¹, where amorphous
  GST's peaks sit; the Tg fit on its 121-point quench gives 675 K;
- known answers: on the perfect rocksalt lattice every Ge/Sb has Z = 6, the mean Z_Te equals
  6 (N_Ge + N_Sb)/N_Te exactly, and bond angles fall only at 90° and 180° (180° fraction 0.2); a toy C cell gives
  the exact cluster sizes, motifs and chain angle. Breaking the bond-vector sign in the angle code fails the toy
  cell check;
- replica statistics: the sample std (ddof 1) of 1, 2, 3 is 1, and a single value gives NaN.

The reference data are frozen copies in `tests/mq_analysis/ref/` (sources and sha256s in `ref/SHA256SUMS`).

**`tests/dft_glass`: CONSISTENT** (`tests/RESULTS.md` 1k). The model glass against DFT's own cold melt-quenched glass,
with the same code: density +0.85%, every mean Z within 0.08.

**Bugs this test has caught (all fixed):** the MSD-gate `min()`; first-minimum CNs (Te–Te ≈ 10, and Sb–Te ≈ 7 in
x10; now fixed cutoffs); repeated `mq.dat` rows breaking `np.gradient`; stage windows computed from the schedule
instead of `stages.txt`.
