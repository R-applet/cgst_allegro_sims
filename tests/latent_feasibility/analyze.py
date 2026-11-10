"""Feasibility: do pooled Allegro latents separate crystal from glass better than Q4, and do they transfer to x10?

Input: features.npz from analysis/latent_features.py on
  smoke_x0     x0 rocksalt, NPT 600 K, frames 0-3000 (step 0 = minimized lattice, excluded)
  smoke_x10    x10 rocksalt at 600 K, disordering (Q4 xfrac 0.93 -> 0.56 in 3 ps)
  mqlogic_x0   tests/mq_logic x0: heating-ramp crystal at 5000 (615 K) and 6000 (689 K); fast-quenched glass at
               32000 (678 K), 33000 (601 K), 34000 (~520 K)
References (Ge/Sb/Te atoms only; all at ~520-690 K):
  crystal train smoke_x0 500,1500,2500 + mq 5000      crystal test smoke_x0 1000,2000,3000 + mq 6000
  glass   train mq 32000, 34000                        glass   test mq 33000
Descriptors, scored per species (Ge, Sb, Te) by ROC AUC on the test frames (0.5 = no separation, 1 = perfect):
  Q4      crystal-like bond count ncb (default criterion), higher = crystal
  E_i     per-atom energy, lower = crystal (sign fixed a priori, not fitted)
  latent  Fisher LDA on the 256-D pooled latent, fitted on the train frames (shrinkage 1e-3), higher = crystal
Unsupervised: per species, k-means (k=2) on the top 10 principal components of train+test latents; accuracy of
  the better cluster-to-phase assignment.
Transfer: the x0-trained LDA (threshold = midpoint of the class means on train) and Q4 (ncb >= 4) applied to the
  x10 trajectory, Ge/Sb/Te atoms: crystalline fraction per frame, and per-atom agreement between the two.
Writes RESULT.txt.
"""
from pathlib import Path

import numpy as np
from scipy.cluster.vq import kmeans2

HERE = Path(__file__).resolve().parent
z = np.load(HERE / "features.npz")
frames = list(z["frames"])
SP = {1: "Ge", 2: "Sb", 3: "Te"}


def get(label):
    k = frames.index(label)
    t = z[f"f{k}_types"]
    m = t < 4
    return {"lat": z[f"f{k}_latent"][m].astype(float), "e": z[f"f{k}_e_atom"][m], "ncb": z[f"f{k}_ncb"][m],
            "t": t[m]}


def stack(labels):
    parts = [get(l) for l in labels]
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def auc(pos, neg):
    """P(score_pos > score_neg) with ties counted half (Mann-Whitney)."""
    s = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(s, kind="mergesort"), kind="mergesort").astype(float) + 1
    # average ranks for ties
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=r)
    r = (sums / cnt)[inv]
    n1, n0 = len(pos), len(neg)
    return (r[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def lda(Xc, Xa, shrink=1e-3):
    mc, ma = Xc.mean(0), Xa.mean(0)
    S = np.cov(np.vstack([Xc - mc, Xa - ma]).T)
    S += shrink * np.trace(S) / len(S) * np.eye(len(S))
    w = np.linalg.solve(S, mc - ma)
    return w, 0.5 * (mc + ma) @ w


sx0 = lambda s: f"smoke_x0.lammpstrj.gz:{s}"
mq = lambda s: f"mqlogic_x0.lammpstrj.gz:{s}"
ctr = stack([sx0(500), sx0(1500), sx0(2500), mq(5000)])
cte = stack([sx0(1000), sx0(2000), sx0(3000), mq(6000)])
atr = stack([mq(32000), mq(34000)])
ate = stack([mq(33000)])

w, thr = lda(ctr["lat"], atr["lat"])
lines = ["Per-species ROC AUC on held-out frames (crystal vs glass, ~600 K):",
         f"{'species':8s} {'n_cry':>6s} {'n_gla':>6s} {'Q4':>7s} {'E_i':>7s} {'latent':>7s} {'kmeans_acc':>11s}"]
for t, name in SP.items():
    c, a = cte["t"] == t, ate["t"] == t
    a_q4 = auc(cte["ncb"][c], ate["ncb"][a])
    a_e = auc(-cte["e"][c], -ate["e"][a])
    a_l = auc(cte["lat"][c] @ w, ate["lat"][a] @ w)
    X = np.vstack([ctr["lat"][ctr["t"] == t], cte["lat"][c], atr["lat"][atr["t"] == t], ate["lat"][a]])
    y = np.r_[np.ones((ctr["t"] == t).sum() + c.sum()), np.zeros((atr["t"] == t).sum() + a.sum())]
    Xc = X - X.mean(0)
    pcs = Xc @ np.linalg.svd(Xc, full_matrices=False)[2][:10].T
    _, lab = kmeans2(pcs, 2, seed=7, minit="++")
    acc = max((lab == y).mean(), (lab != y).mean())
    lines.append(f"{name:8s} {c.sum():6d} {a.sum():6d} {a_q4:7.3f} {a_e:7.3f} {a_l:7.3f} {acc:11.3f}")

lines += ["", "Transfer to x10 (C-rich, disordering from rocksalt at 600 K), Ge/Sb/Te atoms:",
          f"{'frame':>6s} {'xfrac_Q4':>9s} {'xfrac_latent':>13s} {'agreement':>10s}"]
for s in range(0, 3001, 500):
    d = get(f"smoke_x10.lammpstrj.gz:{s}")
    q = d["ncb"] >= 4
    l = d["lat"] @ w > thr
    lines.append(f"{s:6d} {q.mean():9.3f} {l.mean():13.3f} {(q == l).mean():10.3f}")
lines += ["", "Same classifiers on x0 test frames (sanity: should be ~1 crystal / ~0 glass):"]
for name, d in (("x0 crystal test", cte), ("x0 glass test", ate)):
    lines.append(f"  {name:16s} xfrac_Q4 {(d['ncb'] >= 4).mean():.3f}  xfrac_latent {(d['lat'] @ w > thr).mean():.3f}")
txt = "\n".join(lines)
print(txt)
(HERE / "RESULT.txt").write_text(txt + "\n")
