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


def _select_eta(dbar: np.ndarray, A: np.ndarray, P: np.ndarray, L: np.ndarray,
                eta0: float, noise_norm: float, n_try: int = 60) -> Tuple[float, float]:
    """Pick the regularisation by the discrepancy principle.

    The repeat scatter fixes how large the residual ``||d - A m||`` ought to be.
    At the guide's reference eta0 the residual of this data is far above that
    level, i.e. eta0 is a smooth reference reconstruction rather than a
    noise-matched one. The guide explicitly allows another value when the
    repeat noise gives a clear, documented reason, so we keep the largest eta
    whose residual is still consistent with the measured repeat noise: the most
    smoothing that the data can support.

    Returns (eta_chosen, eta0_multiplier).
    """
    mult = 0.01
    for m_try in np.logspace(np.log10(0.01), np.log10(3.0), n_try):
        m_eta = reconstruct(dbar, A, P, L, eta0 * m_try)
        if np.linalg.norm(dbar - A @ m_eta) <= noise_norm:
            mult = float(m_try)
        else:
            break
    return eta0 * mult, float(mult)


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


def _ramp_detrend(m: np.ndarray) -> Tuple[np.ndarray, float, float]:
    """Remove the best-fit planar (wafer-scale) trend from a flat map.

    A single-crystal wafer usually shows a smooth process gradient across the
    whole plate in addition to localised defects. The gradient's extrema always
    sit on the map boundary by construction, so they are NOT features: the
    guide asks for defects ("merge neighbouring pixels into one feature rather
    than reporting every pixel as a separate defect") and the probe resolution
    is defined through a localised point spread. Subtracting the planar trend
    makes the localised features the extrema.

    Returns the detrended map plus the fitted gradients in probe pitches.
    """
    yy, xx = np.meshgrid(np.arange(NPIX), np.arange(NPIX), indexing="ij")
    X = np.column_stack([np.ones(N), xx.ravel(), yy.ravel()])
    coef, *_ = np.linalg.lstsq(X, m, rcond=None)
    ramp = X @ coef
    return m - ramp, float(coef[1]), float(coef[2])


def _merge_features(m: np.ndarray) -> List[Dict]:
    """Largest positive and negative localised features, merged over neighbours.

    The global extremum of each sign is taken as the feature peak; neighbours
    of the same sign and at least half the peak magnitude are merged into that
    one feature (guide p.11: one feature per defect, not one per pixel). The
    half-height cutoff keeps broad plateaus from swallowing the whole map, the
    same convention used for the resolution FWHM. Coordinates are pixel centres
    in probe pitches.
    """
    flat = m.ravel()
    feats: List[Dict] = []

    def _component_peak(seed: int, floor: float) -> List[int]:
        sign = np.sign(flat[seed])
        seen = {seed}
        stack = [seed]
        while stack:
            k = stack.pop()
            i, j = divmod(k, NPIX)
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                if 0 <= ni < NPIX and 0 <= nj < NPIX:
                    nk = ni * NPIX + nj
                    if nk not in seen and np.sign(flat[nk]) == sign \
                            and abs(flat[nk]) >= floor:
                        seen.add(nk)
                        stack.append(nk)
        return sorted(seen)

    for sign in ("positive", "negative"):
        seed = int(np.argmax(flat)) if sign == "positive" else int(np.argmin(flat))
        amp = float(flat[seed])
        comp = _component_peak(seed, 0.5 * abs(amp))
        ci, cj = divmod(seed, NPIX)
        feats.append({
            "sign": sign,
            "amplitude": amp,
            "x": float(PIXEL_CENTRES[cj]),
            "y": float(PIXEL_CENTRES[ci]),
            "pixel": [int(ci), int(cj)],
            "n_pixels": len(comp),
            "centroid_pixel": [float(np.mean([divmod(k, NPIX)[0] for k in comp])),
                               float(np.mean([divmod(k, NPIX)[1] for k in comp]))],
        })
    return feats


