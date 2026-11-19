# AI error ledger — G14 (Jiale Zhang, Zijian Zhou)

Brief requirement: at least one specific, verifiable error in AI-generated work,
with how it was detected and corrected. A generic "the AI can be wrong" entry
scores nothing; the entries below are the eight that actually happened, in the
order they happened. Every number can be reproduced with the pipeline command
given in the entry, and every fix is guarded by a check in reproduce.py
_validate() so that the same mistake cannot silently return.

---

## Entry 1 — L1: the 10^4 mobility trap

| | |
|---|---|
| Date | 2026-09-21 (Session 2) |
| Stage | L1 forward model, src/l1.py |
| AI output | First draft of the mobility step followed an SI-units habit and "converted" the sheet density by 10^4 before dividing, i.e. mu = 1/(e n 10^4 rho). |
| Why it is wrong | The guide warns explicitly against an extra 10^4. Dimensional analysis: n is in cm^-2 and rho in ohm/sq, so e n rho has units C ohm cm^-2 = (cm^2 / (V s))^-1 and 1/(e n rho) is already in cm^2/Vs. Nothing has to be converted. |
| Detection | (i) the guide sentence; (ii) dimensional check; (iii) the reference ratios C(0) = 1.00, C(0.10) = 2.60, C(0.20) = 5.10 still passed with the wrong factor, so the reference checks alone would not have caught it -- it was caught by the units, not by the tests. |
| Correction | mu_corr = 1/(e n_F rho) with the derivation in a code comment; the identity mu_corr / mu_band = C(E_F,op) was made an assertion, which a stray 10^4 would break. |

## Entry 2 — L3: the null space is 8-dimensional, not 1

| | |
|---|---|
| Date | 2026-09-21 (Session 2) |
| Stage | L3 inverse problem, src/l3.py |
| AI output | First implementation repeated the guide's wording that "the matrix cannot recover a constant offset", implying the only unrecoverable mode is the constant vector. |
| Detection | Following brief 5.3 step 1, the singular values of A (128 x 100) were printed: five of them are below 1e-15. A rank computation then gave rank(A) = 92, so the null space has dimension 8: the constant mode plus seven high-spatial-frequency, checkerboard-like modes. |
| Correction | The singular-value spectrum and a null-space orthogonality test (|<m_hat, n_k>| < 7e-4 for all eight basis vectors) were added to the pipeline and to the method figure. The report states the eight-dimensional blind spot instead of repeating the guide. |
| Why it matters | The unrecoverable modes are part of the resolution answer: the probe geometry (64 positions x 2 orientations) cannot see those seven patterns at all, no matter how small eta is. |

## Entry 3 — L2: the transport proxies had the wrong topology (rms 0.4470)

| | |
|---|---|
| Date | 2026-09-23 (Session 3) |
| Stage | L2 nearest-curve fit, src/l2.py: rh_rs_from_np |
| AI output | R_H = 1/(n - p) and R_s = 1/(n + p) were used as "raw Hall and sheet-resistance proxies (e = mu = 1, the scale cancels in the normalisation)". |
| Symptom | L2_model_fit.png showed the model curve completely separated from the data, rms = 0.4470, with every data point on one side of the curve. |
| Why it is wrong | 1/(n - p) diverges at the neutrality point, so the model's R_H range was only [-0.316, +1.000] against the data's [-1.000, +0.985], and the model R_xx had its minimum where the data have their maximum (0.134 vs 1.000). The topology is inverted. The handbook gate (p.4) requires the normalised R_H to pass through zero at neutrality and the wings to obey |R_H| proportional to R_s^2; a divergent form cannot satisfy it. |
| Detection | (i) the handbook gate; (ii) the guide's "important orientation check" on p.7; (iii) a scan over R_H = (p - n)/(n + p)^a and R_s = 1/(n + p)^b with a in {1, 1.5, 2, 2.5, 3} and b in {0.5, 1, 1.5, 2} -- twenty forms scored against the data. |
| Correction | The standard two-carrier result for equal mobilities, R_s = 1/(n + p) and R_H = (p - n)/(n + p)^2, is the unique member of the scanned family that both minimises the residual and puts the R_xx maximum at the R_H zero. r_cone fell from 0.4470 to 0.01396. |
| Side effect | The Fermi-level path changed sign, from +0.067 -> -0.149 eV (wrong) to -0.068 -> +0.146 eV (right), because 1/(n - p) carries an extra minus sign relative to the standard convention. |
| Guard | Three checks in _validate(): the model curve must cross R_H = 0, R_s must peak there, and the relative standard deviation of |R_H|/R_s^2 over the outer indices must stay below 0.15. Re-introducing 1/(n - p) fails all three. |

