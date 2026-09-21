"""L2 -- zero-dimensional inverse problem.

Question: is the material gapless or hard-gapped, how large is the gap, and
how did the Fermi level drift across the measurement series?

Guide reference: Practical Methods Guide pp.6-9.
"""
import json
from typing import Dict, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .common import DATA_DIR, FIG_DIR, KB, NA, OUTPUT_DIR, fermi

# grids (guide p.7)
E_GRID = np.linspace(-2.5, 2.5, 4000)
EF_GRID_KT = np.linspace(-8.0, 9.0, 400)
EG_KT_CANDIDATES = np.arange(0.50, 8.01, 0.25)


def dos(E: np.ndarray, model: str, c: float, Eg: float) -> np.ndarray:
    """Density of states: ideal cone or symmetric hard-gap V model."""
    if model == "cone":
        return c * np.abs(E)
    D = Eg / 2.0
    return np.where(np.abs(E) > D, c * (np.abs(E) - D), 0.0)


def carrier_np(EF: float, T: float, model: str, c: float, Eg: float) -> Tuple[float, float]:
    """Electron-like (E>=EF) and hole-like (E<=EF) Fermi-window populations."""
    f = fermi(E_GRID, EF, T)
    g = dos(E_GRID, model, c, Eg)
    n = NA * np.trapezoid(np.where(E_GRID >= EF, g * f, 0.0), E_GRID)
    p = NA * np.trapezoid(np.where(E_GRID <= EF, g * (1.0 - f), 0.0), E_GRID)
    return float(n), float(p)


