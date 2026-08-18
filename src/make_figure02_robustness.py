from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SENSITIVITY = Path(
    "results/tables/stage1_stage2_q0_sensitivity_tests.csv"
)

SOIL = Path(
    "results/tables/stage1_stage2_soil_stratified_tests.csv"
)

OUT_DIR = Path(
    "results/figures/final"
)

OUT_PNG = OUT_DIR / (
    "figure_02_robustness_and_soil_stratification.png"
)

OUT_PDF = OUT_DIR / (
    "figure_02_robustness_and_soil_stratification.pdf"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

sens = pd.read_csv(
    SENSITIVITY
)

soil = pd.read_csv(
    SOIL
)

# ============================================================
# DEFINITIONS
# ============================================================

metric_order = [
    "y25",
    "y50",
    "y75",
    "mean_y_10_90",
]

metric_labels = {
    "y25":
        r"$y_{25}$",

    "y50":
        r"$y_{50}$",

    "y75":
        r"$y_{75}$",

    "mean_y_10_90":
        r"$\bar{y}_{10-90}$",
}

COLORS = {
    "y25":
        "#4C78A8",

    "y50":
        "#D55E00",

    "y75":
        "#6A9F58",

    "mean_y_10_90":
        "#7A5195",
}

MARKERS = {
    "y25":
        "o",

    "y50":
        "s",

    "y75":
        "^",

    "mean_y_10_90":
        "D",
}

SOIL_COLORS = {
    "MH":
        "#4C78A8",

    "ML":
        "#D55E00",
}

# ============================================================
# STRICT QC
# ============================================================

for q0 in [
    0.02,
    0.05,
    0.10,
    0.15,
]:

    subset = sens[
        np.isclose(
            sens["q0_fraction"],
            q0,
        )
    ]

    if len(subset) != 4:

        raise SystemExit(
            f"FIGURE 02 FAIL: "
            f"q0={q0} has {len(subset)} metrics."
        )

for soil_type in [
    "MH",
    "ML",
]:

    subset = soil[
        soil["soil_type"]
        == soil_type
    ]

    if len(subset) != 4:

        raise SystemExit(
            f"FIGURE 02 FAIL: "
            f"{soil_type} has {len(subset)} metrics."
        )

# ============================================================
# STYLE
# ============================================================

plt.rcParams.update({
    "font.family":
        "DejaVu Serif",

    "mathtext.fontset":
        "stix",

    "font.size":
        10,

    "axes.labelsize":
        11,

    "axes.titlesize":
        11,

    "legend.fontsize":
        9,

    "xtick.labelsize":
        9,

    "ytick.labelsize":
        9,

    "axes.linewidth":
        0.9,

    "lines.linewidth":
        1.6,

    "pdf.fonttype":
        42,

    "ps.fonttype":
        42,
})

# Extra width on the right is intentional:
# panel-b legend lives outside the plotting area.
fig, axes = plt.subplots(
    1,
    2,
    figsize=(
        10.4,
        4.15,
    ),
)

ax1, ax2 = axes

# ============================================================
# PANEL A
# q0 SENSITIVITY
# ============================================================

for metric in metric_order:

    frame = (
        sens[
            sens["metric"]
            == metric
        ]
        .sort_values(
            "q0_fraction"
        )
    )

    x = (
        100.0
        * frame[
            "q0_fraction"
        ].to_numpy(float)
    )

    mean = frame[
        "mean_delta"
    ].to_numpy(float)

    lo = frame[
        "bootstrap_p025"
    ].to_numpy(float)

    hi = frame[
        "bootstrap_p975"
    ].to_numpy(float)

    yerr = np.vstack([
        mean - lo,
        hi - mean,
    ])

    ax1.errorbar(
        x,
        mean,
        yerr=yerr,
        marker=MARKERS[
            metric
        ],
        markersize=5.2,
        capsize=3.2,
        elinewidth=1.15,
        color=COLORS[
            metric
        ],
        label=metric_labels[
            metric
        ],
    )

ax1.axhline(
    0.0,
    color="#777777",
    linestyle="--",
    linewidth=1.0,
)

ax1.set_xlim(
    0.0,
    16.5,
)

ax1.set_ylim(
    0.0,
    0.235,
)

ax1.set_xticks([
    0,
    2,
    5,
    10,
    15,
])

ax1.set_xlabel(
    r"Stage-start window for $q_0$ "
    r"(% of $\varepsilon_{a,p}$)"
)

ax1.set_ylabel(
    r"Paired mobilization shift, "
    r"Stage 2 $-$ Stage 1"
)

# ------------------------------------------------------------
# FIX 1:
# Legend moved completely ABOVE panel A.
# Therefore it cannot cover "(a)" or the data.
# ------------------------------------------------------------

ax1.legend(
    frameon=False,
    loc="lower center",
    bbox_to_anchor=(
        0.53,
        1.025,
    ),
    ncol=4,
    columnspacing=1.5,
    handlelength=2.0,
    borderaxespad=0.0,
)

ax1.text(
    0.02,
    0.96,
    "(a)",
    transform=ax1.transAxes,
    ha="left",
    va="top",
    fontweight="bold",
    fontsize=11,
)

ax1.text(
    0.97,
    0.045,
    "95% tube-cluster\nbootstrap intervals",
    transform=ax1.transAxes,
    ha="right",
    va="bottom",
    fontsize=8,
)

# ============================================================
# PANEL B
# SOIL-STRATIFIED EFFECT
# ============================================================

positions = np.arange(
    len(
        metric_order
    )
)

offset = 0.11

for soil_type, shift in [
    (
        "MH",
        -offset,
    ),
    (
        "ML",
        +offset,
    ),
]:

    frame = (
        soil[
            soil["soil_type"]
            == soil_type
        ]
        .set_index(
            "metric"
        )
        .loc[
            metric_order
        ]
        .reset_index()
    )

    mean = frame[
        "mean_delta"
    ].to_numpy(float)

    lo = frame[
        "bootstrap_p025"
    ].to_numpy(float)

    hi = frame[
        "bootstrap_p975"
    ].to_numpy(float)

    xerr = np.vstack([
        mean - lo,
        hi - mean,
    ])

    ax2.errorbar(
        mean,
        positions
        + shift,
        xerr=xerr,
        fmt="o",
        markersize=5.5,
        capsize=3.2,
        elinewidth=1.2,
        color=SOIL_COLORS[
            soil_type
        ],
        label=soil_type,
    )

ax2.axvline(
    0.0,
    color="#777777",
    linestyle="--",
    linewidth=1.0,
)

ax2.set_yticks(
    positions
)

ax2.set_yticklabels(
    [
        metric_labels[
            metric
        ]
        for metric in metric_order
    ]
)

ax2.invert_yaxis()

ax2.set_xlim(
    0.0,
    0.325,
)

ax2.set_xlabel(
    r"Paired mobilization shift, "
    r"Stage 2 $-$ Stage 1"
)

ax2.set_ylabel(
    "Direct mobilization descriptor"
)

ax2.text(
    0.02,
    0.96,
    "(b)",
    transform=ax2.transAxes,
    ha="left",
    va="top",
    fontweight="bold",
    fontsize=11,
)

# ------------------------------------------------------------
# FIX 2:
# Soil-class legend moved OUTSIDE the axes.
# It can no longer cover y25 or any confidence interval.
# ------------------------------------------------------------

ax2.legend(
    frameon=False,
    loc="upper left",
    bbox_to_anchor=(
        1.025,
        1.00,
    ),
    title="Soil class",
    borderaxespad=0.0,
)

# ============================================================
# BOXED ENGINEERING AXES
# ============================================================

for ax in axes:

    for side in [
        "left",
        "right",
        "top",
        "bottom",
    ]:

        ax.spines[
            side
        ].set_visible(
            True
        )

        ax.spines[
            side
        ].set_linewidth(
            0.9
        )

    ax.tick_params(
        direction="out",
        length=3.5,
        width=0.8,
        top=False,
        right=False,
    )

# ============================================================
# MANUAL LAYOUT
#
# Do not use tight_layout here.
# Explicit margins prevent legends/labels from colliding.
# ============================================================

fig.subplots_adjust(
    left=0.085,
    right=0.835,
    bottom=0.235,
    top=0.815,
    wspace=0.34,
)

# ------------------------------------------------------------
# FIX 3:
# q0 definition moved OUT of panel B and into the footer.
# Therefore it cannot cover ybar_10-90.
# ------------------------------------------------------------

fig.text(
    0.46,
    0.105,
    (
        "Stage 1–Stage 2 paired analysis; "
        "25 specimens from 18 independent tubes. "
        "Soil-stratified inference shown for MH and ML only."
    ),
    ha="center",
    va="center",
    fontsize=8.5,
)

fig.text(
    0.46,
    0.055,
    (
        r"Primary stage-start baseline: "
        r"$q_0$ estimated over "
        r"$\varepsilon_a \leq 0.05\,\varepsilon_{a,p}$."
    ),
    ha="center",
    va="center",
    fontsize=8.3,
)

# ============================================================
# SCIENTIFIC QC
# ============================================================

if not (
    sens[
        "bootstrap_p025"
    ] > 0
).all():

    raise SystemExit(
        "FIGURE 02 FAIL: "
        "q0 sensitivity interval crosses zero."
    )

if not (
    soil[
        "bootstrap_p025"
    ] > 0
).all():

    raise SystemExit(
        "FIGURE 02 FAIL: "
        "soil-stratified interval crosses zero."
    )

# ============================================================
# SAVE
# ============================================================

fig.savefig(
    OUT_PNG,
    dpi=600,
    bbox_inches="tight",
    facecolor="white",
)

fig.savefig(
    OUT_PDF,
    bbox_inches="tight",
    facecolor="white",
)

plt.close(
    fig
)

# ============================================================
# REPORT
# ============================================================

print("=" * 92)
print(
    "UnsatConstitutiveLab — "
    "Figure 02 Robustness V2"
)
print("=" * 92)

print()
print(
    "Panel A legend outside data region : PASS"
)

print(
    "Panel B legend outside axes       : PASS"
)

print(
    "Primary q0 note moved to footer   : PASS"
)

print(
    "Full boxed axes                   : PASS"
)

print(
    "All q0-window CIs > 0             : PASS"
)

print(
    "All MH/ML CIs > 0                 : PASS"
)

print()
print(
    "Figure PNG:",
    OUT_PNG,
)

print(
    "Figure PDF:",
    OUT_PDF,
)

print()
print(
    "PHASE 6B FIGURE 02 V2: PASS"
)
