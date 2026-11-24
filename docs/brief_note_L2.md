# L2 checkpoint note — G14

**Question.** Is the material gapless or does it have a hard gap, how large is the gap, and how does the Fermi level drift across the measurement series?

## Method

- 51 measurement indices, three repeats each (R_H, R_xx). The three repeats are averaged per index and the repeat standard deviation is retained.
- **Gate check.** The sign change of R_H locates the neutrality point: index 17 (+4.48e-13) to index 18 (-2.32e-14).
- R_H and R_xx are normalised independently, each by its own maximum absolute value. The sign of R_H is retained.
- Model library: an ideal cone g = c|E|; a hard gap with g = 0 for |E| <= E_g/2 and g = c(|E| - E_g/2) outside. Energy grid -2.5 to 2.5 eV (4000 points); E_F grid -8 to +9 k_BT (400 points); E_g/k_BT = 0.5 to 8.0 in steps of 0.25.
- Transport proxies for two carriers with equal mobility, e = mu = 1 (the common scale cancels because each axis is normalised separately):

  sigma_xx = n + p, so R_s = 1/(n + p); sigma_xy = B(p - n), so **R_H = (p - n)/(n + p)^2**.

  This form makes R_H pass through zero at neutrality and stay bounded. It satisfies the guide's orientation check (the model curve must cross the measured R_H sign change) and the handbook L2 gate (after normalisation R_H must still cross zero; in the guide's 4-9 kT wing window the ideal-cone wings obey |R_H| proportional to R_xx^2). The fitted model wings give |R_H|/R_xx^2 = 1.52 +/- 0.08, the same order as the measured 1.3-1.7.
- Fit: nearest point on the model curve in the two-dimensional normalised pair space, which assigns an E_F to every measured pair.
- Selection rule: choose a hard gap only if r_gap < 0.85 r_cone and E_g >= 1 k_BT; otherwise choose the cone (E_g = 0).
- Uncertainty: 200 bootstrap resamples (seed 20260921, each draw takes one of the three repeats at every index), reported as the 16th-84th percentile.

## Result

- **Model: cone (gapless), E_g = 0 k_BT.**
- r_cone = **0.01396**; the best hard-gap candidate is E_g = 0.50 k_BT with r_gap = **0.01362**, which is not below 0.85 r_cone = 0.01187. The 15% rule therefore fails and the cone is selected.
- **The residual is well below the noise, so the model has no systematic bias.** On the prescribed 400-point grid r_cone = 0.01396, but this number is not the model mismatch: the grid-convergence diagnostic gives r_cone = **0.00580**, so the true model-data distance is 0.43 times the repeat scatter of 0.01350. The model lies inside the measurement noise. The model and data have the same R_H sign at all 51 indices.
- Bootstrap: **2/200 (0.01)** resamples select a hard gap, so the model decision is confident; the median E_g is 0.00 k_BT with a 16th-84th interval of [0.00, 0.00] k_BT.
- Fermi trajectory: from **-0.068 eV** (index 0, p-type, R_H > 0) to **+0.146 eV** (index 49, n-type, R_H < 0), crossing neutrality between indices 17 and 18 and following the measurement order. The 51-index path has the correct length. Of the 50 steps, 41 rise, 5 are flat and 4 fall slightly; the largest fall is 0.0099 eV, the same size as its bootstrap 16th-84th band, so the path is monotonic within noise.
- Neutrality: R_H flips between index 17 (+4.48e-13) and index 18 (-2.32e-14). R_xx has its global maximum at the same place (5.775e-12 at index 18), an independent confirmation of the neutrality point.

## Residual comparison: a smaller or larger gap does not change the conclusion

The model figure (a) overlays three gap curves in the normalised pair space: E_g = 0.25 (below the candidate grid, for comparison only), 0.50 (the best candidate, the grid lower edge) and 0.75 k_BT (the next step). The three gap curves almost coincide with the cone; their mean separation is only 0.02-0.07 in coordinate units (about 1-6% of the range). The data are therefore very insensitive to the gap size near zero.

