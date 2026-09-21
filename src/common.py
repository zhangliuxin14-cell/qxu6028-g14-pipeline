"""QXU6028 G14 pipeline -- shared constants and numerical helpers.

All constants follow the Practical Methods Guide 2026-27 exactly.
"""
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "regular_G14"
OUTPUT_DIR = ROOT / "outputs"
FIG_DIR = OUTPUT_DIR / "figures"
RESULTS_TEMPLATE = DATA_DIR / "results_template.json"

# ---------------------------------------------------------------------------
# Physical constants (guide p.3)
# ---------------------------------------------------------------------------
KB = 8.617333e-5        # eV / K
NA = 3.816e15           # areal atom density, cm^-2
E_CHARGE = 1.602176634e-19  # C
EMAX = 2.5              # eV, integration cutoff for L1
T_DEFAULT = 300.0       # K


def fermi(E: np.ndarray, EF: float, T: float) -> np.ndarray:
    """Fermi-Dirac occupation with the exponent clipped to [-60, 60]."""
    x = np.clip((E - EF) / (KB * T), -60, 60)
    return 1.0 / (np.exp(x) + 1.0)


def setup_output_dirs() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    FIG_DIR.mkdir(exist_ok=True)
