"""L1 -- forward carrier counting.

Question: by how much does the band-edge count (integral from E = 0) mis-state
carrier density and mobility relative to the Fermi-referenced count
(integral from E = E_F)?

Guide reference: Practical Methods Guide pp.4-5.
"""
import json
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .common import DATA_DIR, E_CHARGE, EMAX, FIG_DIR, KB, NA, OUTPUT_DIR, fermi


def n_band(EF: float, T: float, c: float) -> float:
    """Band-edge count: integrate g(E)=c*E from E=0 to E_max."""
    E = np.linspace(0.0, EMAX, 20001)
    return NA * np.trapezoid(c * E * fermi(E, EF, T), E)


def n_fermi_num(EF: float, T: float, c: float) -> float:
    """Fermi-referenced count: integrate g(E)=c*E from E=EF to E_max."""
    E = np.linspace(EF, EMAX, 20001)
    return NA * np.trapezoid(c * E * fermi(E, EF, T), E)


def n_fermi_closed(EF: float, T: float, c: float) -> float:
    """Closed form of the Fermi-referenced integral for a linear DoS.

    n_F = NA * c * kT * (EF*ln(2) + (pi^2/12)*kT)
    """
    kT = KB * T
    return NA * c * kT * (EF * np.log(2) + (np.pi ** 2 / 12.0) * kT)


def _crossing(EF_grid: np.ndarray, C: np.ndarray, target: float) -> float:
    """First E_F where C(E_F) crosses `target` (linear interpolation)."""
    above = C >= target
    idx = np.argmax(above)
    if idx == 0 or not above[idx]:
        return float("nan")
    e0, e1 = EF_grid[idx - 1], EF_grid[idx]
    c0, c1 = C[idx - 1], C[idx]
    return float(e0 + (target - c0) * (e1 - e0) / (c1 - c0))


def run_l1() -> Dict:
    """Run the complete L1 analysis. Returns the L1 results dict."""
    params = json.loads((DATA_DIR / "L1_params.json").read_text(encoding="utf-8"))
    df = pd.read_csv(DATA_DIR / "L1_data.csv")

    c = float(params["c"])
    T = float(params["T"])
    EF_op = float(params["EF_op_eV"])
    rho = float(params["rho_ohm_sq"])

    # ---- reference checks (guide p.5) ----
    check_EFs = [0.0, 0.073, 0.100, 0.200]
    checks: List[Tuple[float, float]] = []
    for ef in check_EFs:
        ratio = n_band(ef, T, c) / n_fermi_num(ef, T, c)
        checks.append((ef, ratio))

    # ---- sweep: C(E_F) = n_band / n_Fermi, using supplied n_band column ----
    EF_sweep = df["EF_eV"].to_numpy(dtype=float)
    n_band_supplied = df["n_band_cm2"].to_numpy(dtype=float)
    nF_sweep = np.array([n_fermi_num(ef, T, c) for ef in EF_sweep])
    C_sweep = n_band_supplied / nF_sweep

    # ---- recomputed band count as an internal consistency check ----
    n_band_recomputed = np.array([n_band(ef, T, c) for ef in EF_sweep])
    recompute_max_rel_err = float(
        np.max(np.abs(n_band_recomputed - n_band_supplied) / n_band_supplied)
    )

    # ---- exact operating point (never the nearest CSV row) ----
    nF_op = n_fermi_num(EF_op, T, c)
    nF_op_closed = n_fermi_closed(EF_op, T, c)
    nB_op = n_band(EF_op, T, c)
    correction_factor = nB_op / nF_op
    mu_corrected = 1.0 / (E_CHARGE * nF_op * rho)  # cm^2 V^-1 s^-1
    mu_uncorrected = 1.0 / (E_CHARGE * nB_op * rho)

    # ---- crossings used in the figure ----
    EF_C2 = _crossing(EF_sweep, C_sweep, 2.0)
    EF_C4 = _crossing(EF_sweep, C_sweep, 4.0)

    # ---- L1 figure: C(E_F), operating point, C=2 and C=4 crossings ----
    plt.figure(figsize=(7, 4.8))
    plt.plot(EF_sweep, C_sweep, "o-", color="#1f77b4", label=r"$C(E_F)=n_{band}/n_{Fermi}$")
    plt.axvline(EF_op, color="crimson", linestyle="--",
                label=rf"operating point $E_F={EF_op:.4}$ eV")
    plt.plot(EF_op, correction_factor, "r*", markersize=14)
    for target, col in ((2.0, "green"), (4.0, "darkorange")):
        plt.axhline(target, color=col, linestyle=":", alpha=0.8)
        x = _crossing(EF_sweep, C_sweep, target)
        if np.isfinite(x):
            plt.axvline(x, color=col, linestyle=":", alpha=0.4)
            plt.annotate(fr"$C={target:.0f}$ at $E_F\approx{x:.3f}$ eV",
                         xy=(x, target), xytext=(x + 0.012, target + 0.25),
                         fontsize=9, color=col)
    plt.xlabel(r"Fermi level $E_F$ (eV)")
    plt.ylabel(r"correction factor $C = n_{band}/n_{Fermi}$")
    plt.title("L1 G14: band-edge vs Fermi-referenced carrier count")
    plt.legend(loc="upper left")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    fig_path = FIG_DIR / "L1_correction_sweep.png"
    plt.savefig(fig_path, dpi=200)
    plt.close()

    results = {
        "correction_factor": correction_factor,
        "n_fermi_op_cm2": nF_op,
        "mobility_corrected_cm2_Vs": mu_corrected,
    }
    meta = {
        "checks": [{"EF_eV": ef, "ratio": r} for ef, r in checks],
        "n_fermi_op_closed_cm2": nF_op_closed,
        "closed_vs_numerical_rel_diff": abs(nF_op_closed - nF_op) / nF_op,
        "n_band_op_cm2": nB_op,
        "mu_uncorrected_cm2_Vs": mu_uncorrected,
        "EF_C2_eV": EF_C2,
        "EF_C4_eV": EF_C4,
        "n_band_recompute_max_rel_err": recompute_max_rel_err,
        "figure": str(fig_path.relative_to(OUTPUT_DIR)),
        "T_K": T,
        "EF_op_eV": EF_op,
        "rho_ohm_sq": rho,
        "c": c,
    }
    return {"L1": results, "L1_meta": meta}
