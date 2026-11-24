# G14 Pipeline — QXU6028 Virtual Labs L1–L3

Reproduction pipeline for the QXU6028 Polymer Devices coursework (group G14,
dataset `regular_G14`). One command recomputes every number, table entry and
figure in the report from the untouched data files.

## Quick start

```bash
pip install -r requirements.txt

python reproduce.py                 # regular data  -> outputs/results.json
python reproduce.py --check         # verification checks only, writes nothing
python reproduce.py --dataset blind # blind data    -> outputs/blind_results.json
```

`python reproduce.py blind` is accepted as well (same as `--dataset blind`).
Requires Python 3.10+ (3.9 works too), numpy, pandas, matplotlib.

The pipeline does not read anything outside the repository: the data folders
under `data/` are byte-for-byte copies of the released group data and blind
data, and `outputs/run_manifest.json` records their SHA-256 hashes so the
copy can be checked against the release.

## What a run produces

| File | Contents |
|---|---|
| `outputs/results.json` | machine-readable results in the `QXU6028-results-v1` schema (both runs use the same writer) |
| `outputs/blind_results.json` | the same for the blind data |
| `outputs/run_log.txt`, `run_log_blind.txt` | full terminal transcript of the run, written by the pipeline itself |
| `outputs/run_manifest.json` | UTC timestamp, Python/numpy/pandas versions, commit hash, seeds, input hashes |
| `outputs/pipeline_commit.txt` | HEAD commit of the blind run (required by the blind-test instructions) |
| `outputs/figures/*.png` | every figure used in the report (regular data) |
| `outputs/figures_blind/*.png` | the same six plots from the blind data — kept apart so a blind run cannot overwrite the figures the report quotes |

## Layout

```
g14_pipeline/
├── reproduce.py            # the only entry point
├── requirements.txt
├── data/
│   ├── results_template.json   # output schema, shared by both datasets
│   ├── regular_G14/            # released group data (do not edit)
│   └── blind_G14/              # released blind data (do not edit)
├── src/
│   ├── common.py           # constants, Fermi–Dirac, output paths
│   ├── l1.py               # L1 forward carrier counting
│   ├── l2.py               # L2 zero-dimensional inverse problem + bootstrap
│   └── l3.py               # L3 regularised 2-D reconstruction
├── outputs/                # results, logs, figures (regenerated, not hand-edited)
├── checkpoints/            # L1 checkpoint package submitted in Session 2
├── tools/contribution_report.py   # git-log based contribution table
└── docs/                   # checkpoints, AI records, authorship, blind run record
```

## Method summary

**L1.** Linear density of states g(E) = cE with c from `L1_params.json`;
Fermi–Dirac at T = 300 K. The band-edge count integrates from E = 0, the
Fermi-referenced count from E = E_F; C(E_F) = n_band / n_Fermi. Evaluated at
the exact operating point, not at the nearest table row. The corrected
mobility is n = 1/(e n_F ρ) with no extra 10^4 factor, because n[cm^-2] and
ρ[Ω/sq] already give cm^2/Vs.

**L2.** Repeats are averaged per index and the repeat scatter is kept as the
error bar. R_H and R_xx are normalised separately so that the sign of R_H
survives. Model library: ideal cone g = c|E| and hard gap g = 0 inside the gap,
g = c(|E| - E_g/2) outside. Transport proxies for equal mobilities:
R_s = 1/(n+p) and R_H = (p-n)/(n+p)^2, which vanishes at neutrality and has
\|R_H\| ∝ R_s^2 wings, as the handbook gate requires. Nearest-curve fit over
400 candidate E_F values; a hard gap is selected only if it lowers rms by 15%.
Bootstrap: 200 resamples, seed 20260921.

**L3.** SVD first: rank(A) = 92 of 100, so the null space is 8-dimensional, not
the single constant mode the guide mentions. Reconstruct with first-difference
Tikhonov regularisation, projection off the constant mode, and the
discrepancy-principle regularisation parameter (largest η whose residual still
matches the repeat noise). The wafer-scale planar trend and the local defects
are separated before features are reported: the extremum of a planar trend
always sits on the map boundary, so a boundary "feature" is the trend, not a
defect. Resolution and detection limit are measured by injecting known
single-pixel sources and adding noise-only vectors (500 draws, seed 20260921).

## Verification built into the run

`_validate()` in `reproduce.py` re-checks, on every run, the properties the
guide asks for and a few that past bugs would break: L1 reference ratios
(1.00 / 2.60 / 5.10), L2 curve topology (R_H crosses zero, R_s peaks there,
wings scale as R_s^2), L2 trajectory structure, L3 null-space/row-sum
conditions, L3 feature provenance (features must come from the detrended map,
the dominant one must be interior), η inside the scanned range, and that
`dataset_set` matches the folder actually read. A failed check exits non-zero,
so a silent regression cannot pass unnoticed.

## Key numbers (regenerate, never edit by hand)

| Quantity | Value |
|---|---|
| L1 correction factor C(E_F,op) | 2.8672 |
| L1 corrected sheet density | 3.727e11 cm^-2 |
| L1 corrected mobility | 3.824e4 cm^2/Vs |
| L2 model | cone (gapless), E_g = 0 |
| L2 residual | 0.0140 on the guide's 400-point grid; 0.0058 after mesh refinement (0.43 x the repeat noise) |
| L2 Fermi-level path | -0.068 -> +0.146 eV, neutrality between index 17 and 18 |
| L3 decision | fail (clear): max\|m\| = 0.0456 > 0.030 |
| L3 wafer-scale gradient | 1.01e-2 per probe pitch; the fitted plane reaches 3.8% at a corner |
| L3 local features | +0.0179 at (+0.3, +1.5); -0.0142 at (-0.9, -0.9) |
| L3 regularisation | 5.7e-2 x η₀ (discrepancy principle) |
| L3 resolution | 1.80 probe pitches |
| L3 detection limit | 6.46e-5 |

## Reproducibility notes

- Every stochastic step uses the fixed seed 20260921: the L2 bootstrap (200
  resamples) and the L3 noise draws (500 vectors). The seed is recorded in
  `results.json` under `_meta.seeds` and in the run manifest.
- `results.json` carries the commit that produced it (`pipeline_commit`). If
  git is not installed on the marking machine, the value is read directly from
  `.git/HEAD` instead of silently becoming `NO_GIT_REPO`. Note that
  `pipeline_commit` names the code commit, while the regenerated outputs are
  committed one step later, so a fresh run records the commit you ran from.
  Compare every field except that one.
- L2 residual values are reported on the guide's 400-point E_F grid, because
  that is the grid the assessment specifies. A convergence table (400 / 1600 /
  6400 points) is stored in `_meta.L2.grid_convergence`; it shows the 400-point
  residual is dominated by grid quantisation, not by model mismatch.

## Records

`docs/AUTHORSHIP.md` explains who wrote what and how that maps onto the commit
history; `docs/BLIND_HISTORY.md` records the blind-test run; `docs/CHECKPOINTS.md`
lists the per-session checkpoints; `docs/AI_error_ledger.md` and
`docs/AI_usage_log.md` record AI assistance as the brief requires.