## Entry 4 — L2: "the residual has reached the noise floor" was a numerical coincidence

| | |
|---|---|
| Date | 2026-09-23 (Session 3) |
| Stage | L2 interpretation and brief note |
| AI output | "r_cone = 0.01396, repeat scatter 0.01350, ratio 1.03, so the residual is pure noise and the model has no systematic bias." |
| Detection | A group member asked why the best candidate inside the grid, E_g = 0.50 kT, had a larger residual (0.01362) than a value outside it, 0.25 kT (0.01313), when a shrinking gap should return continuously to the cone. Refining the candidate E_F grid to 1600 and 6400 points made the ordering monotonic again. |
| What was actually true | The 400-point grid quantises the curve and adds a floor of about 0.0127 to every residual, comparable to the repeat scatter of 0.01350. The converged model-data distance is 0.00580, i.e. 0.43 of the noise. So the ratio 1.03 was a coincidence between the grid floor and the noise, not evidence that the model fits perfectly. |
| Correction | The brief note now distinguishes the reported 400-point residual from the converged value, the convergence table is stored in _meta.L2.grid_convergence and plotted as a diagnostic panel, and the report says explicitly that E_g below about 1 kT cannot be resolved because the residual differences there are smaller than the 15% rule and contaminated by quantisation. |
| Guard | The 400-point grid is kept because the assessment specifies it; the convergence table is diagnostic only and cannot replace the reported value. |

## Entry 5 — L3: the wafer-scale tilt was reported as a defect (corner artefact)

| | |
|---|---|
| Date | 2026-09-23 (Session 3) |
| Stage | L3 feature extraction, src/l3.py |
| Symptom | The demonstrator pointed out that the optimum solution is not at an end value. The reported feature coordinates were (+2.7, +2.7) and (-2.7, -2.7), exactly the two endpoints of np.linspace(-2.7, 2.7, 10): both extrema sat on the map corners. |
| AI output | The first _merge_features took the global max and min of the map as "the largest positive and negative extrema", which is what the guide's wording appears to ask for. |
| Why it is wrong | A planar trend has its extrema on the boundary by construction, so a boundary extremum is the trend, not a defect. Fitting a pure plane leaves a residual 3005 times the noise, so the data contain both a wafer-scale tilt and local structure and the two must be separated. |
| Detection | (i) the corner coordinates themselves; (ii) matched filtering -- injecting a single-pixel source at each pixel and looking at the residual improvement -- pointed to interior pixels (7,5), (6,5), (7,6), (6,6), (3,4), (3,3), none on the boundary; (iii) across all 29 released datasets, the dominant feature after detrending was interior in 29 of 29 cases, which a random process would not produce. |
| Correction | A least-squares plane is fitted and subtracted first (_ramp_detrend), features are taken from the detrended map with a half-maximum merge rule, and the tilt is reported separately as the wafer-scale gradient (6.03e-3 per pitch). G14 features became +0.0179 at (+0.3, +1.5) and -0.0142 at (-0.9, -0.9). |
| Same session | The check also exposed eta_0 over-regularisation: at eta_0 the residual is 12.80 times the repeat-noise norm, i.e. the reconstruction does not fit the data. The discrepancy principle gives eta = 5.7e-2 eta_0, the largest value whose residual still matches the noise (1.00 x). Resolution 1.44 -> 1.80 pitches and detection limit 2.36e-5 -> 6.46e-5 follow; the FAIL (clear) decision does not change. |
| Guard | Five checks: features must come from the detrended map, the dominant one must be interior, its magnitude must be below the raw map extremum, eta must lie inside the scanned range, and the scanned range must bracket the noise level. |

