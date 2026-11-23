"""Independent re-derivation of L1-L3 from the released data.

This script deliberately does not import src/. Every formula is re-implemented
here, and the numerics differ where the physics allows: a much finer energy
grid for the Fermi integrals, a brute-force nearest-curve search built from
cumulative sums, and a direct linear solve for the Tikhonov system. The point
is to catch a coding slip in the pipeline, not to re-use it.

Usage:
    python tools/verify_independent.py
    python tools/verify_independent.py --student-dir ../L1_L2_L3

The optional student directory is the team's September working copy. When it is
present the script also prints what the original submission got right and wrong
relative to this re-derivation.
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
KB = 8.617333262e-5          # eV per K
QE = 1.602176634e-19         # C
NA = 3.816e15                # cm^-2 eV^-1 (guide, Chapter 3)


def load(dataset):
    d = ROOT / "data" / ("regular_G14" if dataset == "regular" else "blind_G14")
    out = json.loads((ROOT / "outputs" / ("results.json" if dataset == "regular"
                                          else "blind_results.json")).read_text(encoding="utf-8"))
    return d, out


def fd(E, EF, kT):
    return 1.0 / (np.exp((E - EF) / kT) + 1.0)


def l1(d, out):
    rows = np.loadtxt(d / "L1_data.csv", delimiter=",", skiprows=1)
    p = json.loads((d / "L1_params.json").read_text(encoding="utf-8"))
    c, T, EFop, rho = float(p["c"]), float(p["T"]), float(p["EF_op_eV"]), float(p["rho_ohm_sq"])
    kT = KB * T
    E = np.linspace(0.0, 2.5, 250001)
    g = NA * c * E
    f = fd(E, EFop, kT)
    n_band = float(np.trapezoid(g * f, E))
    hi = E >= EFop
    n_F = float(np.trapezoid((g * f)[hi], E[hi]))
    C = n_band / n_F
    mu = 1.0 / (QE * n_F * rho)
    # closed form for the Fermi-referenced integral
    n_F_closed = NA * c * kT * (EFop * np.log(2.0) + np.pi ** 2 / 12.0 * kT)
    # the CSV's own n_band column at the operating point
    # the CSV's n_band column, checked at its own tabulated E_F values
    n_csv_at = np.array([np.trapezoid(g * fd(E, ef, kT), E) for ef in rows[:, 0]])
    n_csv_err = float(np.max(np.abs(n_csv_at / rows[:, 1] - 1)))
    ref = out["L1"]
    print("L1")
    print("  C            independent %.12f   pipeline %.12f   rel %.2e"
          % (C, ref["correction_factor"], abs(C / ref["correction_factor"] - 1)))
    print("  n_F /cm^-2   independent %.6e   pipeline %.6e   rel %.2e"
          % (n_F, ref["n_fermi_op_cm2"], abs(n_F / ref["n_fermi_op_cm2"] - 1)))
    print("  mobility     independent %.6f   pipeline %.6f   rel %.2e"
          % (mu, ref["mobility_corrected_cm2_Vs"],
             abs(mu / ref["mobility_corrected_cm2_Vs"] - 1)))
    print("  n_band vs CSV column, worst over its 12 rows: rel %.2e" % n_csv_err)
    print("  n_F closed form vs grid:       rel %.2e" % (abs(n_F_closed / n_F - 1)))
    return {"C": C, "n_F": n_F, "mu": mu, "n_band": n_band}


def curve(EF, kT, model, Eg_kT=0.0, nE=4000, span=2.5):
    """Normalised (R_H, R_s) model curve, built by direct trapezoid integrals.

    nE and span are explicit so the same function can reproduce the pipeline's
    4000-point integration grid and, separately, a converged one.
    """
    E = np.linspace(-span, span, nE)
    if model == "cone":
        g = np.abs(E)
    else:
        half = 0.5 * Eg_kT * kT
        g = np.where(np.abs(E) > half, np.abs(E) - half, 0.0)
    n = np.empty(EF.size)
    p = np.empty(EF.size)
    for i, ef in enumerate(EF):
        F = fd(E, ef, kT)
        n[i] = np.trapezoid(np.where(E >= ef, g * F, 0.0), E)
        p[i] = np.trapezoid(np.where(E <= ef, g * (1.0 - F), 0.0), E)
    RH = (p - n) / (n + p) ** 2
    Rs = 1.0 / (n + p)
    return RH / np.abs(RH).max(), Rs / Rs.max()


def nearest_rms(RHm, Rsm, RHc, Rsc):
    d2 = (RHm[:, None] - RHc[None, :]) ** 2 + (Rsm[:, None] - Rsc[None, :]) ** 2
    return float(np.sqrt(np.mean(np.min(d2, axis=1))))


def l2(d, out):
    rows = np.loadtxt(d / "L2_data.csv", delimiter=",", skiprows=1)
    meta = json.loads((d / "L2_meta.json").read_text(encoding="utf-8"))
    kT = KB * float(meta["T_K"])
    idx = rows[:, 0].astype(int)
    n_idx = int(idx.max()) + 1
    RHm = np.array([rows[idx == i, 2].mean() for i in range(n_idx)])
    Rsm = np.array([rows[idx == i, 3].mean() for i in range(n_idx)])
    RHm = RHm / np.max(np.abs(RHm))
    Rsm = Rsm / np.max(np.abs(Rsm))

    EF = np.linspace(-8.0, 9.0, 400) * kT
    print("L2")
    res = {}
    labels = (("replica 4000-point E grid", 4000),
              ("converged 20001-point E grid", 20001))
    for label, nE in labels:
        RHc, Rsc = curve(EF, kT, "cone", nE=nE)
        r_cone = nearest_rms(RHm, Rsm, RHc, Rsc)
        gaps = {}
        for Eg in (0.25, 0.5, 0.75, 1.0):
            RHg, Rsg = curve(EF, kT, "gap", Eg, nE=nE)
            gaps[Eg] = nearest_rms(RHm, Rsm, RHg, Rsg)
        res[label] = (r_cone, gaps)
        print("  %s: cone %.9f | gaps " % (label, r_cone)
              + " ".join("Eg=%.2g kT: %.9f" % (k, v) for k, v in gaps.items()))
    ref = out["_meta"]["L2"]
    print("  pipeline r_cone %.9f, best gap %.9f"
          % (ref["r_cone"], ref["best_gap_rms"]))
    RHc, Rsc = curve(EF, kT, "cone")
    j = np.argmin((RHm[:, None] - RHc[None, :]) ** 2
                  + (Rsm[:, None] - Rsc[None, :]) ** 2, axis=1)
    ef_traj = EF[j]
    print("  E_F trajectory vs pipeline: max abs diff %.2e eV"
          % np.abs(ef_traj - np.asarray(out["L2"]["EF_trajectory_eV"])).max())
    wing = EF / kT >= 4.0
    slope = float(np.polyfit(np.log(Rsc[wing]), np.log(np.abs(RHc[wing])), 1)[0])
    print("  log-log slope of |R_H| vs R_s over 4-9 kT: %.3f" % slope)
    print("  selection rule needs gap < 0.85 r_cone = %.9f; best replica gap %.9f"
          % (0.85 * res["replica 4000-point E grid"][0],
             min(res["replica 4000-point E grid"][1].values())))
    return res


def build_system(A, npix=10):
    rows = []
    for i in range(npix):
        for j in range(npix):
            k = i * npix + j
            if j < npix - 1:
                r = np.zeros(npix * npix); r[k] = -1; r[k + 1] = 1; rows.append(r)
            if i < npix - 1:
                r = np.zeros(npix * npix); r[k] = -1; r[k + npix] = 1; rows.append(r)
    L = np.asarray(rows)
    one = np.ones((npix * npix, 1)) / np.sqrt(npix * npix)
    P = np.eye(npix * npix) - one @ one.T
    eta0 = 1e-2 * np.linalg.norm(A, 2) ** 2 / np.linalg.norm(L, 2) ** 2
    return L, P, float(eta0)


def reconstruct(d, A, P, L, eta, npix=10):
    N = npix * npix
    M = P @ (A.T @ A + eta * (L.T @ L)) @ P + 1e-9 * np.eye(N)
    b = P @ (A.T @ d)
    m = np.linalg.solve(M, b)
    return m - m.mean()


def fwhm(q, centre_idx, spacing, npix=10):
    w = np.maximum(q, 0.0)
    i0, j0 = divmod(centre_idx, npix)
    r2 = np.zeros(npix * npix)
    for k in range(npix * npix):
        i, j = divmod(k, npix)
        r2[k] = ((i - i0) * spacing) ** 2 + ((j - j0) * spacing) ** 2
    return float(2.355 * np.sqrt((w * r2).sum() / (2.0 * w.sum())))


def l3(d, out):
    A = np.load(d / "L3_A.npy")
    d_reps = np.loadtxt(d / "L3_d.csv", delimiter=",")
    dbar = d_reps.mean(axis=0)
    sigma = d_reps.std(axis=0, ddof=1)
    noise = float(np.sqrt((sigma ** 2).sum()))
    sv = np.linalg.svd(A, compute_uv=False)
    n_null = int((sv < 1e-10).sum())
    L, P, eta0 = build_system(A)
    eta = 0.01 * eta0
    for mult in np.logspace(np.log10(0.01), np.log10(3.0), 60):
        m = reconstruct(dbar, A, P, L, eta0 * mult)
        if np.linalg.norm(dbar - A @ m) <= noise:
            eta = eta0 * float(mult)
        else:
            break
    m = reconstruct(dbar, A, P, L, eta).reshape(10, 10)
    m_eta0 = reconstruct(dbar, A, P, L, eta0).reshape(10, 10)
    ref_map = np.asarray(out["L3"]["map"]).reshape(10, 10)
    print("L3")
    print("  rank %d of 100, null directions %d, smallest sv %.2e"
          % (int((sv > 1e-10).sum()), n_null, sv[-1]))
    print("  eta chosen %.6e (%.5f eta0); pipeline %.6e"
          % (eta, eta / eta0, out["_meta"]["L3"]["eta_chosen"]))
    print("  max|m| independent %.9f  pipeline %.9f  abs diff %.2e"
          % (np.abs(m).max(), out["_meta"]["L3"]["max_abs_map"],
             abs(np.abs(m).max() - out["_meta"]["L3"]["max_abs_map"])))
    print("  map vs pipeline: max abs diff %.2e" % np.abs(m - ref_map).max())
    # resolution in probe pitches (0.6 pitch per cell) and in map cells
    pitch = 0.6
    r_c = fwhm(reconstruct(A @ (np.eye(100)[55] - 1.0 / 100), A, P, L, eta), 55, pitch)
    r_o = fwhm(reconstruct(A @ (np.eye(100)[22] - 1.0 / 100), A, P, L, eta), 22, pitch)
    y_c = A @ (np.eye(100)[55] - 1.0 / 100)
    r_c_idx = fwhm(reconstruct(y_c, A, P, L, eta0), 55, 1.0)
    print("  FWHM centre %.4f, off-centre %.4f pitch (max %.4f); pipeline %.4f"
          % (r_c, r_o, max(r_c, r_o), out["L3"]["resolution_probe_pitch"]))
    print("  at eta0 in map-cell units: %.4f; at eta0 in pitches: %.4f"
          % (r_c_idx, fwhm(reconstruct(y_c, A, P, L, eta0), 55, 0.6)))
    rng = np.random.default_rng(20260921)
    maxima = np.array([np.abs(reconstruct(rng.normal(0.0, sigma), A, P, L, eta)).max()
                       for _ in range(500)])
    delta95 = float(np.percentile(maxima, 95))
    print("  delta95 independent %.6e  pipeline %.6e"
          % (delta95, out["L3"]["detection_limit_fraction"]))
    # gradient: refit the plane on map indices, convert to per-pitch units
    yy, xx = np.meshgrid(np.arange(10), np.arange(10), indexing="ij")
    X = np.column_stack([np.ones(100), xx.ravel(), yy.ravel()])
    coef = np.linalg.lstsq(X, m.ravel(), rcond=None)[0]
    gx, gy = coef[1] / pitch, coef[2] / pitch
    corner = abs(coef[0] + 9 * coef[1] + 9 * coef[2])
    print("  gradient per pitch (%.6f, %.6f), magnitude %.6f, corner trend %.6f (%.2f%%)"
          % (gx, gy, np.hypot(gx, gy), corner, 100 * corner))
    print("  at eta0: max|m| %.9f, map vs the eta-chosen map %.2e"
          % (np.abs(m_eta0).max(), np.abs(m_eta0 - m).max()))
    return m, m_eta0


def student_check(student_dir, dataset, l1v, m_eta0):
    base = Path(student_dir)
    if not base.exists():
        return
    print("Student working copy (September submission)")
    if dataset == "regular":
        sp = base / "L2" / "results.json"
        s1 = json.loads((base / "L1" / "results.json").read_text(encoding="utf-8"))
    else:
        sp = base / "L3" / "blind_results.json"
        s1 = json.loads(sp.read_text(encoding="utf-8"))
    c = s1["L1"]
    print("  L1 C %.12f (diff %.2e), n_F %.6e (rel %.2e), mu %.6f (rel %.2e)"
          % (c["correction_factor"], abs(c["correction_factor"] - l1v["C"]),
             c["n_fermi_op_cm2"], abs(c["n_fermi_op_cm2"] / l1v["n_F"] - 1),
             c["mobility_corrected_cm2_Vs"],
             abs(c["mobility_corrected_cm2_Vs"] / l1v["mu"] - 1)))
    s2 = json.loads(sp.read_text(encoding="utf-8"))
    ef_student = np.asarray(s2["L2"]["EF_trajectory_eV"])
    print("  L2 model %s, Eg %.3f kT, %d indices"
          % (s2["L2"]["model"], s2["L2"]["Eg_kT"], ef_student.size))
    s3map = np.asarray(s2["L3"]["map"]).reshape(10, 10)
    print("  L3 map vs the eta0 re-derivation: max %.2e" % np.abs(s3map - m_eta0).max())
    print("  L3 resolution as submitted %.6f (map-cell units); in pitches that is %.6f"
          % (s2["L3"]["resolution_probe_pitch"], s2["L3"]["resolution_probe_pitch"] * 0.6))
    print("  L3 detection limit submitted %.3e; verdict %s"
          % (s2["L3"]["detection_limit_fraction"], s2["L3"]["confidence"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="regular", choices=["regular", "blind"])
    ap.add_argument("--student-dir", default=None)
    a = ap.parse_args()
    d, out = load(a.dataset)
    print("Independent re-derivation, dataset = %s" % a.dataset)
    l1v = l1(d, out)
    l2(d, out)
    m, m_eta0 = l3(d, out)
    if a.student_dir:
        student_check(a.student_dir, a.dataset, l1v, m_eta0)


if __name__ == "__main__":
    main()