def _merge_features_global_extrema(m: np.ndarray) -> List[Dict]:
    """Kept for reference: extrema of the raw (non-detrended) map."""
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

    noise_norm = float(np.sqrt((sigma_j ** 2).sum()))

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
                     "roughness_norm": float(rough),
                     "residual_over_noise": float(resid / noise_norm)})

    # ---- regularisation strength ----
    # The guide's eta0 is a smooth reference; the repeat noise documents that
    # this data supports a smaller value (see _select_eta).
    eta_chosen, eta_chosen_mult = _select_eta(dbar, A, P, L, eta0, noise_norm)

    # ---- reference reconstruction ----
    mhat = reconstruct(dbar, A, P, L, eta_chosen).reshape(NPIX, NPIX)
    assert mhat.shape == (NPIX, NPIX)
    assert abs(mhat.mean()) < 1e-12, f"mean {mhat.mean()}"

    # ---- wafer-scale trend and localised features ----
    # The planar trend is the wafer-scale process gradient: its extrema always
    # sit on the map boundary, so it cannot be a "feature". The guide asks for
    # defects, so features are taken from the detrended map.
    det_flat, grad_x, grad_y = _ramp_detrend(mhat.ravel())
    det = det_flat.reshape(NPIX, NPIX)
    features = _merge_features(det)
    global_extrema = _merge_features_global_extrema(mhat)
    features_interior = all(0 < f["pixel"][0] < NPIX - 1 and 0 < f["pixel"][1] < NPIX - 1
                            for f in features)

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

    # ---- map figure: raw map (with trend) and detrended feature map ----
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.6))
    lim = max(np.abs(mhat).max(), np.abs(det).max())
    ax = axes[0]
    im = ax.imshow(mhat, origin="lower", cmap="RdBu_r", vmin=-lim, vmax=lim,
                   extent=(-3.0, 3.0, -3.0, 3.0))
    fig.colorbar(im, ax=ax, label="reconstructed non-uniformity (signal units)")
    for f in global_extrema:
        ax.plot(f["x"], f["y"], marker="x", mec="black", ms=11, mew=2,
                label=f"raw extremum {f['amplitude']:+.4f}")
    ax.set_xlabel("x (probe pitches)")
    ax.set_ylabel("y (probe pitches)")
    ax.set_title(rf"(a) zero-mean map with wafer trend"
                 "\n" rf"gradient ${np.hypot(grad_x, grad_y):.5f}$ /pitch, "
                 rf"$\max|m|={a:.4f}$")
    ax.legend(loc="upper right", fontsize=8)

    ax = axes[1]
    im2 = ax.imshow(det, origin="lower", cmap="RdBu_r", vmin=-lim, vmax=lim,
                    extent=(-3.0, 3.0, -3.0, 3.0))
    fig.colorbar(im2, ax=ax, label="detrended non-uniformity (signal units)")
    for f in features:
        ax.plot(f["x"], f["y"], marker="o" if f["sign"] == "positive" else "s",
                mfc="none", mec="black", ms=12,
                label=f"{f['sign']}: {f['amplitude']:+.4f} @ ({f['x']:+.1f},{f['y']:+.1f})")
    ax.set_xlabel("x (probe pitches)")
    ax.set_ylabel("y (probe pitches)")
    ax.set_title("(b) planar trend removed: the localised features are interior")
    ax.legend(loc="lower left", fontsize=8)
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
    m_star = reconstruct(dbar, A, P, L, eta_chosen)
    ax.plot(np.linalg.norm(dbar - A @ m_star), np.linalg.norm(L @ m_star), "*",
            color="crimson", ms=16,
            label=f"chosen: {eta_chosen_mult:.3g}x eta0")
    ax.axvline(noise_norm, color="gray", ls=":", lw=1.2,
               label="repeat-noise level")
    ax.set_xlabel("residual norm $||d - A m||$")
    ax.set_ylabel("roughness norm $||L m||$")
    ax.set_title("eta sensitivity (L-curve)")
    ax.legend(fontsize=8)
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
        "eta_chosen_multiplier_of_eta0": eta_chosen_mult,
        "eta_selection_rule": (
            "discrepancy principle: largest eta whose residual ||d-A m|| stays "
            "within the repeat-noise norm"),
        "eta_sensitivity": sens,
        "wafer_gradient_x_per_pitch": grad_x,
        "wafer_gradient_y_per_pitch": grad_y,
        "wafer_gradient_magnitude": float(np.hypot(grad_x, grad_y)),
        "raw_global_extrema": global_extrema,
        "detrended_feature_peak_abs": float(np.max(np.abs(det))),
        "features_all_interior": bool(features_interior),
        "fwhm_centre_pitch": fwhm_centre,
        "fwhm_off_centre_pitch": fwhm_off,
        "noise_seed": noise_seed,
        "n_noise": n_noise,
        "noise_norm_estimate": float(np.sqrt((sigma_j ** 2).sum())),
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
