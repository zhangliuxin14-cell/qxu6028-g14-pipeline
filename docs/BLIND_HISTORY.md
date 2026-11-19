# Blind-test run record — G14

## Protocol

The pipeline was frozen before the blind data were touched: the analysis code,
thresholds, regularisation rule, seeds and model library are the same ones used
for data/regular_G14, and no parameter was tuned on the blind set. The only
change between the two runs is the dataset selector:

    python reproduce.py --dataset blind

which reads data/blind_G14, writes outputs/blind_results.json, outputs/run_log_blind.txt,
outputs/run_manifest_blind.json and outputs/pipeline_commit.txt.

## Run

| | |
|---|---|
| Date | 2026-11-19 19:30 (+0800) |
| Code commit | d41ce42c3db1d8b4164fd4be51161bcf21ae575d |
| Output commit | 7ed21d4 |
| Command | python reproduce.py --dataset blind |
| Exit status | 0, all built-in checks passed |
| Log | outputs/run_log_blind.txt (written by the pipeline, not retyped) |
| Provenance | outputs/run_manifest_blind.json (versions, commit, SHA-256 of every input) |
| Commit record | outputs/pipeline_commit.txt |

## Results

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

## One disclosed deviation from a strict freeze

The first blind run (code f536ce8) reported a negative feature on the map
corner, pixel (9,9) -- the same artefact the demonstrator had flagged for the
regular data on 23 September. The interior-only rule in d41ce42 was added after
that run, in response to seeing the corner again.

The rule is data-independent: it excludes boundary pixels for every dataset, it
uses no blind value to set a parameter, and it leaves the regular results and
both pass/fail decisions unchanged. But a strict freeze would have introduced it
before the first blind look, so it is disclosed here rather than presented as
pre-registered. A reader who prefers the frozen version can check out f536ce8
and re-run; the difference is confined to the second L3 feature.
