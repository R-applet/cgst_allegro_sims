"""Compare nucleation rates between compositions and between source glasses, from the text output of
recryst_summary.py --clusters (one or more files, e.g. prod_<cell>_clusters.txt).

Per run it reads t_nuc and t_end from the per-run rows (anneal_<cell>_T<Ta>_r<rep> ...), and the cell volume per
group from the 'nucleation:' line (V = n_nucleated / (J_surv x exposure)). Exposure E = sum over runs of t_nuc if the
run nucleated, else t_end (the censored-exponential likelihood, as in recryst_summary.survival_rate).

Equal-rate test for two groups (Poisson rates with exposures): given n1 + n2 events, n1 ~ Binomial(n1 + n2,
w1 / (w1 + w2)) under equal rates per volume, w = E x V. Two-sided exact p-value. Also prints the rate ratio with an
approximate 95% interval exp(+-1.96 sqrt(1/n1 + 1/n2)).

Composition pairs: 10 tests, so each p is also given Bonferroni-corrected (x number of pairs).

Glasses: replica r started from melt-quench glass ((r - 1) mod 3) + 1. Per composition, ONE permutation test of equal
rates across the three glass subsets (shuffle glass labels over runs, likelihood-ratio statistic; exact under the
null, checked at ~5% false positives on synthetic data). Pairwise glass tests are not
used: 15 of them give false hits at p < 0.05 by chance (seen on synthetic equal-rate data). recryst/README.md: if
rates differ between glasses, more melt-quench samples are needed.

Validated on synthetic data only (no production runs yet): a true 4x rate ratio between two 10-run groups came out
3.5x with the interval containing 4; under equal rates the pairwise test gave p < 0.05 in ~6% of 2000 datasets and the
glass permutation test in ~4.5%. Power is low: with 10 runs a glass nucleating 6x slower is detected ~36% of the time,
so p > 0.05 does not show the glasses agree.

Usage: python rate_compare.py prod_*_clusters.txt     (one recryst_summary.py --clusters output per composition)
"""
import math
import re
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runio import group_of  # noqa: E402


def parse(paths):
    runs, vol = {}, {}
    for p in paths:
        for line in open(p):
            f = line.split()
            if not f:
                continue
            if len(f) > 2 and f[1] == "nucleation:":
                kv = dict(zip(f[2::2], f[3::2]))
                vol[f[0]] = kv
            elif re.match(r"anneal_.+_T\d+_r\d+$", f[0]):
                kv = dict(zip(f[1::2], f[2::2]))
                if "t_nuc" in kv:
                    runs[f[0]] = (float(kv["t_nuc"]), float(kv["t_end"]))
    return runs, vol


def stats(items):
    n = sum(math.isfinite(tn) for tn, _ in items)
    E = sum(tn if math.isfinite(tn) else te for tn, te in items)
    return n, E


def _lr(hit, expo, labels, k):
    """Likelihood-ratio statistic of separate exponential rates per label vs one common rate (censored data)."""
    N, E = hit.sum(), expo.sum()
    out = 0.0
    for g in range(k):
        m = labels == g
        n, e = hit[m].sum(), expo[m].sum()
        if n:
            out += n * math.log((n / e) / (N / E))
    return 2 * out


def glass_test(items, labels, draws=20000, seed=0):
    """Permutation test of equal rates across glass labels: under the null every run is exchangeable (same rate,
    same 5 ns censoring), so shuffle the labels and compare the LR statistic. Exact, unlike a multinomial test that
    treats each glass's exposure as fixed (that one gave P(p < 0.05) ~ 0.12 on equal-rate synthetic data)."""
    hit = np.array([math.isfinite(tn) for tn, _ in items])
    if not hit.any() or hit.all() and len(set(labels)) < 2:
        return math.nan
    expo = np.array([tn if math.isfinite(tn) else te for tn, te in items])
    labels = np.asarray(labels)
    k = labels.max() + 1
    obs = _lr(hit, expo, labels, k)
    rng = np.random.default_rng(seed)
    sim = np.array([_lr(hit, expo, rng.permutation(labels), k) for _ in range(draws)])
    return float((sim >= obs - 1e-9).mean())


def compare(label, a, b, m=1):
    (la, na, wa), (lb, nb, wb) = a, b
    if na + nb == 0:
        print(f"  {label}: {la} vs {lb}: no events in either, no test")
        return
    p = binomtest(na, na + nb, wa / (wa + wb)).pvalue
    padj = f", Bonferroni p = {min(1.0, p * m):.3g}" if m > 1 else ""
    if na and nb:
        r = (na / wa) / (nb / wb)
        h = 1.96 * math.sqrt(1 / na + 1 / nb)
        ratio = f"ratio {r:.3g} (95% ~{r * math.exp(-h):.3g}-{r * math.exp(h):.3g})"
    else:
        ratio = "ratio undefined (zero events on one side)"
    print(f"  {label}: {la} ({na} events) vs {lb} ({nb} events): {ratio}, p = {p:.3g}{padj}")


def main():
    runs, vol = parse(sys.argv[1:])
    groups = {}
    for name, v in runs.items():
        groups.setdefault(group_of(name), []).append((name, v))
    comp = []
    print("per composition (E in ps; V in A^3 from J_surv, needs >= 1 event):")
    for g, items in sorted(groups.items()):
        n, E = stats([v for _, v in items])
        kv = vol.get(g, {})
        J = float(kv.get("J_surv_per_m3_s", "nan"))
        V = n / (J * E * 1e-12) * 1e30 if n and math.isfinite(J) and J > 0 else math.nan
        print(f"  {g:28s} runs {len(items):3d}  nucleated {n:3d}  exposure {E:9.0f} ps  V {V:.4g}")
        comp.append((g, n, E, V))
    print("between compositions (w = E x V; groups with no event are skipped: V unknown):")
    usable = [(g, n, E * V) for g, n, E, V in comp if math.isfinite(V)]
    pairs = list(combinations(usable, 2))
    for a, b in pairs:
        compare("comp", a, b, len(pairs))
    print("between source glasses, within each composition (glass = (r - 1) mod 3 + 1):")
    for g, items in sorted(groups.items()):
        sub = {}
        for name, v in items:
            r = int(re.search(r"_r(\d+)$", name)[1])
            sub.setdefault((r - 1) % 3 + 1, []).append(v)
        rows = [(k, *stats(v)) for k, v in sorted(sub.items())]
        order = sorted(items, key=lambda it: it[0])
        lab = [(int(re.search(r"_r(\d+)$", name)[1]) - 1) % 3 for name, _ in order]
        p = glass_test([v for _, v in order], lab)
        per = ", ".join(f"glass {k}: {n} events / {E:.0f} ps" for k, n, E in rows)
        print(f"  {g:28s} {per}; equal-rate p = {p:.3g}")


if __name__ == "__main__":
    main()
