"""Robust PCA (RPCA) via Inexact Augmented Lagrange Multiplier (ALM).

Solves:  min_{L,S}  ||L||_* + lambda*||S||_1   s.t.  M = L + S

Reference: Z. Lin, M. Chen, Y. Ma, "The Augmented Lagrange Multiplier Method for
Exact Recovery of Corrupted Low-Rank Matrices", arXiv:1009.5055 (2010);
E. J. Candes et al., "Robust Principal Component Analysis?", JACM 2011.

Application: background subtraction in surveillance video -- the static background
is (approximately) low-rank L, moving foreground objects are sparse S.

Run:  python src/rpca.py            (runs both experiments, saves figures + stats)
"""
import json
import time
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)


# ----------------------------------------------------------------- core RPCA
def shrink(X, tau):
    """Element-wise soft-thresholding (proximal operator of the l1 norm)."""
    return np.sign(X) * np.maximum(np.abs(X) - tau, 0.0)


def svt(X, tau):
    """Singular value thresholding (proximal operator of the nuclear norm)."""
    U, s, Vh = np.linalg.svd(X, full_matrices=False)
    return U @ np.diag(shrink(s, tau)) @ Vh, s


def rpca(M, lam=None, tol=1e-7, max_iter=500, mu=None):
    """Inexact ALM for Robust PCA. Returns (L, S, history, elapsed_seconds)."""
    m, n = M.shape
    scale = np.linalg.norm(M)
    if scale == 0:
        return M, np.zeros_like(M), [], 0.0
    lam = 1.0 / np.sqrt(max(m, n)) if lam is None else lam
    mu = 1.25 / np.linalg.norm(M, 2) if mu is None else mu
    mu_bar = mu * 1e6
    rho = 1.5
    Y = M / np.maximum(np.linalg.norm(M, 2), np.abs(M).max())  # practical init
    L = np.zeros_like(M)
    hist, t0 = [], time.perf_counter()
    for it in range(max_iter):
        S = shrink(M - L + Y / mu, lam / mu)
        L, sv = svt(M - S + Y / mu, 1.0 / mu)
        rel = np.linalg.norm(M - L - S) / scale
        hist.append({"iter": it + 1, "rel_err": float(rel),
                     "rank": int((sv > 1e-3 * sv[0]).sum())})
        Y = Y + mu * (M - L - S)
        mu = min(rho * mu, mu_bar)
        if rel < tol:
            break
    return L, S, hist, time.perf_counter() - t0


