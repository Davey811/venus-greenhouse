#!/usr/bin/env python3
"""The Venus Test: is Venus hot because of pressure, or because of the greenhouse effect?

Two runs with the same sunlight, the same 92 bar and the same lapse rate:
  1. pressure only    the air is transparent in the infrared, the ground radiates straight to space
  2. IR-opaque CO2    the planet radiates to space from the level where the measured profile reaches Te

For each run the script checks two energy ledgers, per square metre, planet average:
  Venus as a whole   infrared sent to space = sunlight absorbed (steady state)
  the ground         what the ground emits = sunlight it absorbs + what comes back from the air
It also prints the ceiling for a ground that radiates freely to space if Venus reflected nothing,
and the greenhouse effect G = infrared emitted by the ground - infrared sent to space, with Earth's for comparison.

Usage:
    python3 venus_test.py      # prints the ledgers, writes results/numbers.txt and results/venus_test.png
"""
import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SIGMA = 5.670374419e-8
S, ALBEDO = 2601.3, 0.77          # NASA Venus Fact Sheet: solar irradiance (W/m2), Bond albedo
R_VENUS = 6051.8                  # km, mean radius (NASA Venus Fact Sheet)
SUN_AT_GROUND = 17.0              # W/m2, average surface insolation (Taylor & Grinspoon 2009, sec. 2.4)
EARTH_SURFACE_LW = 396.0          # W/m2, Earth's surface emission (Trenberth & Fasullo 2012)
EARTH_OLR = 1361 * (1 - 0.294) / 4  # W/m2 to space = sunlight absorbed (NASA Earth Fact Sheet)
BASE = os.path.dirname(os.path.abspath(__file__))

# Taylor & Grinspoon (2009), Table 2, from the model of Bullock & Grinspoon (2001):
# surface cooling (K) when one species is removed, the others kept, albedo fixed. Not additive.
REMOVE_ONE = [("CO2", 422.7), ("clouds", 142.8), ("H2O", 68.8), ("OCS", 12.0), ("CO", 3.3), ("SO2", 2.5), ("HCl", 1.5)]


def load():
    with open(os.path.join(BASE, "data", "venus_vira.csv")) as f:
        rows = list(csv.DictReader(f))
    return (np.array([float(r[k]) for r in rows]) for k in ("altitude_km", "temperature_K"))


def crossing(z, T, Te):
    for i in range(len(z) - 1):
        if (T[i] - Te) * (T[i + 1] - Te) <= 0:
            return z[i] + (T[i] - Te) / (T[i] - T[i + 1]) * (z[i + 1] - z[i])