def rh_rs_from_np(n: np.ndarray, p: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Raw Hall and sheet-resistance proxies (e=1, mu=1; scales cancel later)."""
    R_H = 1.0 / (n - p)
    R_s = 1.0 / (n + p)
    return R_H, R_s


class ModelLibrary:
    """Precomputed normalised model curves (guide p.7: build once, reuse)."""

    def __init__(self, T: float):
        self.T = T
        self.EF_grid = EF_GRID_KT * KB * T
        self.cone = self._build("cone", 0.0)
        self.gaps: Dict[float, np.ndarray] = {}
        for eg in EG_KT_CANDIDATES:
            self.gaps[float(eg)] = self._build("hardgap", float(eg) * KB * T)

    def _build(self, model: str, Eg: float) -> np.ndarray:
        n = np.empty(len(self.EF_grid))
        p = np.empty(len(self.EF_grid))
        for i, ef in enumerate(self.EF_grid):
            n[i], p[i] = carrier_np(ef, self.T, model, 1.0, Eg)
        RH, Rs = rh_rs_from_np(n, p)
        RHn = RH / np.max(np.abs(RH))
        Rsn = Rs / np.max(np.abs(Rs))
        return np.column_stack([RHn, Rsn])


def _fit_nearest(data_xy: np.ndarray, model_xy: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """Nearest-curve fit in normalised pair space (guide p.8)."""
    d2 = ((data_xy[:, None, :] - model_xy[None, :, :]) ** 2).sum(axis=2)
    j_nearest = np.argmin(d2, axis=1)
    rms = float(np.sqrt(np.mean(np.min(d2, axis=1))))
    return j_nearest, np.min(d2, axis=1), rms


def _normalise_pair(RH: np.ndarray, Rs: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Normalise R_H and R_s independently by their own maxima (guide p.6)."""
    return RH / np.max(np.abs(RH)), Rs / np.max(np.abs(Rs))


def _select_model(r_cone: float, best_gap: float, r_gap: float) -> Tuple[str, float]:
    """15% improvement rule (guide p.8)."""
    if r_gap < 0.85 * r_cone and best_gap >= 1.0:
        return "hardgap", best_gap
    return "cone", 0.0


def fit_once(RH_mean: np.ndarray, Rs_mean: np.ndarray, lib: ModelLibrary
             ) -> Tuple[str, float, float, float, np.ndarray]:
    """Fit the repeat means once. Returns model, Eg/kBT, r_cone, r_gap, EF indices."""
    RHn, Rsn = _normalise_pair(RH_mean, Rs_mean)
    data_xy = np.column_stack([RHn, Rsn])

    _, _, r_cone = _fit_nearest(data_xy, lib.cone)

    best_gap, best_r = 0.0, np.inf
    for eg, curve in lib.gaps.items():
        _, _, r = _fit_nearest(data_xy, curve)
        if r < best_r:
            best_r, best_gap = r, eg

    model, eg = _select_model(r_cone, best_gap, best_r)
    if model == "hardgap":
        idx, _, _ = _fit_nearest(data_xy, lib.gaps[eg])
    else:
        idx, _, _ = _fit_nearest(data_xy, lib.cone)
        best_r = r_cone
    return model, eg, r_cone, best_r, idx


def run_l2(n_boot: int = 200, seed: int = 20260921) -> Dict:
    """Run the complete L2 analysis with bootstrap uncertainty."""
    meta = json.loads((DATA_DIR / "L2_meta.json").read_text(encoding="utf-8"))
    df = pd.read_csv(DATA_DIR / "L2_data.csv")
    T = float(meta["T_K"])

    idxs = np.sort(df["measurement_index"].unique())
    n_idx = len(idxs)
    RH_mean = np.empty(n_idx)
    Rs_mean = np.empty(n_idx)
    RH_std = np.empty(n_idx)
    Rs_std = np.empty(n_idx)
    reps_by_idx = []
    for i, m in enumerate(idxs):
        sub = df[df["measurement_index"] == m]
        reps_by_idx.append(sub[["R_H_raw", "R_xx_raw"]].to_numpy(dtype=float))
        RH_mean[i] = sub["R_H_raw"].mean()
        Rs_mean[i] = sub["R_xx_raw"].mean()
        RH_std[i] = sub["R_H_raw"].std(ddof=1)
        Rs_std[i] = sub["R_xx_raw"].std(ddof=1)

    # ---- locate the R_H sign change (gate check) ----
    RH_mean_signed = np.asarray(RH_mean)
    sign = np.sign(RH_mean_signed)
    cross_indices = np.where(sign[1:] != sign[:-1])[0]
    zero_crossing_pairs = [
        [int(idxs[j]), int(idxs[j + 1])] for j in cross_indices
    ]

    lib = ModelLibrary(T)

    # ---- central fit ----
    model, eg_kt, r_cone, r_gap, idx_central = fit_once(RH_mean, Rs_mean, lib)
    EF_central = lib.EF_grid[idx_central]

    # ---- bootstrap over the three repeats ----
    rng = np.random.default_rng(seed)
    eg_boot = np.empty(n_boot)
    EF_boot = np.empty((n_boot, n_idx))
    hardgap_boot = np.zeros(n_boot, dtype=bool)
    for b in range(n_boot):
        RH_rep = np.empty(n_idx)
        Rs_rep = np.empty(n_idx)
        for i in range(n_idx):
            row = reps_by_idx[i][rng.integers(0, 3)]
            RH_rep[i] = row[0]
            Rs_rep[i] = row[1]
        m_b, eg_b, r_c, r_g, idx_b = fit_once(RH_rep, Rs_rep, lib)
        eg_boot[b] = eg_b
        EF_boot[b] = lib.EF_grid[idx_b]
        hardgap_boot[b] = m_b == "hardgap"

    eg_median = float(np.median(eg_boot))
    eg_lo, eg_hi = float(np.percentile(eg_boot, 16)), float(np.percentile(eg_boot, 84))
    eg_uncertainty = 0.5 * (eg_hi - eg_lo)
    EF_lo = np.percentile(EF_boot, 16, axis=0)
    EF_hi = np.percentile(EF_boot, 84, axis=0)
    frac_hardgap = float(hardgap_boot.mean())

    # ---- model figure: normalised R_H-R_s space ----
    RHn, Rsn = _normalise_pair(RH_mean, Rs_mean)
    data_xy = np.column_stack([RHn, Rsn])
    curve = lib.cone if model == "cone" else lib.gaps[eg_kt]

    plt.figure(figsize=(7, 5.2))
    plt.plot(curve[:, 0], curve[:, 1], "-", color="#1f77b4", lw=2,
             label=f"selected model: {model}"
                   + ("" if model == "cone" else rf", $E_g={eg_kt:.2f}\,k_BT$"))
    plt.plot(curve[:, 0], curve[:, 1], "k.", markersize=0.6, alpha=0.4)
    plt.plot(data_xy[:, 0], data_xy[:, 1], "o", color="crimson", ms=5,
             label="mean measured pairs")
    plt.plot(data_xy[0, 0], data_xy[0, 1], "g*", ms=16, label="first index")
    plt.plot(data_xy[-1, 0], data_xy[-1, 1], "m*", ms=16, label="last index")
    plt.xlabel(r"normalised $R_H$ (sign preserved)")
    plt.ylabel(r"normalised $R_{xx}$")
    plt.title(
        rf"L2 G14: normalised pair space -- $r_{{cone}}={r_cone:.4f}$, "
        rf"$r_{{gap}}={r_gap:.4f}$"
    )
    plt.legend(loc="best")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    fig_model = FIG_DIR / "L2_model_fit.png"
    plt.savefig(fig_model, dpi=200)
    plt.close()

    # ---- trajectory figure ----
    plt.figure(figsize=(7, 4.8))
    plt.plot(idxs, EF_central, "o-", color="#1f77b4", label="assigned $E_F$")
    plt.fill_between(idxs, EF_lo, EF_hi, color="#1f77b4", alpha=0.25,
                     label="bootstrap 16-84% band")
    plt.xlabel("measurement index")
    plt.ylabel(r"Fermi level $E_F$ (eV)")
    plt.title(rf"L2 G14: Fermi-level trajectory ($n_{{boot}}={n_boot}$, seed {seed})")
    plt.legend(loc="best")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    fig_traj = FIG_DIR / "L2_trajectory.png"
    plt.savefig(fig_traj, dpi=200)
    plt.close()

    # best hard-gap candidate for the mean fit (already tracked in fit_once;
    # recompute its rms here for reporting alongside the selection)
    best_gap_rms = r_gap if model == "hardgap" else min(
        _fit_nearest(data_xy, lib.gaps[eg])[2] for eg in lib.gaps)
    best_gap_kt = eg_kt if model == "hardgap" else min(
        lib.gaps, key=lambda eg: _fit_nearest(data_xy, lib.gaps[eg])[2])

    results = {
        "model": model,
        "Eg_kT": 0.0 if model == "cone" else eg_kt,
        "Eg_uncertainty_kT": 0.0 if model == "cone" else eg_uncertainty,
        "EF_trajectory_eV": [float(x) for x in EF_central],
    }
    meta_out = {
        "T_K": T,
        "n_index": n_idx,
        "RH_zero_crossing_pairs": zero_crossing_pairs,
        "r_cone": r_cone,
        "r_gap": r_gap,
        "best_gap_kT": best_gap_kt,
        "best_gap_rms": best_gap_rms,
        "eg_median_kT": eg_median,
        "eg_16_84_kT": [eg_lo, eg_hi],
        "EF_16_84_eV": [EF_lo.tolist(), EF_hi.tolist()],
        "frac_hardgap": frac_hardgap,
        "bootstrap_seed": seed,
        "bootstrap_n": n_boot,
        "model_figure": str(fig_model.relative_to(OUTPUT_DIR)),
        "trajectory_figure": str(fig_traj.relative_to(OUTPUT_DIR)),
    }
    return {"L2": results, "L2_meta": meta_out}