Model figure (b) plots the residual against gap size: r_cone = 0.01396, and the candidates worsen monotonically from **0.01362** at E_g = 0.50 k_BT to **0.12728** at E_g = 8 k_BT.

| E_g/k_BT | 0 (cone) | 0.25* | **0.50** | 0.75 | 1.00 | 2.00 | 8.00 |
|---|---|---|---|---|---|---|---|
| Residual r | 0.01396 | 0.01313 | **0.01362** | 0.01737 | 0.02246 | 0.06755 | 0.12728 |
| Improvement relative to cone | - | +6.0% | +2.5% | -24% | -61% | -384% | -811% |

*Below the guide's candidate grid (0.50-8.00 k_BT); shown only to demonstrate that a still smaller gap does not improve the fit. It does not enter the model selection.

- **The 15% threshold is 0.85 r_cone = 0.01187.** All 31 candidate gaps are above it; the closest is the grid lower edge at 0.50 k_BT, which improves the residual by only 2.5%. The rule therefore selects the cone.
- The key argument: **even when the search is extended below the grid to 0.25 k_BT, the improvement is only 6.0%**, far short of 15%. The cone is therefore not an artefact of the grid boundary; it is the conclusion of the data.
- The residual becomes worse as the gap grows and saturates above E_g of about 3 k_BT (near 0.127), because the hard gap flattens the curve so that it can no longer pass through the data points.

## Grid artefact: why the 0.25 k_BT residual looks lower than 0.50 k_BT

On the 400-point grid the ordering in the table is **non-monotonic** (0.25 gives 0.01313, 0.50 gives 0.01362 and the cone gives 0.01396), which is not physical: a gap shrinking continuously to zero should approach the cone continuously. The cause is **quantisation of the candidate E_F grid**.

The nearest-curve fit measures the distance to the discrete sample points of the model curve, and the curve is sampled only at 400 candidate E_F values. This adds a quantisation floor of about 0.0127 to every residual. The floor differs slightly between curves, so a curve whose 400 samples happen to lie a little closer to the data gets an artificial improvement. Refining the E_F grid removes it.

| Candidate E_F grid | r_cone | r(0.25) | r(0.50) | r(0.75) | Ordering |
|---|---|---|---|---|---|
| 400 points (guide, **used for the report**) | 0.01396 | 0.01313 | 0.01362 | 0.01737 | non-monotonic; cone in the middle |
| 6400 points (diagnostic only) | **0.00580** | 0.00634 | 0.00759 | 0.01072 | **monotonic; cone lowest** |

- After refinement the physical ordering returns: the cone is lowest and the residual rises with the gap. The low 0.25 value on the 400-point grid is therefore **grid luck**, not evidence for a sub-thermal gap. A point-by-point check supports this: relative to the cone, 0.25 improves 25 of the 51 points and worsens 26, essentially a coin toss rather than a systematic shape preference.
- Error budget: the 400-point quantisation is about **0.0127**, the repeat scatter is **0.01350**, and the true model-data distance is **0.00580**. The reported residual is therefore dominated by grid quantisation and measurement noise, not by model mismatch.
- The honest statement about gap resolution is therefore: for E_g below about 1 k_BT the residual differences (at most 6%) are both below the 15% rule and contaminated by quantisation, so they **cannot be used as evidence for a gap**; only the clear worsening for E_g above about 1 k_BT is robust. This is consistent with the conclusion that a sub-thermal gap cannot be distinguished from a gapless cone, now with a quantitative boundary.

## Device advice

The material behaves as a **gapless (Dirac-cone) semiconductor**. E_F can be tuned continuously from about -0.07 to +0.15 eV across neutrality, which suits **sensors and continuously tunable devices**; it is not suitable for a high-on/off-ratio logic switch, because a zero gap cannot be turned off. The zero gap uncertainty means only that the data cannot distinguish a sub-thermal gap from zero at the 1 k_BT resolution; a gap below 1 k_BT would not be resolved by this experiment.

*English version of the 2026-09-23 checkpoint note; numbers unchanged.*
