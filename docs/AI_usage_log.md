# AI usage log — G14

Brief requirement: a log of every substantive use of generative AI, with the
tool, the purpose and the scope of what the AI contributed. Entries are listed
in the order the work happened. Supporting documents: docs/AI_error_ledger.md
for the specific errors, docs/AUTHORSHIP.md for how AI output maps onto the
commit history.

---

## 1. Session 2 — L1 pipeline and repository skeleton

| | |
|---|---|
| Date | 2026-09-21 |
| Member | Jiale Zhang |
| Tool | Visual Studio Code with a chat agent running a DeepSeek model (API key supplied by a coursemate; the key belonged to that coursemate, not to the group) |
| Purpose | Read the handbook and the practical methods guide, then build the L1 analysis and the first version of the repository |
| What was asked | Implement the two carrier counts (band-edge integral from E = 0 and Fermi-referenced integral from E = E_F), the correction factor, the mobility at the operating point, the sweep figure, and assertion checks against the guide's reference values 1.00 / 2.60 / 5.10. Set up src/ with a shared constants module and a reproduce.py entry point. |
| What the AI produced | src/common.py, src/l1.py, the L1 figure, the checkpoint note and the repository layout, in one pass |
| What we checked before accepting | The three reference ratios recomputed by hand; the units of the mobility step (the AI's first version inserted a spurious 10^4, entry 1 of the ledger); that the operating point was evaluated at the exact E_F,op rather than the nearest table row; that the figure axis labels carried units |
| What we rejected | The 10^4 conversion, and an early version that integrated from E_F over only the tabulated rows -- the table is sparse near the band edge, so the integral had to be done on a fine grid, not on the CSV |
| Recorded in | commit e18aa4b (initial pipeline), commit c19de7c (L1 checkpoint package) |

## 2. Session 3 — L2 and L3 (Zijian Zhou)

| | |
|---|---|
| Date | 2026-09-23 |
| Member | Zijian Zhou |
| Tool | Visual Studio Code with a chat agent running a DeepSeek model on his own API key |
| Purpose | Build the L2 zero-dimensional inverse problem (model library, nearest-curve fit, 15% rule, bootstrap, Fermi path) and the L3 regularised 2-D reconstruction (SVD, Tikhonov, eta scan, resolution, detection limit, pass/fail) |
| What was asked | Read the L2/L3 sections of the guide literally, implement each required check, and diagnose two visible failures: the L2 model curve sitting away from the data, and the L3 feature coordinates landing on the map corners |
| What the AI produced | src/l2.py and src/l3.py, the six figures, brief notes for both labs, and the diagnosis of both failures (ledger entries 3 and 5) |
| What we checked before accepting | The handbook L2 gate (R_H crosses zero at neutrality, R_s peaks there, wings scale as R_s^2) evaluated numerically on the model curves; the 20-form (a, b) scan re-run independently; the residual recomputed from the raw CSV without the pipeline; the null-space dimension recomputed by SVD; the eta scan plotted against the noise norm; the pass/fail threshold read back from the brief |
| What we rejected | The first transport proxies R_H = 1/(n - p), R_s = 1/(n + p), which are topologically wrong (rms 0.4470); the global-extremum feature extraction; the claim that the residual had "reached the noise floor" at 400 points |
| Recorded in | commit 93102f0 (import of the L2/L3 working copy into the shared repository, message names the author), ledger entries 3, 4, 5 |

## 3. Session 4 — repository consolidation, verification and writing

| | |
|---|---|
| Date | 2026-11-19 |
| Member | Jiale Zhang |
| Tool | DeepSeek Harness coding agent (DeepSeek model, agent mode in a local session) |
| Purpose | Turn the working copy into a repository that a marker can run: fix the two data-path bugs, add the dataset selector, run log, run manifest and --check mode, regenerate every output, write the authoring records, and draft the report |
| What the AI produced | The reproduce.py CLI, the DATA_DIR and results-template fixes, the run manifest and log capture, the checks added to _validate(), the English README, this log and the error ledger, docs/AUTHORSHIP.md, docs/BLIND_HISTORY.md, docs/CHECKPOINTS.md, tools/contribution_report.py, the report draft and the figures for it |
| What we checked before accepting | Both datasets run end to end and exit 0; --check exits 0; every number in the report traced back to a key in results.json; the blind output compared with the regular output (this comparison is what caught ledger entry 7); a clean clone of the repository run from scratch; the word count of the report |
| What we rejected | The first blind run's output, which was a silent copy of the regular numbers; a first attempt at splitting the run log that crashed on Windows console encoding; an early version of the manifest that was overwritten by the blind run |
| Recorded in | commits fa4d1d0, 2204f04, 9f10e43, 50ff23e, f536ce8, 8eb5923, ledger entries 6 and 7 |

## 4. Session 5 — independent verification, unit correction and the journal-format report

| | |
|---|---|
| Date | 2026-11-23 |
| Member | Jiale Zhang |
| Tool | DeepSeek Harness coding agent (DeepSeek model, local session) |
| Purpose | Re-derive L1, L2 and L3 from the raw data without reusing src/, find why one reported L3 number did not survive that check, rebuild the report in the course journal template, and rewrite the internal explainer for a reader with no AI-for-science background |
| What the AI produced | tools/verify_independent.py and docs/VERIFICATION.md; the L3 gradient-unit fix and its guards; the rho-class report and its bibliography; the rewritten explainer; refreshed working-record tables |
| What we checked before accepting | Every re-derived number compared with outputs/results.json; both datasets rerun after the fix and diffed field by field; the unit conversion repeated by hand (0.003308 / 0.6 = 0.005514); the report compiled with no errors and no overfull boxes; every figure cited before it appears |
| What we rejected | A first suggestion to present the 400-point gap fit as a genuine improvement (it is a grid artefact, ledger entry 4); the minted code-listing package, which needs pygmentize that this TeX installation lacks, so the template is used without it |
| Recorded in | commits 43185d8 (unit fix), 78cd039 (regenerated outputs); report and explainer are submitted outside the repository |

## 5. What was not AI-generated

The group chose the questions to ask, decided which model forms were physically
acceptable, and checked every number that appears in the report against the JSON
and the code. This log and the contribution statement were drafted by the AI
from the group's records and then read line by line by Jiale Zhang; they are not
claimed as hand-written. The AI never had access to the blind results at the time
the analysis choices for L1-L3 were frozen, and the blind run uses the identical
code path.

## 6. Declaration

No AI output was submitted without a check recorded here or in the error
ledger. Where an AI output was wrong, the error, the detection and the
correction are in docs/AI_error_ledger.md.
