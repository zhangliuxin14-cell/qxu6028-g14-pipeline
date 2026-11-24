# L3 checkpoint note — G14

> **Correction added 2026-11-23 (Session 5).** The 2026-09-23 checkpoint fitted the plane on map indices but labelled the slopes "per pitch". The raw slopes are per map step (0.6 probe pitch). Corrected values are x = -5.514e-3, y = -8.432e-3 per probe pitch, magnitude 1.0075e-2 per pitch, and a wafer trend at the corner of 3.765e-2 (3.8% of the reference conductivity). The map, the features, the resolution, the detection limit and the FAIL verdict are unchanged. The 2026-09-23 note's 6.03e-3 "per pitch" and 4.5% corner values are retained here only as the historical reading; they are not the final numbers.

**Question.** Where is the wafer non-uniform? What can the probe resolve? Does the wafer meet the Session 3 specification (PASS when max|m| <= 0.030, i.e. 3.0% of the reference conductivity)?

## Method

- File checks: A has shape (128, 100); d has shape (3, 128); the largest row sum is 1.67e-16, below 1e-11.
- **Singular-value check (important finding).** A has rank 92, so the null space is **8-dimensional**: besides the constant mode (the probe blind spot) there are seven high-frequency modes that cannot be recovered. The guide mentions only the constant mode explicitly; the extra modes are checkerboard-like high-frequency structure (see the method figure).
- Reconstruction: first-difference matrix L (180 x 100); projector P = I - 11^T/100 removes the constant mode; Tikhonov regularisation with eta_0 = 1e-2 ||A||_2^2 / ||L||_2^2 = 1.331e-3; solve with lstsq and then enforce zero mean (|mean| = 6.9e-16).
- **Choice of eta (discrepancy principle).** At eta_0 the residual ||d - Am|| = 2.163e-4 = **12.80 times the repeat-noise norm** (1.690e-5), so eta_0 is a smooth reference reconstruction, not a noise-matched solution. The guide allows another value when the noise gives a clear reason. We take the largest eta whose residual still matches the repeat noise: **eta = 5.7e-2 eta_0** (residual = 1.00 times the noise norm). This lies inside the guide's scan range {0.01, 0.1, 1, 10, 100} x eta_0, at the L-curve corner marked in the method figure.
- **Trend separation and feature definition (key step).** The wafer contains both a **wafer-scale planar gradient** and **localised defects**. The extrema of a plane must lie on the map boundary, so a boundary extremum cannot be a defect. Following the guide's instruction to merge adjacent pixels into one feature rather than report every pixel as a defect, features are taken from the **plane-detrended map**, with a half-maximum merge rule.
- Resolution: inject a unit point source at the centre pixel and at the off-centre pixel (2,2), reconstruct with the same eta and solver, and use the positive lobe with sigma^2 = sum(w r^2)/(2 sum w), FWHM = 2.355 sigma.
- Detection limit: the three scans give a per-channel sigma_j; 500 noise vectors (seed 20260921, zero-mean normal with sigma_j) are reconstructed, and delta_95 is the 95th percentile of max|m_noise|.

## Result

- **Wafer-scale gradient (final, per probe pitch):** x = -5.514e-3, y = -8.432e-3, magnitude **1.0075e-2 per pitch**. The corner trend is **3.765e-2 (3.8%)** of the reference conductivity. After detrending, the largest residual is 0.0179.
- **Localised features (both interior):**

| Sign | Amplitude | Position (x, y) | Pixel | Merged pixels |
|---|---|---|---|---|
| positive | **+0.0179** | **(+0.3, +1.5)** | (7, 5) | 7 |
| negative | **-0.0142** | **(-0.9, -0.9)** | (3, 3) | 6 |

- **The dominant features are strictly interior** (neither coordinate is on the boundary +/-2.7). Taking the global extrema directly would return (-2.7,-2.7) and (+2.7,+2.7), which are the corners of the planar trend, not defects. That was the error in the earlier version.
- Resolution: **1.62 probe pitches at the centre and 1.80 off-centre**; the conservative reported value is **1.80 probe pitches** (about 3.0 pixels). The earlier note's "centre 1.80, off-centre smaller" was the reverse of the measured values.
- Detection limit delta_95 = **6.46e-5** at the chosen eta. At eta_0 it would be 2.36e-5, but that reconstruction has a residual 12.8 times the noise.
- Decision: a = max|m| = **0.0456** (including the wafer-scale trend, as the guide requires a = max|m_hat|); a - delta_95 = 0.0456 > 0.030, so **FAIL (clear)**. The decision envelope is 0.04550-0.04563.

## Physical interpretation

The wafer has a **planar conductivity gradient across the full wafer** (corner trend 3.8% of the reference value, gradient 1.01e-2 per probe pitch), plus two **localised defect dipoles**: a positive defect (+1.8%) at (x,y) = (+0.3,+1.5) and a negative defect (-1.4%) at (-0.9,-0.9), about 2.7 probe pitches apart.

- The planar gradient is a **systematic process problem** (a temperature or gas-flow gradient along x/y in the growth furnace); the directional distribution inside the furnace should be checked.
- The two localised defects are **local defects**, and each is below the 3.0% specification on its own. But the **full-map max|m| is set by the gradient**, and the specification constrains the whole wafer, so the overall verdict is FAIL.
- A resolution of 1.80 pitches means detail closer than about 1.8 pitches cannot be separated; the seven extra high-frequency null modes are an inherent blind spot of this probe geometry (in addition to the constant mode).
- This is consistent with L2: E_F in this material is very sensitive to doping, so a small growth gradient can produce a measurable wafer-scale non-uniformity.

*English version of the 2026-09-23 checkpoint note, with the Session 5 unit correction. The final numbers are the ones in outputs/results.json (regular G14).*
