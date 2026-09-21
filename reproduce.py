"""QXU6028 G14 one-command reproduction pipeline.

Usage:
    python reproduce.py            # regular group data -> results.json
    python reproduce.py blind      # blind-test folder -> blind_results.json
    python reproduce.py --check    # run the built-in verification checks only

The pipeline reads the untouched group data from data/regular_G14 (or
data/blind_GNN for the blind run), recomputes L1-L3 and writes the results
into the exact results_template.json schema. No value is hand-edited.

Environment: Python 3.10+, numpy, pandas, matplotlib (Python 3.9.10 works).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import src.common as common  # noqa: E402
from src.common import setup_output_dirs  # noqa: E402

SEED = 20260921          # recorded random seed for all stochastic steps
N_BOOT = 200             # L2 bootstrap replicates
N_NOISE = 500            # L3 noise-only detection-limit vectors
PIPELINE_VERSION = "QXU6028-G14-pipeline-v1.0"


def _load_template(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(blind: bool = False) -> dict:
    from src.l1 import run_l1
    from src.l2 import run_l2
    from src.l3 import run_l3

    if blind:
        blind_dirs = sorted(ROOT.glob("data/blind_G*"))
        if len(blind_dirs) != 1:
            raise FileNotFoundError(
                "Expected exactly one data/blind_GNN folder for the blind run.")
        # redirect the data path for this process only
        common.DATA_DIR = blind_dirs[0]
        common.RESULTS_TEMPLATE = blind_dirs[0] / "results_template.json"

    template = _load_template(common.RESULTS_TEMPLATE)
    assert template.get("schema_version") == "QXU6028-results-v1"

    l1 = run_l1()
    l2 = run_l2(n_boot=N_BOOT, seed=SEED)
    l3 = run_l3(noise_seed=SEED, n_noise=N_NOISE)

    out = dict(template)
    out["pipeline_commit"] = "REPLACE_WITH_GIT_COMMIT_HASH"
    out["pipeline_version"] = PIPELINE_VERSION
    out["L1"].update({k: float(v) for k, v in l1["L1"].items()})
    out["L2"].update(l2["L2"])
    out["L3"].update(l3["L3"])
    out["_meta"] = {
        "L1": {k: (v if isinstance(v, (str, list, dict, bool)) or v is None
                   else float(v)) for k, v in l1["L1_meta"].items()},
        "L2": l2["L2_meta"],
        "L3": l3["L3_meta"],
        "seeds": {"l2_bootstrap": SEED, "l3_noise": SEED},
        "pipeline_version": PIPELINE_VERSION,
    }
    return out


def _validate(out: dict) -> list:
    """Built-in verification checks (guide pp.15-16)."""
    ok, bad = [], []
    checks = []

    L1, L2, L3 = out["L1"], out["L2"], out["L3"]

    # L1 reference ratios (exact checks, guide p.5)
    from src.l1 import n_band, n_fermi_num
    from src.common import DATA_DIR
    params = json.loads((DATA_DIR / "L1_params.json").read_text(encoding="utf-8"))
    c, T = float(params["c"]), float(params["T"])
    ratios = [n_band(ef, T, c) / n_fermi_num(ef, T, c) for ef in (0.0, 0.10, 0.20)]
    checks.append(("L1 ratio at EF=0 == 1.00", abs(ratios[0] - 1.0) < 1e-6))
    checks.append(("L1 ratio at EF=0.10 ~ 2.60", abs(ratios[1] - 2.60) < 0.05))
    checks.append(("L1 ratio at EF=0.20 ~ 5.10", abs(ratios[2] - 5.10) < 0.05))
    checks.append(("L1 correction factor finite and > 1",
                   np.isfinite(L1["correction_factor"]) and L1["correction_factor"] > 1))
    checks.append(("L1 corrected mobility > 0", L1["mobility_corrected_cm2_Vs"] > 0))

    # L2 checks
    checks.append(("L2 model in {cone, hardgap}", L2["model"] in ("cone", "hardgap")))
    n_idx = out["_meta"]["L2"]["n_index"]
    checks.append(("L2 trajectory length == n indices",
                   len(L2["EF_trajectory_eV"]) == n_idx))
    checks.append(("L2 Eg_kT == 0 for cone or >= 0.5 for gap",
                   (L2["model"] == "cone" and L2["Eg_kT"] == 0.0)
                   or (L2["model"] == "hardgap" and L2["Eg_kT"] >= 0.5)))
    checks.append(("L2 bootstrap hard-gap fraction in [0,1]",
                   0.0 <= out["_meta"]["L2"]["frac_hardgap"] <= 1.0))

    # L3 checks
    m = np.asarray(L3["map"], dtype=float)
    checks.append(("L3 map is 100 finite values",
                   m.shape == (100,) and np.all(np.isfinite(m))))
    checks.append(("L3 map has zero mean", abs(m.mean()) < 1e-9))
    checks.append(("L3 row sums ~ 0", out["_meta"]["L3"]["row_sum_max"] < 1e-11))
    checks.append(("L3 pass field is boolean", isinstance(L3["pass"], bool)))
    checks.append(("L3 confidence in {clear, borderline}",
                   L3["confidence"] in ("clear", "borderline")))

    for name, passed in checks:
        (ok if passed else bad).append(name)
    return bad


def write_outputs(out: dict, blind: bool = False) -> None:
    setup_output_dirs()
    name = "blind_results.json" if blind else "results.json"
    target = ROOT / "outputs" / name
    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {target}")
    for fig in out["_meta"].get("L1", {}).get("figure", ""), \
                out["_meta"]["L2"].get("model_figure", ""), \
                out["_meta"]["L2"].get("trajectory_figure", ""), \
                out["_meta"]["L3"].get("map_figure", ""), \
                out["_meta"]["L3"].get("method_figure", ""):
        p = ROOT / "outputs" / fig
        print(f"figure ok: {p}" if p.exists() else f"figure MISSING: {p}")


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT,
            stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "NO_GIT_REPO"


def main() -> int:
    blind = "--blind" in sys.argv or "blind" in sys.argv[1:2]
    check_only = "--check" in sys.argv

    if check_only:
        # regenerate from scratch, then validate without writing
        out = run(blind=blind)
        bad = _validate(out)
        if bad:
            print("FAILED checks:")
            for b in bad:
                print(f"  - {b}")
            return 1
        print("all built-in checks passed")
        return 0

    out = run(blind=blind)
    bad = _validate(out)
    for b in bad:
        print(f"WARNING: check failed: {b}")

    hash_ = git_commit_hash()
    if hash_ != "NO_GIT_REPO":
        out["pipeline_commit"] = hash_
    write_outputs(out, blind=blind)
    print(f"pipeline_commit = {out['pipeline_commit']}")

    if blind:
        (ROOT / "outputs" / "pipeline_commit.txt").write_text(
            out["pipeline_commit"] + "\n", encoding="utf-8")
        print("wrote outputs/pipeline_commit.txt (run_log.txt: save your "
              "terminal output)")
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
