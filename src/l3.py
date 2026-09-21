"""L3 -- two-dimensional inverse problem.

Question: where is the Hall-conductivity non-uniform, what can the probe
resolve, and does the wafer pass the announced specification?

Guide reference: Practical Methods Guide pp.10-13.
"""
import json
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .common import DATA_DIR, FIG_DIR, OUTPUT_DIR

NPIX = 10
N = NPIX * NPIX
PIXEL_CENTRES = np.linspace(-2.7, 2.7, NPIX)  # probe-pitch units

# specification announced at the start of Session 3 (slides p.15):
# PASS when max|m| <= 0.030 (3.0% of the reference conductivity)
ANNOUNCED_SPEC = 0.030


def gradient_matrix(npix: int = NPIX) -> np.ndarray:
    """First-difference matrix L (180 x 100 for a 10x10 map). Guide p.10."""
    rows = []
    Np = npix * npix
    for i in range(npix):
        for j in range(npix):
            k = i * npix + j
            if j < npix - 1:
                r = np.zeros(Np)
                r[k] = -1
                r[k + 1] = 1
                rows.append(r)
            if i < npix - 1:
                r = np.zeros(Np)
                r[k] = -1
                r[k + npix] = 1
                rows.append(r)
    return np.asarray(rows)


def _build_system(A: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    L = gradient_matrix(NPIX)
    one = np.ones((N, 1)) / np.sqrt(N)
    P = np.eye(N) - one @ one.T
    eta0 = 1e-2 * np.linalg.norm(A, 2) ** 2 / np.linalg.norm(L, 2) ** 2
    return L, P, float(eta0)


def reconstruct(dvec: np.ndarray, A: np.ndarray, P: np.ndarray, L: np.ndarray,
                eta: float) -> np.ndarray:
    """Tikhonov-regularised zero-mean reconstruction. Guide p.11."""
    M = P @ (A.T @ A + eta * (L.T @ L)) @ P + 1e-9 * np.eye(N)
    b = P @ (A.T @ dvec)
    m = np.linalg.lstsq(M, b, rcond=None)[0]
    return m - m.mean()


def _fwhm_positive_lobe(q_hat: np.ndarray, centre_idx: int) -> float:
    """FWHM of the positive lobe around the injected pixel (guide p.12)."""
    w = np.maximum(q_hat, 0.0)
    if w.sum() == 0:
        return float("nan")
    i0, j0 = np.unravel_index(centre_idx, (NPIX, NPIX))
    r2 = np.zeros(N)
    for k in range(N):
        i, j = np.unravel_index(k, (NPIX, NPIX))
        r2[k] = (PIXEL_CENTRES[i] - PIXEL_CENTRES[i0]) ** 2 + \
                (PIXEL_CENTRES[j] - PIXEL_CENTRES[j0]) ** 2
    sigma2 = float((w * r2).sum() / (2.0 * w.sum()))
    return 2.355 * np.sqrt(sigma2)


def _merge_features(m: np.ndarray) -> List[Dict]:
    """Locate largest positive and negative extrema; merge 4-neighbours."""
    features: List[Dict] = []
    pos_candidates = list(zip(*np.where(m > 0)))
    if pos_candidates:
        k = max(pos_candidates, key=lambda ij: m[ij])
        features.append({
            "sign": "positive",
            "amplitude": float(m[k]),
            "x": float(PIXEL_CENTRES[k[1]]),
            "y": float(PIXEL_CENTRES[k[0]]),
            "pixel": [int(k[0]), int(k[1])],
        })
    neg_candidates = list(zip(*np.where(m < 0)))
    if neg_candidates:
        k = min(neg_candidates, key=lambda ij: m[ij])
        features.append({
            "sign": "negative",
            "amplitude": float(m[k]),
            "x": float(PIXEL_CENTRES[k[1]]),
            "y": float(PIXEL_CENTRES[k[0]]),
            "pixel": [int(k[0]), int(k[1])],
        })
    return features


def run_l3(noise_seed: int = 20260921, n_noise: int = 500) -> Dict:
    """Run the complete L3 analysis."""
    meta = json.loads((DATA_DIR / "L3_meta.json").read_text(encoding="utf-8"))
    A = np.load(DATA_DIR / "L3_A.npy")
    d_reps = np.loadtxt(DATA_DIR / "L3_d.csv", delimiter=",")

    # ---- file checks (guide p.10) ----
    assert A.shape == (128, 100), f"A shape {A.shape}"
    assert d_reps.shape == (3, 128), f"d shape {d_reps.shape}"
    row_sum_max = float(np.max(np.abs(A.sum(axis=1))))
    assert row_sum_max < 1e-11, f"row sums {row_sum_max}"

    dbar = d_reps.mean(axis=0)
    sigma_j = d_reps.std(axis=0, ddof=1)

    # singular-value inspection (brief 5.3, step 1)
    sv = np.linalg.svd(A, compute_uv=False)
    sv_top = float(sv[0])
    sv_smallest = float(sv[-1])
    n_null = int(np.sum(sv < 1e-10))  # null-space directions (incl. constant)

    L, P, eta0 = _build_system(A)

    # ---- reference reconstruction ----
    mhat = reconstruct(dbar, A, P, L, eta0).reshape(NPIX, NPIX)
    assert mhat.shape == (NPIX, NPIX)
    assert abs(mhat.mean()) < 1e-12, f"mean {mhat.mean()}"

    # ---- eta sensitivity (guide p.11) ----
    eta_multipliers = [0.01, 0.1, 1.0, 10.0, 100.0]
    sens = []
    for mult in eta_multipliers:
        eta = eta0 * mult
        m_eta = reconstruct(dbar, A, P, L, eta)
        resid = np.linalg.norm(dbar - A @ m_eta)
        rough = np.linalg.norm(L @ m_eta)
        sens.append({"eta_multiplier": mult, "eta": float(eta),
                     "residual_norm": float(resid),
                     "roughness_norm": float(rough)})
    eta_chosen = eta0  # reference value unless sensitivity says otherwise

    # ---- features ----
    features = _merge_features(mhat)

    # ---- resolution test (guide p.12) ----
    def psf_width(pixel_idx: int) -> float:
        q = np.zeros(N)
        q[pixel_idx] = 1.0
        q = q - q.mean()
        y = A @ q
        q_hat = reconstruct(y, A, P, L, eta_chosen)
        return _fwhm_positive_lobe(q_hat, pixel_idx)

    centre = NPIX * (NPIX // 2) + (NPIX // 2)          # (5,5)
    off_centre = 2 * NPIX + 2                          # (2,2)
    fwhm_centre = psf_width(centre)
    fwhm_off = psf_width(off_centre)
    resolution = float(max(fwhm_centre, fwhm_off))

    # ---- noise-linked detection limit (guide p.12) ----
    rng = np.random.default_rng(noise_seed)
    noise_max = np.empty(n_noise)
    for k in range(n_noise):
        noise_vec = rng.normal(0.0, sigma_j)
        m_noise = reconstruct(noise_vec, A, P, L, eta_chosen)
        noise_max[k] = np.max(np.abs(m_noise))
    delta95 = float(np.percentile(noise_max, 95))

    # ---- pass/fail decision ----
    a = float(np.max(np.abs(mhat)))
    thr = ANNOUNCED_SPEC
    if a + delta95 < thr:
        decision, confidence = "pass", "clear"
    elif a - delta95 > thr:
        decision, confidence = "fail", "clear"
    else:
        decision, confidence = "borderline", "borderline"

    # ---- map figure ----
    plt.figure(figsize=(6.2, 5.6))
    im = plt.imshow(mhat, origin="lower", cmap="RdBu_r",
                    extent=(-3.0, 3.0, -3.0, 3.0))
    plt.colorbar(im, label="reconstructed non-uniformity (signal units)")
    for f in features:
        plt.plot(f["x"], f["y"], marker="o" if f["sign"] == "positive" else "s",
                 mfc="none", mec="black", ms=12,
                 label=f"{f['sign']}: {f['amplitude']:+.4f}")
    plt.xlabel("x (probe pitches)")
    plt.ylabel("y (probe pitches)")
    plt.title("L3 G14: zero-mean non-uniformity map")
    plt.legend(loc="best")
    plt.tight_layout()
    fig_map = FIG_DIR / "L3_map.png"
    plt.savefig(fig_map, dpi=200)
    plt.close()

    # ---- method figure: eta sensitivity, singular values, PSF ----
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.6))
    ax = axes[0]
    res = [s["residual_norm"] for s in sens]
    rough = [s["roughness_norm"] for s in sens]
    ax.loglog(res, rough, "o-", color="#1f77b4")
    for i, s in enumerate(sens):
        ax.annotate(f"{s['eta_multiplier']:g}x", (res[i], rough[i]),
                    textcoords="offset points", xytext=(6, -4), fontsize=8)
    ax.set_xlabel("residual norm $||d - A m||$")
    ax.set_ylabel("roughness norm $||L m||$")
    ax.set_title("eta sensitivity (L-curve)")
    ax.grid(alpha=0.3)

    ax = axes[1]
    ax.semilogy(sv, ".-", color="#2ca02c")
    ax.axhline(1e-10, color="gray", linestyle=":", label="null-space cutoff")
    ax.set_xlabel("singular-value index")
    ax.set_ylabel("singular value")
    ax.set_title(f"singular values of A ({n_null} null directions)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    ax = axes[2]
    q = np.zeros(N)
    q[centre] = 1.0
    q = q - q.mean()
    y = A @ q
    q_hat = reconstruct(y, A, P, L, eta_chosen).reshape(NPIX, NPIX)
    im2 = ax.imshow(q_hat, origin="lower", cmap="RdBu_r",
                    extent=(-3.0, 3.0, -3.0, 3.0))
    fig.colorbar(im2, ax=ax, label="recovered PSF")
    ax.set_title(f"point-spread: centre injection\nFWHM = {fwhm_centre:.2f} pitches")
    ax.set_xlabel("x (probe pitches)")
    ax.set_ylabel("y (probe pitches)")
    plt.tight_layout()
    fig_method = FIG_DIR / "L3_method.png"
    plt.savefig(fig_method, dpi=200)
    plt.close()

    results = {
        "map": [float(x) for x in mhat.ravel()],
        "features": features,
        "resolution_probe_pitch": resolution,
        "detection_limit_fraction": delta95,
        "pass": decision == "pass",
        "confidence": confidence,
    }
    meta_out = {
        "row_sum_max": row_sum_max,
        "map_mean_abs": float(abs(mhat.mean())),
        "sv_max": sv_top,
        "sv_min": sv_smallest,
        "n_null_directions": n_null,
        "sv_spectrum": [float(x) for x in sv],
        "eta0": eta0,
        "eta_chosen": eta_chosen,
        "eta_sensitivity": sens,
        "fwhm_centre_pitch": fwhm_centre,
        "fwhm_off_centre_pitch": fwhm_off,
        "noise_seed": noise_seed,
        "n_noise": n_noise,
        "max_abs_map": a,
        "announced_spec": thr,
        "decision": decision,
        "a_plus_delta95": a + delta95,
        "a_minus_delta95": a - delta95,
        "npix": int(meta["npix"]),
        "matrix_shape": meta["matrix_shape"],
        "readings_shape": meta["readings_shape"],
        "map_figure": str(fig_map.relative_to(OUTPUT_DIR)),
        "method_figure": str(fig_method.relative_to(OUTPUT_DIR)),
    }
    return {"L3": results, "L3_meta": meta_out}