## Entry 6 — reproduce.py: --dataset blind crashed on a missing template (2026-11-19)

| | |
|---|---|
| Date | 2026-11-19 (Session 4, repository consolidation) |
| Stage | reproduce.py, results template handling |
| AI output | The earlier reproduce.py rebound common.RESULTS_TEMPLATE to <blind folder>/results_template.json for the blind run. |
| Symptom | python reproduce.py --blind died with FileNotFoundError: data/blind_G14/results_template.json, before writing any result. The blind pack ships data and a manifest, not a results template. |
| Detection | Running the blind command on the clean copy; the traceback names the missing file. |
| Correction | The template is a property of the output schema, not of the dataset, so src/common.py now points at data/results_template.json at the repository root and both runs share it. Verified by running both datasets end to end in one session. |
| Guard | The blind run is part of the acceptance procedure, not an afterthought: reproduce.py --dataset blind must write blind_results.json and pass all checks. |

## Entry 7 — reproduce.py: the blind run silently recomputed the regular data (2026-11-19)

| | |
|---|---|
| Date | 2026-11-19 (Session 4) |
| Stage | src/l1.py, src/l2.py, src/l3.py data binding |
| AI output | The lab modules used "from .common import DATA_DIR", which copies the Path object at import time, while reproduce.py rebound common.DATA_DIR at run time to point at the blind folder. |
| Symptom | None -- and that is the point. python reproduce.py --blind ran to completion, reported "all checks passed" and wrote outputs/blind_results.json. The numbers in it were the regular numbers, because the modules were still reading data/regular_G14 and the checks were validating the regular values they had just computed. |
| Detection | Comparing the blind output with the regular output: identical L1 values to the last digit, which is impossible for an independent dataset. |
| Correction | The modules import the module (from . import common) and read common.DATA_DIR inside the functions, so the run-time rebinding is seen. reproduce.py also records dataset_set in the results and _validate checks it, so a regular result can no longer be passed off as a blind one. |
| Why it is in this ledger | This is the most dangerous class of AI error we met: a silent fallback that produces a plausible, green-ticking, wrong artefact. The fix is not just the import -- it is making the wrong state detectable, so the same mistake cannot pass review again. |

## Entry 8 — the blind run overwrote the regular figures (2026-11-19)

| | |
|---|---|
| Date | 2026-11-19 (Session 4, after the consolidation) |
| Stage | src/l1.py, src/l2.py, src/l3.py figure paths; src/common.py FIG_DIR |
| AI output | The lab modules used "from .common import FIG_DIR" and wrote to outputs/figures. reproduce.run() rebound DATA_DIR for the blind run but never rebound FIG_DIR. |
| Symptom | outputs/figures held the blind plots while outputs/results.json described the regular data. The JSON was right; the pictures next to it were not. |
| Detection | Opening the figures to write this report. Panel (a) of L2_model_fit printed r_cone = 0.0190 and "15% rule needs < 0.0162", while results.json said r_cone = 0.013962; L3_method printed "chosen: 0.0147x eta0" where the JSON said 0.05698. Two plots disagreed with the file they were supposed to illustrate. |
| Why it is the same bug as entry 7 | Same mechanism one level down: a module-level constant bound at import, rebound at run time, and no check that the artefact came from the run that produced the JSON. Entry 7 was found by comparing two datasets; this one survived that comparison because only the figures collided, not the numbers. |
| Correction | common.figure_path(name) resolves FIG_DIR at call time; run() sets common.FIG_DIR to outputs/figures or outputs/figures_blind; the blind figures are committed separately; and _validate now fails if any recorded figure path is not under the folder of the dataset that was run. |
| Evidence that no number moved | Re-running both datasets after the fix changes pipeline_commit and six figure-path strings in the blind _meta, and pipeline_commit only in the regular results. git diff 7ed21d4 -- outputs/ shows exactly that. The reported physics is untouched; the provenance of the pictures is now correct. |

---

## What this ledger is not

It is not a list of every AI mistake; it is the list of mistakes that changed a
number in the submission, plus the two that changed an artefact's provenance.
Typos and formatting errors are excluded because they do not test anything.
Each entry is written so that a reader can re-run the check that caught it.
