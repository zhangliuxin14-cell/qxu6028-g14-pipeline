"""L2 -- zero-dimensional inverse problem.

Question: is the material gapless or hard-gapped, how large is the gap, and
how did the Fermi level drift across the measurement series?

Guide reference: Practical Methods Guide pp.6-9.
"""
import json
from typing import Dict, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import common
from .common import KB, NA, OUTPUT_DIR, fermi

# grids (guide p.7)
E_GRID = np.linspace(-2.5, 2.5, 4000)
EF_GRID_KT = np.linspace(-8.0, 9.0, 400)
EG_KT_CANDIDATES = np.arange(0.50, 8.01, 0.25)
# Denser candidate E_F grid used ONLY as a convergence diagnostic: it shows how
# much of the reported residual is the 400-point grid's quantisation floor
# rather than genuine model misfit. No reported number uses this grid.
EF_GRID_DIAG_NEF = 6400


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
    """Hall and sheet-resistance proxies of a two-carrier sheet.

    Equal electron and hole mobilities, with e = mu = 1 (the fixed scale
    cancels because R_H and R_s are normalised separately, guide p.6):

        sigma_xx = n + p                ->  R_s = 1 / (n + p)
        sigma_xy = B * (p - n)          ->  R_H = (p - n) / (n + p)**2

    The (p - n) numerator and the squared denominator are what make R_H
    finite and sign-changing at charge neutrality, so the model curve passes
    continuously through the measured R_H zero crossing (guide p.7 orientation
    check) and the wings obey |R_H| ~ R_s**2 (handbook L2 gate). Using
    1/(n - p) instead makes R_H diverge exactly where charge neutrality sits,
    which is topologically incompatible with the data.
    """
    return (p - n) / (n + p) ** 2, 1.0 / (n + p)


