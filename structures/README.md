# Structures

| File | What | Tracked |
|---|---|---|
| `x0_461.data`, `x1_466.data`, `x2p5_473.data`, `x5_486.data`, `x10_512.data` | the cleaned single rocksalt cells (8×8×8 sites, 3.015 Å grid, 24.12 Å box), named by atom count: the reference crystal structures and the source of every supercell | yes |
| `build_supercells.py` | replicates them: `--nrep N` writes `NNN/<tag>.data`; `--from-original` rebuilds the cleaned cells from `original/` | yes |
| `original/` | the ASE-written inputs (`gst_cubic`, `c1_cubic`, `c2_5_cubic`, `c5_cubic`, `c10_cubic`), kept as received; two defects repaired in the cleaned cells (0.5 Å boundary gap in gst/c1/c2_5, no masses in gst/c10) | yes |
| `111/`, `222/` | 1×1×1 and 2×2×2 cells (`<tag>.data`) for the tests | no (generated) |
| `333/` | 3×3×3, 12.4k–13.8k atoms, 72.4 Å: tests/density, tuning, the 333 scaling benchmark | no |
| `444/` | 4×4×4, 29.5k–32.8k atoms, 96.5 Å: chosen for the melt-quench and recrystallization from nequip_no_zbl on (throughput test 2026-11-13, tests/scaling/submit_size.sh) | no |

Composition, the x10 caveat (vacancy-free endpoint, unstable as a crystal) and the repairs: the docstring of
`build_supercells.py`. Rebuild everything: `for n in 1 2 3 4; do python structures/build_supercells.py --nrep $n; done`
(with `env/cgst-ana`, a few seconds each).
