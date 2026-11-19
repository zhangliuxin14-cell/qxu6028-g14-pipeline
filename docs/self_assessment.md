# Critical self-assessment — G14

Two weaknesses limit this submission.

First, our reported L2 residual is dominated by the assessment's 400-point
Fermi-level grid, not by model mismatch. The grid adds a quantisation floor
near 0.0127, close to the repeat scatter of 0.0135, so r_cone = 0.0140
overstates how badly a cone fits; refining to 6400 points gives 0.0058, about
0.43 of the noise, and only there does the ordering of candidate gaps become
monotonic. We keep the 400-point value because the assessment specifies that
grid, label it grid-limited, and publish the convergence table as a diagnostic.
The proper fix is to solve along each model curve instead of sampling 400
candidate Fermi levels.

Second, we chose eta by the discrepancy principle (5.7e-2 eta_0) rather than the
guide's default, which is defensible but not optimal: it trusts a noise norm
estimated from only three repeats. Generalised cross-validation over an
estimated noise covariance would use the data better, at the cost of a longer
method section.

A smaller limitation: we measure the eight-dimensional null space but do not
explain each mode by probe geometry.
