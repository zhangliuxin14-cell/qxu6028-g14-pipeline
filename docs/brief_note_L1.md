# L1 checkpoint note — G14

**Question.** The data sheet uses the textbook band-edge count (integration from E = 0). At the operating point, how much does this convention misstate the carrier density, the mobility and the sensor sensitivity?

## Method

- Linear density of states g(E) = cE with c = 0.038341 cm^-2 eV^-2 from L1_params.json; T = 300 K.
- Band-edge count n_band: integrate g(E) f(E) from E = 0 to 2.5 eV.
- Fermi-referenced count n_Fermi: integrate g(E) f(E) from E = E_F to 2.5 eV (20001 points, np.trapezoid).
- Correction factor C(E_F) = n_band / n_Fermi.
- Operating point E_F,op = 0.1115 eV (the exact value, not the nearest CSV row); rho = 437.93 ohm/sq.
- Corrected mobility mu = 1 / (e n_F rho). The units follow directly from n in cm^-2 and rho in ohm/sq and give cm^2 V^-1 s^-1; no factor of 10^4 is applied.

## Reference checks (all pass)

| E_F (eV) | n_band / n_Fermi | Expected |
|---|---|---|
| 0.000 | 1.000 | 1.00 |
| 0.073 | 2.005 | about 2.00 |
| 0.100 | 2.599 | about 2.60 |
| 0.200 | 5.104 | about 5.10 |

The closed form agrees with the numerical integral to 2.7e-7 relative, and the sweep is monotonic.

## Result

- Correction factor C(E_F,op) = **2.867**
- Corrected carrier density n_F(E_F,op) = **3.727e11 cm^-2**
- Corrected mobility mu_corr = **3.824e4 cm^2 V^-1 s^-1** (uncorrected mu_band = 1.334e4 cm^2 V^-1 s^-1)
- C = 2 at E_F = 0.0725 eV; C = 4 at E_F = 0.157 eV

## Physical interpretation and sensor advice

The band-edge count adds the filled states between E = 0 and E_F that the Fermi function has already occupied. Because n_F itself grows quickly at low doping, C is not simply a constant offset; it rises monotonically with E_F. At E_F -> 0+ the two integrals coincide and C -> 1. It does not diverge there. In this linear-DoS model C continues to grow at high E_F, roughly in proportion to E_F once E_F is much larger than kT.

**Quantitative advice.** At the operating point the band-edge count gives n_band = 2.867 n_F. A mobility inferred as 1 / (e n_band rho) is therefore **2.867 times too low** (1.334e4 instead of 3.824e4 cm^2 V^-1 s^-1). Conversely, if a sensor signal is taken to be proportional to n_band, it is **overestimated by 2.87**; the Fermi-referenced count is the correct one. Calibrating near E_F = 0.11 eV without the correction leaves an error of about 187%.

*This English version replaces the Chinese checkpoint note. The numbers are unchanged; the direction of the mobility/sensitivity error and the C -> 1 limit were corrected during translation (the earlier Chinese note had them reversed).*
