# Blind-test run record — G14

## Protocol

The pipeline was frozen before the blind data were touched: the analysis code,
thresholds, regularisation rule, seeds and model library are the same ones used
for data/regular_G14, and no parameter was tuned on the blind set. The only
change between the two runs is the dataset selector:

    python reproduce.py --dataset blind

which reads data/blind_G14, writes outputs/blind_results.json, outputs/run_log_blind.txt,
outputs/run_manifest_blind.json, outputs/figures_blind/ and outputs/pipeline_commit.txt.

## Runs

| Run | When (+0800) | Code commit | Why it was run | Retained as |
|---|---|---|---|---|
| A — first look | 2026-11-19 19:28 | f536ce8 | first execution on the blind data | docs/run_artifacts/blind_results_2026-11-19_first_look.json (git 8eb5923) |
| B — submitted | 2026-11-19 19:30 | d41ce42 | re-run after the interior-feature rule (see the deviation below) | docs/run_artifacts/blind_results_2026-11-19_submitted.json, run_log_blind_2026-11-19_submitted.txt, pipeline_commit_2026-11-19_submitted.txt (git 7ed21d4) |
| C — reproducibility re-run | 2026-11-19 19:34 | b9aad8a + figure-folder fix | re-run after the blind run was given its own figure folder (ledger entry 8) | outputs/ (current working files) |
| D — diagnostic re-run | 2026-11-19 19:40 | 03e5e8f | re-run after the eta sweep also started recording max abs(m) (a diagnostic field only) | outputs/ (current working files) |
| E — figure re-run | 2026-11-19 19:47 | 194418f | wrapped a clipped axis title in the map figure; no data change | outputs/ (current working files) |

All four runs: exit status 0, "all built-in checks passed", same command.
The logs and the commit id were written by the pipeline itself, not retyped.

## Results

Values below are from run D. Runs B to D give the same numbers except for the
second L3 feature, which is the one item affected by the disclosed change.

| Quantity | Blind value |
|---|---|
| L1 correction factor | 4.3627 |
| L1 corrected sheet density | 6.434e11 cm^-2 |
| L1 corrected mobility | 2.229e4 cm^2/Vs |
| L2 model | cone (gapless), E_g = 0 |
| L2 indices | 56; R_H changes sign between index 27 and 28 |
| L2 residual | r_cone = 0.0190 (400-point grid) |
| L3 decision | fail (clear), max abs(m) = 0.0338 > 0.030 |
| L3 local features | +0.0183 at (+1.5, +0.9); -0.0048 at (+2.1, -1.5) |
| L3 resolution | 1.76 probe pitches |
| L3 detection limit | 1.57e-5 |

## What run C changed relative to run B

Nothing in the analysis. A value-by-value comparison of
outputs/blind_results.json at 7ed21d4 against the current file finds no
difference except pipeline_commit and six figure-path strings in _meta, which
now name figures_blind/ instead of figures/. The regular results differ in
pipeline_commit only. The reader can check this with

    git diff 7ed21d4 -- outputs/blind_results.json outputs/results.json

Run C exists because the blind run used to write its plots into
outputs/figures, the same folder as the regular run, so whichever ran last
overwrote the other's figures. The fix gives the blind run
outputs/figures_blind (ledger entry 8).

## What run D changed relative to run C

Nothing in the analysis. The eta sweep now also stores max abs(m) for each
multiplier, so a reader can see whether the verdict would survive a different
regularisation strength; that adds five numbers and changes none. Comparing the
JSON with pipeline_commit, max_abs_map and the figure paths excluded finds zero
differences, for both the blind and the regular results. Reproduce the check
with

## One disclosed deviation from a strict freeze

Run A reported two features: +0.0183 at pixel (6,7) and -0.0109 at pixel (9,9).
Pixel (9,9) is a map corner -- the same artefact the demonstrator had flagged
for the regular data on 23 September. The interior-only rule in d41ce42 was
added after run A, in response to seeing a corner extremum again.

The rule is data-independent: it excludes boundary pixels for every dataset, it
uses no blind value to set a parameter, and it changes nothing except the
second feature, which becomes -0.0048 at pixel (2,8). The positive feature,
the resolution, the detection limit and the pass/fail verdict are identical
between runs A and B. Both runs are retained above so a reader can see exactly
what the rule did rather than take our word for it.

A strict freeze would have introduced the rule before the first look, so it is
disclosed here rather than presented as pre-registered.
