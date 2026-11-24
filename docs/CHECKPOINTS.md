# Checkpoint record — G14

The module runs as three virtual-lab sessions with a checkpoint after each. This
file records what was produced at each one and what was checked, so the
checkpoints can be compared with the commit history.

## Session 1 — 2026-09-20: setup

Read the brief, the handbook and the practical methods guide. Split the work:
Jiale took L1 and the pipeline, Zijian took L2 and L3. No data were modified;
data/regular_G14 is a byte-for-byte copy of the release and
outputs/run_manifest.json records its SHA-256 hashes.

## Session 2 — 2026-09-21: L1 checkpoint

| | |
|---|---|
| Deliverable | checkpoints/G14_L1_Checkpoint.zip (also unpacked in checkpoints/L1/) |
| Commit | c19de7c (the commit that added the package) |
| Hash recorded in the package | 39218b27..., written to checkpoints/L1/commit_hash.txt so the checkpoint can be traced to a commit |
| Contents | brief note, L1 figure, results.json (L1 block), commit hash |

Checks performed before submitting the checkpoint:

- reference ratios n_band/n_Fermi = 1.00 at E_F = 0, 2.60 at 0.10 eV, 5.10 at 0.20 eV;
- the operating point evaluated at the exact E_F,op rather than the nearest row of L1_data.csv;
- dimensional analysis of the mobility step (the 10^4 trap, ledger entry 1);
- the sweep figure axis labels and units;
- that reproduce.py regenerates the checkpoint numbers from the CSV.

## Session 3 — 2026-09-23: L2 and L3 checkpoint

| | |
|---|---|
| Deliverable | brief notes for L2 and L3, the six figures, results.json |
| Recorded in | L1: docs/run_artifacts/check_out_2026-09-21.txt. L2/L3: docs/brief_note_L2.md, docs/brief_note_L3.md, outputs/figures. The shared import commit 93102f0 (2026-11-19) brought Zijian Zhou's working copy into this repository; its date is not the 2026-09-23 checkpoint date. |

Checks performed:

- L2 handbook gate: the model R_H crosses zero at neutrality, R_s peaks there, and the wings scale as R_s^2;
- the 20-form (a, b) scan for the transport proxies, re-run independently of the AI;
- L2 residual recomputed from the raw CSV, outside the pipeline;
- L3 singular values: rank(A) = 92 of 100, null space 8-dimensional;
- L3 eta scan against the repeat-noise norm, discrepancy principle;
- L3 features taken from the detrended map, so that a boundary extremum cannot be reported as a defect (ledger entry 5);
- the pass/fail threshold read back from the brief: max abs(m) <= 0.030.

The group also made a live blind-test attempt during the Session 3 live session. The data and method used at the time were judged unreliable, so the attempt was discarded and no result from it was adopted. It is not used in any number in this repository and no artifact from it is presented as the submitted blind result. The adopted blind test is the frozen-pipeline run on the released blind_G14 pack recorded in docs/BLIND_HISTORY.md (2026-11-19 to 2026-11-23).

## Session 4 — 2026-11-19: consolidation and adopted blind test

| | |
|---|---|
| Commits | fa4d1d0, 2204f04, 9f10e43, 50ff23e, f536ce8, 8eb5923, d41ce42, 7ed21d4 |
| Deliverables | working reproduce.py with --check and --dataset; regenerated outputs; the blind run; this record |

Checks performed:

- both datasets run end to end from a clean copy and exit 0;
- reproduce.py --check exits 0;
- the blind output compared with the regular output, which is how ledger entry 7 was found;
- every reported result traceable to a key in results.json or blind_results.json;
- a fresh clone of the repository run from scratch;
- the report word count and the section limits.

## Session 5 - 2026-11-23: independent verification and the unit audit

| | |
|---|---|
| Commits | 43185d8 (gradient unit), 78cd039 (regenerated outputs), the commit that adds tools/verify_independent.py and docs/VERIFICATION.md |
| Deliverables | an independent re-derivation for both datasets, the corrected gradient fields, this record |

Checks performed:

- every L1, L2 and L3 number re-derived without importing src/ (agreement: L1 to 1e-5, L2 replica to 1e-8, L3 to machine precision);
- the September working copy compared with the re-derivation (L1 correct; L2 decision correct; L3 reconstruction exact but resolution reported in map cells and eta left at eta0);
- the L3 gradient refitted on map indices and converted to probe pitches, which is how the unit error was found;
- both datasets regenerated after the fix; the JSON diff contains only the gradient fields and pipeline_commit.

## Evidence map

| Evidence | Where |
|---|---|
| Session 2 checkpoint | checkpoints/L1/, checkpoints/G14_L1_Checkpoint.zip |
| Session 3 analysis | docs/brief_note_L2.md, docs/brief_note_L3.md, outputs/figures |
| Session 4 consolidation | outputs/run_log.txt, outputs/run_log_blind.txt, outputs/run_manifest*.json |
| Blind run | docs/BLIND_HISTORY.md, outputs/pipeline_commit.txt |
| AI use | docs/AI_usage_log.md, docs/AI_error_ledger.md |
| Independent re-derivation | tools/verify_independent.py, docs/VERIFICATION.md |
