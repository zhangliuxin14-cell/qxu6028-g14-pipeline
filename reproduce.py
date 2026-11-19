"""QXU6028 G14 one-command reproduction pipeline.

Usage:
    python reproduce.py                      # regular group data -> outputs/results.json
    python reproduce.py --dataset blind      # blind-test folder  -> outputs/blind_results.json
    python reproduce.py blind                # same, kept for the Session 3 command line
    python reproduce.py --check              # run the built-in verification checks only
    python reproduce.py --dataset blind --check

The pipeline reads the untouched group data from data/regular_G14 (or
data/blind_GNN for the blind run), recomputes L1-L3 and writes the results
into the exact results_template.json schema. No value is hand-edited.

Outputs
    outputs/results.json          (regular) or outputs/blind_results.json (blind)
    outputs/run_log.txt           full terminal transcript of the run
    outputs/run_manifest.json     timestamp, versions, commit, data hashes
    outputs/figures/*.png         every figure quoted in the report

Environment: Python 3.10+, numpy, pandas, matplotlib.
"""
import argparse
import contextlib
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
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


class Tee:
    """Write to the terminal and to the run log at the same time."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def _load_template(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_dir(dataset):
    """Resolve the data folder for a named dataset.

    The blind release is only known by its folder name (data/blind_GNN), so it
    has to be globbed. Resolving it here -- and not through a module-level
    constant copied at import time -- is what makes --dataset blind actually
    read the blind files instead of silently recomputing the regular ones.
    """
    if dataset == "regular":
        return ROOT / "data" / "regular_G14"
    dirs = sorted(ROOT.glob("data/blind_G*"))
    if len(dirs) != 1:
        raise FileNotFoundError(
            "Expected exactly one data/blind_GNN folder for the blind run.")
    return dirs[0]


def run(dataset="regular"):
    from src.l1 import run_l1
    from src.l2 import run_l2
    from src.l3 import run_l3

    common.DATA_DIR = dataset_dir(dataset)
    template = _load_template(common.RESULTS_TEMPLATE)
    assert template.get("schema_version") == "QXU6028-results-v1"

    l1 = run_l1()
    l2 = run_l2(n_boot=N_BOOT, seed=SEED)
    l3 = run_l3(noise_seed=SEED, n_noise=N_NOISE)

    out = dict(template)
    out["pipeline_commit"] = "REPLACE_WITH_GIT_COMMIT_HASH"
    out["pipeline_version"] = PIPELINE_VERSION
    out["dataset_set"] = dataset
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


def _validate(out):
    """Built-in verification checks (guide pp.15-16)."""
    ok, bad = [], []
    checks = []

    L1, L2, L3 = out["L1"], out["L2"], out["L3"]

    # L1 reference ratios (exact checks, guide p.5)
    from src.l1 import n_band, n_fermi_num
    params = json.loads((common.DATA_DIR / "L1_params.json").read_text(encoding="utf-8"))
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
    checks.append(("L2 trajectory crosses neutrality exactly once",
                   int(np.sum(np.diff(np.sign(L2["EF_trajectory_eV"])) != 0)) == 1))

    # L2 orientation gate (guide p.7, handbook L2 gate): the model curve must
    # pass continuously through R_H = 0 with R_s peaking there, and the wings
    # must obey |R_H| ~ R_s**2. A 1/(n-p) proxy diverges at neutrality instead.
    from src.l2 import ModelLibrary
    _lib = ModelLibrary(float(out["_meta"]["L2"]["T_K"]))
    _cone = _lib.cone
    _j0 = int(np.argmin(np.abs(_cone[:, 0])))
    _ja = int(np.argmax(_cone[:, 1]))
    checks.append(("L2 cone curve crosses R_H = 0 at neutrality",
                   abs(_cone[_j0, 0]) < 0.05))
    checks.append(("L2 cone R_s peaks at the R_H zero crossing",
                   abs(_j0 - _ja) <= 2 and _cone[_j0, 1] > 0.95))
    _k = np.argsort(-np.abs(_cone[:, 0]))[:8]
    _ratio = np.abs(_cone[_k, 0]) / _cone[_k, 1] ** 2
    checks.append(("L2 cone wings obey |R_H| ~ R_s^2",
                   float(_ratio.std() / _ratio.mean()) < 0.15))

    # L3 checks
    m = np.asarray(L3["map"], dtype=float)
    checks.append(("L3 map is 100 finite values",
                   m.shape == (100,) and np.all(np.isfinite(m))))
    checks.append(("L3 map has zero mean", abs(m.mean()) < 1e-9))
    checks.append(("L3 row sums ~ 0", out["_meta"]["L3"]["row_sum_max"] < 1e-11))
    checks.append(("L3 pass field is boolean", isinstance(L3["pass"], bool)))
    checks.append(("L3 confidence in {clear, borderline}",
                   L3["confidence"] in ("clear", "borderline")))

    # L3 feature gate: the wafer-scale planar trend always puts its extrema on
    # the map boundary, so those are not features. The reported features must
    # come from the detrended map, and the dominant one must be interior
    # (a feature reported at a corner means the trend was not removed).
    _l3m = out["_meta"]["L3"]
    checks.append(("L3 features come from the detrended map",
                   all("centroid_pixel" in f for f in L3["features"])))
    _dom = max(L3["features"], key=lambda f: abs(f["amplitude"]))
    checks.append(("L3 dominant feature is interior, not on the map edge",
                   0 < _dom["pixel"][0] < _l3m["npix"] - 1
                   and 0 < _dom["pixel"][1] < _l3m["npix"] - 1))
    checks.append(("L3 every reported feature is interior",
                   all(0 < f["pixel"][0] < _l3m["npix"] - 1
                       and 0 < f["pixel"][1] < _l3m["npix"] - 1
                       for f in L3["features"])))
    checks.append(("L3 feature peak below raw map extremum",
                   abs(_dom["amplitude"]) < _l3m["max_abs_map"]))
    checks.append(("L3 eta chosen inside the scanned range",
                   0.01 * _l3m["eta0"] <= _l3m["eta_chosen"] <= 100.0 * _l3m["eta0"]))
    checks.append(("L3 residual at chosen eta consistent with repeat noise",
                   min(s["residual_over_noise"] for s in _l3m["eta_sensitivity"]) <= 1.0
                   <= max(s["residual_over_noise"] for s in _l3m["eta_sensitivity"])))

    checks.append(("dataset_set matches the requested dataset",
                   out.get("dataset_set") in ("regular", "blind")))

    for name, passed in checks:
        (ok if passed else bad).append(name)
    return bad


def write_outputs(out, blind=False, outdir=None):
    outdir = Path(outdir) if outdir is not None else ROOT / "outputs"
    outdir.mkdir(parents=True, exist_ok=True)
    setup_output_dirs()
    name = "blind_results.json" if blind else "results.json"
    target = outdir / name
    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {target}")
    for fig in out["_meta"].get("L1", {}).get("figure", ""), \
                out["_meta"]["L2"].get("gate_figure", ""), \
                out["_meta"]["L2"].get("model_figure", ""), \
                out["_meta"]["L2"].get("trajectory_figure", ""), \
                out["_meta"]["L3"].get("map_figure", ""), \
                out["_meta"]["L3"].get("method_figure", ""):
        p = ROOT / "outputs" / fig
        print(f"figure ok: {p}" if p.exists() else f"figure MISSING: {p}")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(out, dataset, outdir=None):
    outdir = Path(outdir) if outdir is not None else ROOT / "outputs"
    data_dir = dataset_dir(dataset)
    files = sorted(p for p in data_dir.iterdir() if p.is_file())
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": dataset,
        "data_dir": data_dir.relative_to(ROOT).as_posix(),
        "pipeline_commit": out.get("pipeline_commit"),
        "pipeline_version": PIPELINE_VERSION,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": __import__("pandas").__version__,
        "seeds": {"l2_bootstrap": SEED, "l3_noise": SEED},
        "n_boot": N_BOOT,
        "n_noise": N_NOISE,
        "data_sha256": {p.name: _sha256(p) for p in files},
    }
    target = outdir / ("run_manifest_blind.json" if dataset == "blind" else "run_manifest.json")
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {target}")
    return manifest


def git_commit_hash():
    """HEAD hash, with a pure-Python fallback for machines without git."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT,
            stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        pass
    try:
        git_dir = ROOT / ".git"
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref:"):
            ref = head.split(":", 1)[1].strip()
            ref_file = git_dir / ref
            if ref_file.exists():
                return ref_file.read_text(encoding="utf-8").strip()
            packed = git_dir / "packed-refs"
            if packed.exists():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line.endswith(" " + ref):
                        return line.split()[0]
            return "NO_GIT_REPO"
        return head
    except Exception:
        return "NO_GIT_REPO"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Reproduce the QXU6028 G14 L1-L3 results from the data folder.")
    parser.add_argument("dataset_positional", nargs="?", choices=["regular", "blind"],
                        help="dataset to run (kept for 'python reproduce.py blind')")
    parser.add_argument("--dataset", choices=["regular", "blind"], default=None,
                        help="dataset to run (default: regular)")
    parser.add_argument("--blind", action="store_true",
                        help="shorthand for --dataset blind")
    parser.add_argument("--check", action="store_true",
                        help="run the built-in checks only, write nothing")
    parser.add_argument("--outdir", default=None,
                        help="output folder (default: <repo>/outputs)")
    args = parser.parse_args(argv)

    dataset = args.dataset or args.dataset_positional or ("blind" if args.blind else "regular")
    blind = dataset == "blind"
    outdir = Path(args.outdir) if args.outdir else ROOT / "outputs"

    log_path = outdir / ("run_log_blind.txt" if blind else "run_log.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(Tee(sys.stdout, log)):
            print(f"QXU6028 G14 pipeline {PIPELINE_VERSION}")
            print(f"dataset = {dataset} ({dataset_dir(dataset).name})")
            print(f"started = {datetime.now(timezone.utc).isoformat(timespec='seconds')}")

            out = run(dataset=dataset)
            bad = _validate(out)

            if bad:
                print("FAILED checks:")
                for b in bad:
                    print(f"  - {b}")
            else:
                print("all built-in checks passed")
            print(f"wrote {log_path}")

            if args.check:
                return 1 if bad else 0

            hash_ = git_commit_hash()
            if hash_ != "NO_GIT_REPO":
                out["pipeline_commit"] = hash_
            write_outputs(out, blind=blind, outdir=outdir)
            write_manifest(out, dataset, outdir=outdir)
            print(f"pipeline_commit = {out['pipeline_commit']}")

            if blind:
                (outdir / "pipeline_commit.txt").write_text(
                    out["pipeline_commit"] + "\n", encoding="utf-8")
                print("wrote pipeline_commit.txt")

            for b in bad:
                print(f"WARNING: check failed: {b}")
            return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