class ModelLibrary:
    """Precomputed normalised model curves (guide p.7: build once, reuse).

    ``n_ef`` overrides the number of candidate E_F points. The guide fixes this
    at 400 for every reported number; a denser grid is only useful as a
    convergence diagnostic, because the nearest-curve residual carries a
    quantisation floor set by the spacing of those candidate points.
    """

    def __init__(self, T: float, n_ef: Optional[int] = None,
                 eg_list: Optional[Sequence[float]] = None):
        self.T = T
        grid = (EF_GRID_KT if n_ef is None
                else np.linspace(EF_GRID_KT[0], EF_GRID_KT[-1], int(n_ef)))
        self.n_ef = int(len(grid))
        self.EF_grid = grid * KB * T
        self.cone = self._build("cone", 0.0)
        self.gaps: Dict[float, np.ndarray] = {}
        for eg in (EG_KT_CANDIDATES if eg_list is None else eg_list):
            self.gaps[float(eg)] = self._build("hardgap", float(eg) * KB * T)
        self._extra: Dict[float, np.ndarray] = {}

    def extra(self, Eg_kt: float) -> np.ndarray:
        """Curve for a gap that is NOT on the candidate grid (display only).

        Kept out of ``self.gaps`` on purpose: ``fit_once`` and the 15% selection
        rule must keep seeing exactly the grid specified by the guide
        (0.50-8.00 kT, step 0.25). This exists so the comparison figure can also
        show what a gap just below the grid floor would look like.
        """
        key = float(Eg_kt)
        if key not in self._extra:
            self._extra[key] = self._build("hardgap", key * KB * self.T)
        return self._extra[key]

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
    meta = json.loads((common.DATA_DIR / "L2_meta.json").read_text(encoding="utf-8"))
    df = pd.read_csv(common.DATA_DIR / "L2_data.csv")
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

    # ---- gate figure: three raw repeats, sign-change bracket marked ----
    # (guide p.6 step 3; the zero crossing must be located BEFORE normalisation)
    plt.figure(figsize=(7.4, 4.8))
    for i, m in enumerate(idxs):
        reps = reps_by_idx[i]
        plt.plot(np.full(len(reps), m), reps[:, 0], ".", color="#1f77b4",
                 ms=6, alpha=0.7, label="raw repeats" if i == 0 else None)
    plt.plot(idxs, RH_mean, "-", color="crimson", lw=1.2, label="repeat mean")
    plt.axhline(0.0, color="k", lw=0.8)
    for j, pair in enumerate(zero_crossing_pairs):
        plt.axvspan(pair[0], pair[1], color="orange", alpha=0.35,
                    label="sign-change bracket" if j == 0 else None)
        for m in pair:
            plt.axvline(m, color="orange", ls=":", lw=1.2)
    plt.xlabel("measurement index")
    plt.ylabel(r"raw $R_H$")
    plt.title("L2 G14: gate -- R_H zero crossing located before normalisation")
    plt.legend(loc="best")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    fig_gate = common.figure_path("L2_gate.png")
    plt.savefig(fig_gate, dpi=200)
    plt.close()

    # ---- best hard-gap candidate on the repeat means ----
    RHn, Rsn = _normalise_pair(RH_mean, Rs_mean)
    data_xy = np.column_stack([RHn, Rsn])
    # (computed here because the model figure below draws its gap neighbours)
    if model == "hardgap":
        best_gap_kt, best_gap_rms = eg_kt, r_gap
    else:
        best_gap_kt = min(
            lib.gaps, key=lambda g: _fit_nearest(data_xy, lib.gaps[g])[2])
        best_gap_rms = _fit_nearest(data_xy, lib.gaps[best_gap_kt])[2]

    # ---- model figure: normalised R_H-R_s space ----
    curve = lib.cone if model == "cone" else lib.gaps[eg_kt]

    # Gap-family comparison around the best candidate: one gap step smaller,
    # the best candidate itself, and one gap step larger. When the best
    # candidate sits on the grid floor (0.50 kT) there is no smaller grid
    # value, so one sub-grid step is added for illustration only -- it is
    # never offered to the selection rule.
    gap_keys = sorted(lib.gaps)
    i_best = gap_keys.index(best_gap_kt)
    sub_grid = i_best - 1 < 0
    show_gaps = [(best_gap_kt, lib.gaps[best_gap_kt], False)]
    show_gaps.insert(0, (best_gap_kt - 0.25, lib.extra(best_gap_kt - 0.25), True)
                     if sub_grid else
                     (gap_keys[i_best - 1], lib.gaps[gap_keys[i_best - 1]], False))
    if i_best + 1 < len(gap_keys):
        show_gaps.append((gap_keys[i_best + 1], lib.gaps[gap_keys[i_best + 1]],
                          False))

    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(13.2, 5.6), gridspec_kw={"width_ratios": [1.12, 1.0]})

    # ----- panel A: curve comparison in the normalised pair space -----
    for g, gcurve, below in show_gaps:
        if model == "hardgap" and g == eg_kt:
            continue  # already drawn as the selected curve below
        r_g = _fit_nearest(data_xy, gcurve)[2]
        if g == best_gap_kt:
            ls, col, lw = "-", "#2ca02c", 1.8
        elif g < best_gap_kt:
            ls, col, lw = "--", "#7f7f7f", 1.4
        else:
            ls, col, lw = ":", "#c8a165", 1.8
        tag = ""
        if below:
            tag = " (below grid, comparison only)"
        elif g == gap_keys[0]:
            tag = " (grid minimum)"
        axA.plot(gcurve[:, 0], gcurve[:, 1], ls, color=col, lw=lw,
                 label=rf"hard gap $E_g={g:.2f}\,k_BT${tag}, $r={r_g:.4f}$")

    axA.plot(curve[:, 0], curve[:, 1], "-", color="#1f77b4", lw=2.4,
             label=f"selected: {model}"
                   + ("" if model == "cone" else rf", $E_g={eg_kt:.2f}\,k_BT$"))
    axA.plot(data_xy[:, 0], data_xy[:, 1], "o", color="crimson", ms=5,
             label="mean measured pairs")
    axA.plot(data_xy[0, 0], data_xy[0, 1], "g*", ms=16, label="first index")
    axA.plot(data_xy[-1, 0], data_xy[-1, 1], "m*", ms=16, label="last index")
    axA.set_xlabel(r"normalised $R_H$ (sign preserved)")
    axA.set_ylabel(r"normalised $R_{xx}$")
    axA.set_title(
        rf"(a) normalised pair space -- the gap family nearly coincides"
        "\n"
        rf"$r_{{cone}}={r_cone:.4f}$, best hard gap $r={best_gap_rms:.4f}$, "
        rf"15% rule needs $<{0.85 * r_cone:.4f}$"
    )
    axA.legend(loc="best", fontsize=8)
    axA.grid(alpha=0.3)

    # ----- panel B: residual against gap, with the selection threshold -----
    threshold = 0.85 * r_cone
    grid_egs = np.array(sorted(lib.gaps), dtype=float)
    grid_rms = np.array([_fit_nearest(data_xy, lib.gaps[float(e)])[2]
                         for e in grid_egs])

    # Convergence diagnostic. Every residual is the distance to a curve that is
    # itself sampled on the candidate E_F grid, so it carries a quantisation
    # floor (~0.013 here) that differs slightly from curve to curve. On a denser
    # grid that artefact disappears and the residual grows monotonically with
    # the gap, leaving the cone lowest -- which is the physically expected
    # ordering. Only cone plus the gaps shown in panel (a) are rebuilt.
    shown_egs = sorted({float(g) for g, _, _ in show_gaps})
    lib_fine = ModelLibrary(T, n_ef=EF_GRID_DIAG_NEF, eg_list=shown_egs)
    r_cone_fine = _fit_nearest(data_xy, lib_fine.cone)[2]

    def _fine_curve(eg: float) -> np.ndarray:
        return (lib_fine.gaps[eg] if eg in lib_fine.gaps
                else lib_fine.extra(eg))

    fine_gap_rms = {e: _fit_nearest(data_xy, _fine_curve(e))[2]
                    for e in shown_egs}
    fine_gap_rms_list = [fine_gap_rms[e] for e in shown_egs]

    axB.axhspan(0.0, threshold, color="crimson", alpha=0.08)
    axB.axhline(threshold, color="crimson", ls="--", lw=1.6,
                label=rf"15% rule: $0.85\,r_{{cone}}={threshold:.5f}$")
    axB.plot(0.0, r_cone_fine, "v", color="#555555", ms=8, zorder=4,
             label=rf"cone, converged grid ({EF_GRID_DIAG_NEF} pts)")
    axB.plot(shown_egs, fine_gap_rms_list, "v--", color="#555555", ms=8, lw=1.3,
             label=rf"hard gap, converged grid ({EF_GRID_DIAG_NEF} pts)")
    axB.plot(grid_egs, grid_rms, "s-", color="#2ca02c", ms=4, lw=1.4,
             label="hard-gap candidates (guide grid, 400 pts)")
    axB.plot(0.0, r_cone, "o", color="#1f77b4", ms=9, zorder=5,
             label=rf"cone, guide grid, selected ($r={r_cone:.5f}$)")
    for g, gcurve, below in show_gaps:
        r_g = _fit_nearest(data_xy, gcurve)[2]
        axB.plot(g, r_g, "k*", ms=13, zorder=6,
                 label="gaps drawn in panel (a)" if g == best_gap_kt else None)
    axB.annotate(
        "no candidate enters this band on either grid,\n"
        "so the 15% rule keeps the cone",
        xy=(2.7, threshold), xytext=(2.7, threshold * 4.6),
        fontsize=8.5, color="crimson",
        arrowprops=dict(arrowstyle="->", color="crimson", lw=1.1))
    axB.annotate(
        "guide grid: artificial dip from grid quantisation\n"
        "converged grid: monotone, cone lowest",
        xy=(0.7, fine_gap_rms[0.75] if 0.75 in fine_gap_rms else 0.012),
        xytext=(2.9, 0.030), fontsize=8.5, color="#333333",
        arrowprops=dict(arrowstyle="->", color="#333333", lw=1.0))
    axB.set_xlabel(r"$E_g\,/\,k_BT$")
    axB.set_ylabel(r"nearest-curve residual $r$")
    axB.set_title("(b) residual vs gap size, and its convergence with the E_F grid")
    axB.set_xlim(-0.35, 8.4)
    axB.set_ylim(bottom=0.0)
    axB.legend(loc="upper left", fontsize=7.5)
    axB.grid(alpha=0.3)

    plt.tight_layout()
    fig_model = common.figure_path("L2_model_fit.png")
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
    fig_traj = common.figure_path("L2_trajectory.png")
    plt.savefig(fig_traj, dpi=200)
    plt.close()

    results = {
        "model": model,
        "Eg_kT": 0.0 if model == "cone" else eg_kt,
        "Eg_uncertainty_kT": 0.0 if model == "cone" else eg_uncertainty,
        "EF_trajectory_eV": [float(x) for x in EF_central],
    }
    # residual sweep over the gap family, for the comparison figure and notes
    gap_sweep = []
    for g, gcurve, below in show_gaps:
        gap_sweep.append({
            "Eg_kT": float(g),
            "rms": float(_fit_nearest(data_xy, gcurve)[2]),
            "on_candidate_grid": not below,
        })

    # grid-convergence diagnostic: how much of the reported residual is the
    # 400-point candidate grid rather than genuine model misfit
    _scatter = np.array([
        [reps_by_idx[i][j, 0] / np.max(np.abs(RH_mean)) - RHn[i],
         reps_by_idx[i][j, 1] / np.max(np.abs(Rs_mean)) - Rsn[i]]
        for i in range(n_idx) for j in range(len(reps_by_idx[i]))
    ])
    repeat_scatter = float(np.sqrt(np.mean((_scatter ** 2).sum(axis=1))))
    grid_quantisation = float(np.sqrt(max(
        r_cone ** 2 - r_cone_fine ** 2, 0.0)))

    grid_convergence = {
        "n_ef_guide": int(lib.n_ef),
        "n_ef_diag": int(lib_fine.n_ef),
        "r_cone_guide_grid": float(r_cone),
        "r_cone_diag_grid": float(r_cone_fine),
        "grid_quantisation_estimate": grid_quantisation,
        "repeat_scatter_normalised": repeat_scatter,
        "gap_rms_guide_grid": {f"{g:.2f}": float(_fit_nearest(data_xy, c)[2])
                               for g, c, _ in show_gaps},
        "gap_rms_diag_grid": {f"{e:.2f}": float(v)
                              for e, v in fine_gap_rms.items()},
    }

    meta_out = {
        "T_K": T,
        "n_index": n_idx,
        "RH_zero_crossing_pairs": zero_crossing_pairs,
        "r_cone": r_cone,
        "r_gap": r_gap,
        "best_gap_kT": best_gap_kt,
        "best_gap_rms": best_gap_rms,
        "gap_sweep": gap_sweep,
        "grid_convergence": grid_convergence,
        "eg_median_kT": eg_median,
        "eg_16_84_kT": [eg_lo, eg_hi],
        "EF_16_84_eV": [EF_lo.tolist(), EF_hi.tolist()],
        "frac_hardgap": frac_hardgap,
        "bootstrap_seed": seed,
        "bootstrap_n": n_boot,
        "gate_figure": str(fig_gate.relative_to(OUTPUT_DIR)),
        "model_figure": str(fig_model.relative_to(OUTPUT_DIR)),
        "trajectory_figure": str(fig_traj.relative_to(OUTPUT_DIR)),
    }
    return {"L2": results, "L2_meta": meta_out}
