# iso vs aniso barostat check (x0, nequip_no_zbl, 3 replicas each, mean +- sample std)

| | T600 aniso | T600 iso | T650 aniso | T650 iso |
|---|---|---|---|---|
| t_nuc (ps) | 47 +- 1 | 57 +- 15 | 98 +- 44 | 88 +- 10 |
| t_inc (ps) | 67 +- 1 | 64 +- 8 | 158 +- 33 | 128 +- 11 |
| t50 (ps) | 275 +- 16 | 285 +- 16 | 317 +- 38 | 299 +- 19 |
| v_growth (m/s) | 6.45 +- 0.26 | 6.48 +- 0.48 | 12.1 +- 1.2 | 11.1 +- 0.5 |

Files: grid_x0[_iso]_T{600,650}[_clusters].txt (cluster job 12447898). All differences are within
replica scatter (at most ~1.5 combined SE); the barostat choice does not change the kinetics.
