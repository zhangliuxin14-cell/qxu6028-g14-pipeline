# Independent re-derivation and cross-check

This note records a third check on the three labs: a re-implementation of every
calculation that does not import `src/`, written to a different numerical plan,
and compared against the committed results. It also compares the September
working copy kept in `L1_L2_L3/` with the re-derivation, so the original team
answers can be judged separately from the later pipeline.

The script is `tools/verify_independent.py`. It reads only the released data
files and the committed `outputs/*.json`; it shares no code with the pipeline.

## How to run it

    python tools/verify_independent.py --dataset regular
    python tools/verify_independent.py --dataset regular --student-dir ../L1_L2_L3
    python tools/verify_independent.py --dataset blind   --student-dir ../L1_L2_L3

`--student-dir` is optional; without it the script only re-derives the pipeline
numbers. The path above assumes the September working copy sits next to the
repository.

## L1: the counting convention

| quantity | independent | pipeline | relative difference |
|---|---|---|---|
| C(E_F,op) | 2.867239936353 | 2.867211749569 | 9.8e-6 |
| n_F / cm^-2 | 3.726616e11 | 3.726652e11 | 9.7e-6 |
| mobility / cm^2 V^-1 s^-1 | 38244.753699 | 38244.384755 | 9.7e-6 |
| n_band against the CSV column (worst of 12 rows) | - | - | 7.6e-7 |
| closed form against the grid n_F | - | - | 9.4e-6 |

The verifier integrates on a 250001-point grid instead of the pipeline's 20001,
so the difference is the trapezoid discretisation and shrinks with the grid; the
blind dataset agrees to 4.0e-5 for the same reason. Both counting conventions,
the exact operating-point evaluation and the mobility conversion are therefore
implemented correctly, and C = 2.867 is not an artefact of one code path.

## L2: cone against hard gap

Two runs of the same verifier are reported. The *replica* uses the pipeline's
discretisation (400 E_F points, 4000-point energy grid); the *converged* run
keeps the prescribed 400 E_F points but integrates the Fermi window on 20001
energy points.

Regular dataset, replica:

| curve | independent | pipeline |
|---|---|---|
| cone | 0.013962397 | 0.013962399 |
| gap 0.25 kT (below grid, comparison only) | 0.013129893 | 0.013129891 |
| gap 0.50 kT | 0.013618530 | 0.013618525 |
| gap 0.75 kT | 0.017365438 | 0.017365430 |

Agreement is at the 1e-8 level, and the E_F trajectory matches to 4.4e-9 eV at
every one of the 51 indices. The independent curve also confirms the handbook
gate: over the probed window (4-9 kT) a log-log fit of |R_H| against R_s gives
a slope of 1.973, i.e. |R_H| ~ R_s^2 to 2%.

Converged energy grid, regular dataset: cone 0.012749476, gaps 0.013836988
(0.25 kT), 0.015880982 (0.50 kT), 0.020185371 (0.75 kT). The cone is now the
best curve outright, so refining the integral strengthens the choice rather
than reversing it. With the 15% rule a gap would need r < 0.85 x 0.012749476 =
0.010837, which no candidate approaches.

Blind dataset, replica: cone 0.019001636 against the pipeline's 0.019001639;
gaps 0.017981691 (0.25 kT), 0.017763067 (0.50 kT), 0.018498526 (0.75 kT). The
rule needs r < 0.016151; the best gap, 0.017763, is 10% better than the cone but
not 15% better, so the cone stays. The same verdict comes out of the independent
code.

What this means: the reported 0.0140 is the residual on the grid the assessment
prescribes, and it is dominated by the 1.1 meV spacing of those 400 E_F points,
not by model mismatch. The 6400-point diagnostic (0.0058) and the convergence
table in `_meta.L2.grid_convergence` quantify that floor, and the self-assessment
in the report says so.

## L3: reconstruction, resolution and the verdict

Regular dataset:

| quantity | independent | pipeline |
|---|---|---|
| rank / null directions | 92 / 8 | 92 / 8 |
| smallest singular value | 5.20e-17 | 5.20e-17 |
| eta0 | 1.331e-3 | 1.331e-3 |
| eta chosen | 7.584160e-5 (0.05698 eta0) | 7.584160e-5 |
| max abs(m) | 0.045561975 | 0.045561975 |
| map, maximum difference | 1.6e-14 | - |
| resolution (FWHM, probe pitches) | 1.8025 | 1.8025 |
| delta_95 | 6.456373e-5 | 6.456373e-5 |
| gradient per probe pitch | (-5.514e-3, -8.432e-3) | same fields |
| plane value at the (9,9) corner | 0.037654 (3.77%) | 3.77% |

Blind dataset: eta 1.959368e-5 (0.01472 eta0), max abs(m) 0.033795878 against
0.033795878 (difference 3.8e-14), resolution 1.7635 pitches, delta_95
1.565916e-5, corner trend 0.028668 (2.87%) - all equal to the committed values.

The Tikhonov system is solved directly here (the pipeline uses a least-squares
solve), the eta scan is re-implemented, and the noise draws are regenerated from
the fixed seed. Exact agreement to machine precision means the numbers depend on
the mathematics, not on one library call.

## The September working copy

| item | September value | re-derivation | verdict |
|---|---|---|---|
| L1 C | 2.867211749569 | 2.867239936353 | correct, 2.8e-5 from integration grid |
| L1 n_F, mobility | 3.726652e11, 38244.384755 | 3.726616e11, 38244.753699 | correct, 1e-5 |
| L2 model | cone, E_g = 0, 51 indices | same | correct decision |
| L3 map, regular | - | eta0 reconstruction | identical to 1.4e-15 |
| L3 map, blind | - | eta0 reconstruction | identical to 1.9e-15 |
| L3 resolution | 2.407158 | 1.4443 pitches | map-cell units, not pitches |
| L3 detection limit | 2.349e-5 (regular), 3.019e-6 (blind) | at eta0 | consistent with eta0 |

Two things in the September work need naming, and neither is a physics error.
First, the reported resolution 2.407 is in map cells; the probe pitch is 0.6 of
a cell, so the answer in the units the brief asks for is 1.444 pitches (later
1.80 with the discrepancy-principle eta). Second, the September L3 used
eta = eta0, the guide's default, rather than the discrepancy-principle eta;
that moves max abs(m) from 0.04507 to 0.04556, the resolution from 1.44 to 1.80
pitches and delta_95 from 2.36e-5 to 6.46e-5, while the fail verdict is
unchanged. The blind working copy shows the same pattern (0.03389 against
0.03380).

Three documentation defects are also visible in that copy: the L2 results file
still carries the placeholder `REPLACE_WITH_GIT_COMMIT_HASH`; the L1 brief note
has a sentence about C tending to infinity that is backwards; and the L2 note
quotes a different bootstrap seed and hard-gap fraction (20260923, 0%) from the
committed result (20260921, 1%). None of these changes a number; they are the
kind of slip the ledger entries exist to catch.

## What this check does not cover

- It cannot replace the hidden reference values: it shows that the reported
  numbers follow from the released data under the documented model, not that the
  model is the one the markers use.
- The L2 residual is discretisation-limited on the prescribed grid; the
  converged value 0.0127 is closer to the quantisation floor than the reported
  0.0140, and both are quoted.
- The L3 detection limit covers repeat noise only. The systematic uncertainty is
  the eta dependence shown in the report's Figure 6(a), and it is larger.

All numbers in this note are printed by the script; rerun it rather than copy
them.