# --------------------------------------------------------- experiment 1: synthetic
def synthetic_experiment():
    rng = np.random.default_rng(0)
    m, n, r = 200, 100, 5
    L_true = rng.standard_normal((m, r)) @ rng.standard_normal((r, n))
    S_true = np.zeros((m, n))
    for _ in range(15):  # 15 sparse blocks = "moving objects"
        i, j = rng.integers(0, m - 8), rng.integers(0, n - 8)
        S_true[i:i + 8, j:j + 8] = rng.uniform(2.0, 5.0)
    support = S_true != 0
    M = L_true + S_true + 0.01 * rng.standard_normal((m, n))

    L, S, hist, secs = rpca(M)
    pred = np.abs(S) > 0.3  # true entries are in [2,5]; shrink leakage << 0.3
    tp = (pred & support).sum()
    prec = tp / max(pred.sum(), 1)
    rec = tp / max(support.sum(), 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-12)
    err_L = np.linalg.norm(L - L_true) / np.linalg.norm(L_true)

    # naive baseline: plain truncated SVD (rank r) -- the non-robust PCA
    U, s, Vh = np.linalg.svd(M, full_matrices=False)
    L_naive = U[:, :r] @ np.diag(s[:r]) @ Vh[:r]
    S_naive = M - L_naive
    err_naive = np.linalg.norm(L_naive - L_true) / np.linalg.norm(L_true)
    pred_n = np.abs(S_naive) > 0.3
    tp_n = (pred_n & support).sum()
    prec_n = tp_n / max(pred_n.sum(), 1)
    rec_n = tp_n / max(support.sum(), 1)
    f1_naive = 2 * prec_n * rec_n / max(prec_n + rec_n, 1e-12)

    # figure
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.4), dpi=170)
    for ax, (img, title) in zip(axes, [
        (M, "Observed M = L* + S*"),
        (L, "RPCA recovered L"),
        (S, "RPCA recovered S"),
        (S_true, "Ground-truth S*"),
    ]):
        ax.imshow(img, cmap="gray")
        ax.set_title(title, fontsize=10)
        ax.axis("off")
    fig.suptitle(
        f"Synthetic: RPCA support F1 = {f1:.4f} (naive SVD: {f1_naive:.4f})   "
        f"||L-L*||/||L*|| = {err_L:.2e} (naive: {err_naive:.2e})",
        fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_synthetic.png", bbox_inches="tight")

    stats = {"precision": prec, "recall": rec, "f1": f1, "f1_naive_svd": f1_naive,
             "err_L": err_L, "err_L_naive": err_naive, "iters": hist[-1]["iter"],
             "seconds": secs, "matrix": f"{m}x{n}", "true_rank": r}
    (OUT / "stats_synthetic.json").write_text(json.dumps(stats, indent=2))
    return stats


# ------------------------------------------------- experiment 2: surveillance video
def video_experiment():
    cap = cv2.VideoCapture(str(ROOT / "data" / "vtest.avi"))
    frames, idx = [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if idx % 5 == 0:
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            g = cv2.resize(g, (96, 72))
            frames.append(g.astype(np.float64) / 255.0)
        idx += 1
    cap.release()
    F = np.stack(frames, axis=-1)  # H x W x T
    h, w, T = F.shape
    M = F.reshape(-1, T).T  # T x (H*W); each row = one frame
    print(f"video: {T} frames sampled, matrix {M.shape}")

    L, S, hist, secs = rpca(M)
    Bg = L.reshape(T, h, w)
    Fg = S.reshape(T, h, w)
    # effective rank of the recovered background (relative singular-value cutoff)
    _, s_bg, _ = np.linalg.svd(L, full_matrices=False)
    bg_rank = int((s_bg > 1e-3 * s_bg[0]).sum())

    # pick 3 frames with clear pedestrians
    fg_energy = (np.abs(Fg) > 0.05).sum(axis=(1, 2))
    picks = [int(np.argsort(fg_energy)[k]) for k in (-1, -len(fg_energy) // 2, len(fg_energy) // 4)]

    fig, axes = plt.subplots(4, 3, figsize=(9.6, 10.5), dpi=170)
    for col, t in enumerate(picks):
        axes[0, col].imshow(F[:, :, t], cmap="gray")
        axes[0, col].set_title(f"frame {t}: observed", fontsize=9)
        axes[1, col].imshow(Bg[t], cmap="gray")
        axes[1, col].set_title("low-rank L (background)", fontsize=9)
        axes[2, col].imshow(np.abs(Fg[t]), cmap="hot", vmin=0, vmax=0.6)
        axes[2, col].set_title("sparse S (foreground)", fontsize=9)
        axes[3, col].imshow((np.abs(Fg[t]) > 0.05), cmap="gray")
        axes[3, col].set_title("foreground mask", fontsize=9)
    for ax in axes.ravel():
        ax.axis("off")
    fig.suptitle("Robust PCA background subtraction on vtest.avi (pedestrians)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_video.png", bbox_inches="tight")

    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=170)
    err = [hh["rel_err"] for hh in hist]
    rk = [hh["rank"] for hh in hist]
    ax.semilogy(err, "b-", lw=2)
    ax.set_xlabel("iteration")
    ax.set_ylabel("relative error ||M-L-S||/||M||")
    ax2 = ax.twinx()
    ax2.plot(rk, "g--", lw=1.5, alpha=0.8)
    ax2.set_ylabel("estimated rank of L", color="g")
    ax.set_title(f"ALM convergence ({len(hist)} iterations, {secs:.1f} s)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_convergence.png", bbox_inches="tight")

    stats = {"frames_total": idx, "frames_used": T, "resolution": f"{w}x{h}",
             "matrix_shape": f"{M.shape[0]}x{M.shape[1]}", "iters": hist[-1]["iter"],
             "final_rel_err": hist[-1]["rel_err"], "bg_rank": bg_rank,
             "seconds": secs,
             "fg_ratio_mean": float((np.abs(Fg) > 0.05).mean())}
    (OUT / "stats_video.json").write_text(json.dumps(stats, indent=2))
    return stats


if __name__ == "__main__":
    s1 = synthetic_experiment()
    print("synthetic:", json.dumps({k: round(v, 4) if isinstance(v, float) else v for k, v in s1.items()}))
    s2 = video_experiment()
    print("video:", json.dumps({k: round(v, 4) if isinstance(v, float) else v for k, v in s2.items()}))