def main():
    z, T = load()
    absorbed = S * (1 - ALBEDO) / 4                 # planet-average absorbed sunlight
    Te = (absorbed / SIGMA) ** 0.25
    # the emission level is a sphere of radius R + h: it radiates the same power as Te over the ground,
    # so its temperature is T_em(h) = Te * sqrt(R / (R + h)). Find where the measured profile reaches it.
    T_em = lambda h: Te * (R_VENUS / (R_VENUS + h)) ** 0.5
    ze = crossing(z, T, Te)
    for _ in range(20):
        ze = crossing(z, T, T_em(ze))                # emission level
    gamma = (T[0] - T_em(ze)) / ze                  # mean lapse rate, ground to emission level

    ceiling = (S / 4 / SIGMA) ** 0.25               # transparent air, nothing reflected

    runs = []
    for name, h, opaque in (("pressure only (air that doesn't absorb infrared)", 0.0, False),
                            ("pressure + infrared absorbers (radiating from the emission level)", ze, True)):
        Ts = T_em(h) + gamma * h
        emit = SIGMA * Ts ** 4
        leaves = absorbed                           # steady state; transparent air: all of it from the ground
        sun_ground = SUN_AT_GROUND if opaque else absorbed
        back = emit - sun_ground                    # at least this much must come back from the air
        runs.append((name, h, Ts, emit, leaves, sun_ground, back))

    out = [
        f"absorbed sunlight (planet average)  {absorbed:7.1f} W/m2",
        f"effective temperature Te            {Te:7.2f} K",
        f"emission level (profile reaches T_em) {ze:5.2f} km, T_em = {T_em(ze):.2f} K (curvature)",
        f"mean lapse rate                     {gamma:7.3f} K/km",
        f"measured surface                    {T[0]:7.1f} K",
        f"ceiling, transparent air and nothing reflected: sigma T^4 = {S / 4:.1f} W/m2 -> {ceiling:.1f} K",
        "",
    ]
    for name, h, Ts, emit, leaves, sun_ground, back in runs:
        out += [
            name,
            f"  ground {Ts:6.1f} K ({Ts - 273.15:5.1f} C), emission height {h:5.2f} km",
            f"  Venus: absorbs {absorbed:6.1f} W/m2, sends to space {leaves:6.1f} W/m2 -> balanced",
            f"  ground: emits {emit:9.1f} W/m2 ({emit / absorbed:5.1f} x what Venus absorbs, {emit / (S / 4):4.1f} x all sunlight reaching Venus)",
            f"          sunlight absorbed {'<=' if h > 0 else '  '} {sun_ground:6.1f} W/m2, must come back from the air "
            f"{'>=' if h > 0 else '  '} {back:8.1f} W/m2 ({100 * back / emit:4.1f}%)",
            f"  greenhouse effect G = ground emits - sent to space = {emit - leaves:8.1f} W/m2",
            "",
        ]
    G_earth = EARTH_SURFACE_LW - EARTH_OLR
    out += [f"Earth for comparison: G = {EARTH_SURFACE_LW:.0f} - {EARTH_OLR:.1f} = {G_earth:.1f} W/m2; "
            f"Venus / Earth = {(runs[1][3] - runs[1][4]) / G_earth:.0f}", ""]
    # explicit equations, Earth alongside Venus, and the middle-of-the-mass rule
    T0_E, L_E, R_E = 288.15, 6.5, 6371.0                     # U.S. Standard Atmosphere 1976, Earth radius
    Te_E = (1361 * (1 - 0.294) / 4 / SIGMA) ** 0.25           # NASA Earth Fact Sheet
    expo = 9.80665 * 0.0289644 / (8.3144598 * 0.0065)        # hydrostatic exponent of the 1976 troposphere
    zhalf_E = (T0_E - T0_E * 0.5 ** (1 / expo)) / L_E         # half of the mass above
    ze_E = 5.0
    for _ in range(60):
        ze_E = (T0_E - Te_E * (R_E / (R_E + ze_E)) ** 0.5) / L_E
    Tem_E = Te_E * (R_E / (R_E + ze_E)) ** 0.5
    zhalf_V = 10.40                                           # VIRA: half of the mass above (see slope-and-height)
    rule_E, rule_V = Te_E + L_E * zhalf_E, Te + gamma * zhalf_V
    out += [
        "Explicit equations: T_s = T_em + Gamma x z_e",
        f"  Earth: {Tem_E:.2f} + {L_E} x {ze_E:.3f} = {Tem_E + L_E * ze_E:.2f} K (measured {T0_E} K)",
        f"  Venus: {T_em(ze):.2f} + {gamma:.3f} x {ze:.2f} = {T_em(ze) + gamma * ze:.2f} K (measured {T[0]} K)",
        "Middle-of-the-mass rule: T_s = T_e + Gamma x z_half",
        f"  Earth: {Te_E:.2f} + {L_E} x {zhalf_E:.2f} = {rule_E:.2f} K, off by {T0_E - rule_E:+.2f} K",
        f"  Venus: {Te:.2f} + {gamma:.3f} x {zhalf_V:.2f} = {rule_V:.2f} K, off by {T[0] - rule_V:+.1f} K",
        "",
    ]
    # First Law in time: raise the emission level by dz, integrate C dTs/dt = absorbed - outgoing
    C = (9.21e6 / 8.87) * 1100.0                             # J/(m2 K), whole column, cp of CO2 at 600-700 K
    out.append(f"First Law in time, C = {C:.3g} J/(m2 K), e-folding {C / (4 * SIGMA * T_em(ze) ** 3) / 3.156e7:.1f} years")
    for dz in (1.0, 5.0):
        z1, ts0 = ze + dz, T_em(ze) + gamma * ze
        f = ((R_VENUS + z1) / R_VENUS) ** 2
        ts, total, dt = ts0, 0.0, 0.02 * 3.156e7
        first = SIGMA * (ts - gamma * z1) ** 4 * f - absorbed
        for _ in range(4001):
            imb = absorbed - SIGMA * (ts - gamma * z1) ** 4 * f
            ts += imb * dt / C
            total += imb * dt
        out.append(f"  +{dz:.0f} km: outgoing - absorbed {first:+.1f} W/m2, ground {ts - ts0:+.2f} K after 80 years "
                   f"(end state {T_em(z1) + gamma * z1 - ts0:+.2f} K), stored {C * (ts - ts0) / 1e9:.2f} GJ/m2 = added up {total / 1e9:.2f} GJ/m2")
    out.append("")
    # radiation only: Eddington grey radiative equilibrium with the same absorbers
    with open(os.path.join(BASE, "data", "venus_vira.csv")) as fh:
        rows = list(csv.DictReader(fh))
    zz = np.array([float(r["altitude_km"]) for r in rows]); pp = np.array([float(r["pressure_bar"]) for r in rows])
    p_e = float(np.exp(np.interp(ze, zz, np.log(pp))))
    tau0 = pp[0] / p_e
    T_rad = Te * (0.75 * tau0 + 0.5) ** 0.25
    slope = np.log(T[0] / T[2]) / np.log(pp[0] / pp[2])
    out += [
        "Radiation only (Eddington grey atmosphere, no convection):",
        f"  tau0 = p0 / p(z_e) = {pp[0]} / {p_e:.4f} = {tau0:.0f}",
        f"  ground T = Te (3 tau0/4 + 1/2)^(1/4) = {T_rad:.0f} K (measured {T[0]} K)",
        f"  d lnT / d lnp: radiative 0.25, adiabat R/cp = {188.9 / 1100:.3f}, measured 0-10 km {slope:.3f}",
        "",
    ]
    # if compression paid the bill: gravitational energy of the column, and the sinking speed needed
    E = sum((zz[i + 1] - zz[i]) * 1e3 / np.log(pp[i] / pp[i + 1]) * (pp[i] - pp[i + 1]) * 1e5
            for i in range(len(zz) - 1) if zz[i + 1] <= 80)
    E += float(np.interp(80, zz, pp)) * 1e5 * 4.7e3        # above 80 km
    bill = SIGMA * T[0] ** 4 - SUN_AT_GROUND
    out += [
        "If compression paid the bill:",
        f"  ground's bill {bill:.0f} W/m2 -> sinking speed {bill / (pp[0] * 1e5) * 1e3:.2f} mm/s = {bill / (pp[0] * 1e5) * 3.156e7 / 1e3:.0f} km/yr",
        f"  gravitational energy of the atmosphere {E / 1e9:.0f} GJ/m2, centre of mass {E / (pp[0] * 1e5) / 1e3:.1f} km, lasts {E / bill / 86400:.0f} days",
        "",
    ]
    out.append("Published model, one species removed (Taylor & Grinspoon 2009, Table 2):")
    out += [f"  {n:7s} -{d:5.1f} K  ->  about {int(np.floor(T[0] - d + 0.5))} K" for n, d in REMOVE_ONE]
    total = sum(d for _, d in REMOVE_ONE)
    out += [f"  sum of the single effects {total:.1f} K, but everything off leaves the ground at Te: "
            f"{T[0] - Te:.1f} K of warming in all -> the effects overlap, they don't add up"]
    print("\n".join(out))
    os.makedirs(os.path.join(BASE, "results"), exist_ok=True)
    with open(os.path.join(BASE, "results", "numbers.txt"), "w") as f:
        f.write("\n".join(out) + "\n")

    BG, FG, DIM = "#0f1419", "#e7e9ea", "#8b98a5"
    COLS = ("#a0aec0", "#4fd1c5")
    plt.rcParams.update({"text.color": FG, "axes.labelcolor": FG, "xtick.color": DIM, "ytick.color": DIM,
                         "axes.edgecolor": DIM, "figure.facecolor": BG, "axes.facecolor": BG, "font.family": "DejaVu Sans"})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 6), dpi=160, gridspec_kw={"width_ratios": [1.25, 1]})

    m = z <= 80
    a1.plot(T[m], z[m], color=FG, alpha=0.5, lw=2.4, label="measured (VIRA)")
    a1.axvline(Te, color=DIM, ls="--", lw=1)
    a1.text(Te + 4, 77, f"Te = {Te:.1f} K", color=DIM, fontsize=9)
    for (name, h, Ts, *_), c, lab in zip(runs, COLS, ("pressure only", "infrared absorbers")):
        if h > 0:
            a1.plot([T_em(h), Ts], [h, 0], color=c, lw=2.6)
            a1.plot(T_em(h), h, "o", color=c, ms=7)
            a1.text(T_em(h) + 8, h + 1.5, f"radiates to space from {h:.0f} km", color=c, fontsize=9)
        a1.plot(Ts, 0, "o", color=c, ms=11, clip_on=False, label=f"{lab}: ground {Ts:.0f} K")
    a1.set_xlim(150, 760)
    a1.set_ylim(0, 80)
    a1.set_xlabel("temperature (K)")
    a1.set_ylabel("altitude (km)")
    a1.set_title("Same slope, different height", loc="left", fontsize=12)
    a1.grid(alpha=0.15)
    a1.legend(frameon=False, fontsize=9, loc="upper right")

    # where the ground's energy goes, log scale
    items = ("Venus absorbs\n= sends\nto space", "ground\nemits", "sunlight\nabsorbed by\nthe ground", "must come\nback from\nthe air")
    x = np.arange(len(items))
    for k, ((name, h, Ts, emit, leaves, sun_ground, back), c, lab) in enumerate(zip(runs, COLS, ("pressure only", "infrared absorbers"))):
        vals = (absorbed, emit, sun_ground, back)
        xs = x + (k - 0.5) * 0.38
        a2.bar(xs, [max(v, 1e-9) for v in vals], 0.36, color=c, label=lab)
        for xi, v in zip(xs, vals):
            txt = "0" if v < 0.5 else (f"{v / 1000:.1f}k" if v >= 1000 else f"{v:.0f}")
            a2.text(xi, max(v, 6) * 1.12, txt, ha="center", va="bottom", fontsize=8.5, color=c)
    a2.set_yscale("log")
    a2.set_ylim(5, 60000)
    a2.set_xticks(x, items, fontsize=9)
    a2.set_ylabel("W/m²")
    a2.set_title("Energy ledger, per m² (log scale)", loc="left", fontsize=12)
    a2.grid(alpha=0.15, axis="y")
    a2.legend(frameon=False, fontsize=9, loc="upper left")

    fig.suptitle("The Venus Test: the lapse rate sets the slope, the greenhouse effect sets the height", x=0.01, ha="left", fontsize=13)
    fig.text(0.01, 0.01, "Data: VIRA (Seiff et al. 1985); NASA Venus Fact Sheet; Taylor & Grinspoon 2009 (17 W/m² at the ground)   ·   Made with Python by @splugged",
             fontsize=8, color=DIM)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    path = os.path.join(BASE, "results", "venus_test.png")
    fig.savefig(path, facecolor=BG)
    print("saved", path)


if __name__ == "__main__":
    main()
