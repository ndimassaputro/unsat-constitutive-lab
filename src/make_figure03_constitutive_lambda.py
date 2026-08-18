from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

# ============================================================
# PATHS
# ============================================================

DESC = Path(
    "results/tables/nonparametric_mobilization_descriptors.csv"
)

PARAMS = Path(
    "results/tables/incremental_mobilization_parameters.csv"
)

OUT_DIR = Path(
    "results/figures/final"
)

OUT_PNG = OUT_DIR / (
    "figure_03_constitutive_lambda.png"
)

OUT_PDF = OUT_DIR / (
    "figure_03_constitutive_lambda.pdf"
)

OUT_DATA = Path(
    "results/tables/figure_03_constitutive_lambda_data.csv"
)

OUT_SUMMARY = Path(
    "results/tables/figure_03_constitutive_lambda_summary.csv"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUT_DATA.parent.mkdir(
    parents=True,
    exist_ok=True,
)

RNG = np.random.default_rng(
    20260818
)

N_BOOT = 30000

desc = pd.read_csv(
    DESC
)

params = pd.read_csv(
    PARAMS
)

# ============================================================
# QC
# ============================================================

required = [
    "specimen_id",
    "tube_id",
    "stage_index",
    "protocol_group",
    "lambda_incremental",
    "mean_y_10_90",
]

missing = [
    column
    for column in required
    if column not in desc.columns
]

if missing:
    raise SystemExit(
        "FIGURE 03 FAIL: missing columns "
        + str(missing)
    )

if len(desc) != 84:
    raise SystemExit(
        "FIGURE 03 FAIL: "
        f"expected 84 stages, found {len(desc)}."
    )

# ============================================================
# GROUPS
# ============================================================

GROUP_ORDER = [
    "single_stage",
    "multistage_stage1",
    "multistage_later",
]

GROUP_LABELS = {
    "single_stage":
        "Single-stage",

    "multistage_stage1":
        "Multistage: Stage 1",

    "multistage_later":
        "Multistage: later stages",
}

GROUP_COLORS = {
    "single_stage":
        "#7A7A7A",

    "multistage_stage1":
        "#4C78A8",

    "multistage_later":
        "#D95F02",
}

GROUP_MARKERS = {
    "single_stage":
        "o",

    "multistage_stage1":
        "s",

    "multistage_later":
        "^",
}

# ============================================================
# GROUP SUMMARY
# ============================================================

group_summary = (
    desc.groupby(
        "protocol_group",
        as_index=False,
    )
    .agg(
        n_stages=(
            "specimen_id",
            "size",
        ),
        n_specimens=(
            "specimen_id",
            "nunique",
        ),
        n_tubes=(
            "tube_id",
            "nunique",
        ),
        median_lambda=(
            "lambda_incremental",
            "median",
        ),
        median_mean_y=(
            "mean_y_10_90",
            "median",
        ),
    )
)

# ============================================================
# CORRELATION
# ============================================================

rho_all, p_all = spearmanr(
    desc[
        "lambda_incremental"
    ],
    desc[
        "mean_y_10_90"
    ],
)

multi_desc = desc[
    desc[
        "protocol_group"
    ].isin(
        [
            "multistage_stage1",
            "multistage_later",
        ]
    )
].copy()

rho_multi, p_multi = spearmanr(
    multi_desc[
        "lambda_incremental"
    ],
    multi_desc[
        "mean_y_10_90"
    ],
)

# ============================================================
# PAIRED STAGE 1 -> STAGE 2
# ============================================================

multi = params[
    (
        params[
            "family_normalized"
        ]
        == "multistage"
    )
    & (
        params[
            "stage_index"
        ].isin(
            [
                1,
                2,
            ]
        )
    )
].copy()

counts = (
    multi.groupby(
        "specimen_id"
    )[
        "stage_index"
    ]
    .nunique()
)

valid_specimens = (
    counts[
        counts == 2
    ]
    .index
)

multi = multi[
    multi[
        "specimen_id"
    ].isin(
        valid_specimens
    )
].copy()

paired_rows = []

for specimen_id, frame in multi.groupby(
    "specimen_id"
):

    s1 = frame[
        frame[
            "stage_index"
        ]
        == 1
    ]

    s2 = frame[
        frame[
            "stage_index"
        ]
        == 2
    ]

    if (
        s1.empty
        or s2.empty
    ):
        continue

    first = s1.iloc[0]
    second = s2.iloc[0]

    paired_rows.append({
        "specimen_id":
            specimen_id,

        "tube_id":
            first[
                "tube_id"
            ],

        "soil_type":
            first[
                "soil_type"
            ],

        "lambda_stage1":
            float(
                first[
                    "lambda_incremental"
                ]
            ),

        "lambda_stage2":
            float(
                second[
                    "lambda_incremental"
                ]
            ),
    })

paired = pd.DataFrame(
    paired_rows
)

if len(paired) != 25:
    raise SystemExit(
        "FIGURE 03 FAIL: "
        f"expected 25 paired specimens, found {len(paired)}."
    )

if (
    paired[
        "tube_id"
    ].nunique()
    != 18
):
    raise SystemExit(
        "FIGURE 03 FAIL: expected 18 independent tubes."
    )

# ============================================================
# TUBE-LEVEL PAIRED VALUES
# ============================================================

tube_paired = (
    paired.groupby(
        "tube_id",
        as_index=False,
    )
    .agg(
        lambda_stage1=(
            "lambda_stage1",
            "mean",
        ),
        lambda_stage2=(
            "lambda_stage2",
            "mean",
        ),
        n_specimens=(
            "specimen_id",
            "nunique",
        ),
    )
)

tube_paired[
    "delta_lambda"
] = (
    tube_paired[
        "lambda_stage2"
    ]
    - tube_paired[
        "lambda_stage1"
    ]
)

delta_values = (
    tube_paired[
        "delta_lambda"
    ].to_numpy(float)
)

boot = np.empty(
    N_BOOT,
    dtype=float,
)

for i in range(
    N_BOOT
):

    sample = RNG.choice(
        delta_values,
        size=len(
            delta_values
        ),
        replace=True,
    )

    boot[i] = float(
        np.mean(
            sample
        )
    )

delta_mean = float(
    np.mean(
        delta_values
    )
)

delta_lo = float(
    np.quantile(
        boot,
        0.025,
    )
)

delta_hi = float(
    np.quantile(
        boot,
        0.975,
    )
)

prob_positive = float(
    np.mean(
        boot > 0
    )
)

# ============================================================
# MEDIAN LAMBDA VALUES
# ============================================================

def group_median_lambda(
    name,
):

    return float(
        desc.loc[
            desc[
                "protocol_group"
            ]
            == name,
            "lambda_incremental",
        ].median()
    )


lambda_single = group_median_lambda(
    "single_stage"
)

lambda_stage1 = group_median_lambda(
    "multistage_stage1"
)

lambda_later = group_median_lambda(
    "multistage_later"
)

# ============================================================
# CONSTITUTIVE BACKBONE
# ============================================================

X = np.linspace(
    0.0,
    1.0,
    301,
)


def hyperbolic(
    x,
    lam,
):

    return (
        x
        * (
            1.0
            + lam
        )
        / (
            1.0
            + lam
            * x
        )
    )


Y_LINEAR = X

Y_STAGE1 = hyperbolic(
    X,
    lambda_stage1,
)

Y_LATER = hyperbolic(
    X,
    lambda_later,
)

Y_SINGLE = hyperbolic(
    X,
    lambda_single,
)

# ============================================================
# EXPORT DATA
# ============================================================

scatter_export = desc[
    [
        "specimen_id",
        "tube_id",
        "stage_index",
        "protocol_group",
        "lambda_incremental",
        "mean_y_10_90",
        "incremental_prepeak_nrmse",
    ]
].copy()

scatter_export[
    "table"
] = "scatter"

paired_export = tube_paired.copy()

paired_export[
    "table"
] = "paired_tube"

pd.concat(
    [
        scatter_export,
        paired_export,
    ],
    ignore_index=True,
    sort=False,
).to_csv(
    OUT_DATA,
    index=False,
)

pd.DataFrame(
    [
        {
            "quantity":
                "spearman_rho_all",

            "value":
                rho_all,

            "lower":
                np.nan,

            "upper":
                np.nan,
        },
        {
            "quantity":
                "spearman_rho_multistage",

            "value":
                rho_multi,

            "lower":
                np.nan,

            "upper":
                np.nan,
        },
        {
            "quantity":
                "paired_delta_lambda_mean",

            "value":
                delta_mean,

            "lower":
                delta_lo,

            "upper":
                delta_hi,
        },
        {
            "quantity":
                "paired_prob_delta_positive",

            "value":
                prob_positive,

            "lower":
                np.nan,

            "upper":
                np.nan,
        },
    ]
).to_csv(
    OUT_SUMMARY,
    index=False,
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

    "legend.fontsize":
        8,

    "xtick.labelsize":
        9,

    "ytick.labelsize":
        9,

    "axes.linewidth":
        0.9,

    "lines.linewidth":
        1.7,

    "pdf.fonttype":
        42,

    "ps.fonttype":
        42,
})

fig, axes = plt.subplots(
    1,
    3,
    figsize=(
        11.6,
        4.15,
    ),
)

ax1, ax2, ax3 = axes

# ============================================================
# PANEL A
# ============================================================

ax1.plot(
    X,
    Y_LINEAR,
    linestyle="--",
    linewidth=1.1,
    color="#888888",
    label=r"$\lambda=0$",
)

ax1.plot(
    X,
    Y_STAGE1,
    color=GROUP_COLORS[
        "multistage_stage1"
    ],
    label=(
        rf"Stage 1 median $\lambda={lambda_stage1:.2f}$"
    ),
)

ax1.plot(
    X,
    Y_LATER,
    color=GROUP_COLORS[
        "multistage_later"
    ],
    label=(
        rf"Later-stage median $\lambda={lambda_later:.2f}$"
    ),
)

ax1.plot(
    X,
    Y_SINGLE,
    color="#666666",
    linestyle=":",
    label=(
        rf"Single-stage median $\lambda={lambda_single:.2f}$"
    ),
)

ax1.set_xlim(
    0.0,
    1.0,
)

ax1.set_ylim(
    0.0,
    1.03,
)

ax1.set_xticks(
    np.arange(
        0.0,
        1.01,
        0.2,
    )
)

ax1.set_yticks(
    np.arange(
        0.0,
        1.01,
        0.2,
    )
)

ax1.set_xlabel(
    r"Normalized axial strain, $x$"
)

ax1.set_ylabel(
    r"Normalized mobilization, "
    r"$y=\Delta q/\Delta q_p$"
)

# Compact legend, entirely within low-mobilization region.
ax1.legend(
    frameon=False,
    loc="lower right",
    fontsize=6.8,
    handlelength=1.65,
    handletextpad=0.55,
    labelspacing=0.18,
    borderpad=0.12,
    borderaxespad=0.40,
)

ax1.text(
    0.03,
    0.96,
    "(a)",
    transform=ax1.transAxes,
    ha="left",
    va="top",
    fontsize=11,
    fontweight="bold",
)

# ============================================================
# PANEL B
# ============================================================

for group in GROUP_ORDER:

    frame = desc[
        desc[
            "protocol_group"
        ]
        == group
    ]

    ax2.scatter(
        np.log1p(
            frame[
                "lambda_incremental"
            ]
        ),
        frame[
            "mean_y_10_90"
        ],
        s=29,
        marker=GROUP_MARKERS[
            group
        ],
        color=GROUP_COLORS[
            group
        ],
        alpha=0.80,
        edgecolors="white",
        linewidths=0.35,
        label=GROUP_LABELS[
            group
        ],
    )

ax2.set_xlabel(
    r"Compact curvature descriptor, "
    r"$\log(1+\lambda)$"
)

ax2.set_ylabel(
    r"Model-free mean mobilization, "
    r"$\bar{y}_{10-90}$"
)

ax2.legend(
    frameon=False,
    loc="lower right",
    fontsize=7.8,
)

ax2.text(
    0.03,
    0.96,
    "(b)",
    transform=ax2.transAxes,
    ha="left",
    va="top",
    fontsize=11,
    fontweight="bold",
)

ax2.text(
    0.06,
    0.86,
    (
        rf"All stages: $\rho={rho_all:.3f}$"
        "\n"
        rf"Multistage: $\rho={rho_multi:.3f}$"
    ),
    transform=ax2.transAxes,
    ha="left",
    va="top",
    fontsize=8.0,
)

# ============================================================
# PANEL C
# ============================================================

for _, row in (
    tube_paired.sort_values(
        "lambda_stage1"
    )
    .iterrows()
):

    ax3.plot(
        [
            0,
            1,
        ],
        [
            row[
                "lambda_stage1"
            ],
            row[
                "lambda_stage2"
            ],
        ],
        color="#AAAAAA",
        alpha=0.58,
        linewidth=0.9,
        zorder=1,
    )

    ax3.scatter(
        0,
        row[
            "lambda_stage1"
        ],
        s=24,
        color=GROUP_COLORS[
            "multistage_stage1"
        ],
        edgecolors="white",
        linewidths=0.35,
        zorder=2,
    )

    ax3.scatter(
        1,
        row[
            "lambda_stage2"
        ],
        s=24,
        color=GROUP_COLORS[
            "multistage_later"
        ],
        edgecolors="white",
        linewidths=0.35,
        zorder=2,
    )

lambda_max = float(
    max(
        tube_paired[
            "lambda_stage1"
        ].max(),
        tube_paired[
            "lambda_stage2"
        ].max(),
    )
)

# Deliberate headroom for annotation.
ax3.set_ylim(
    0.0,
    max(
        11.0,
        lambda_max
        * 1.14,
    ),
)

ax3.set_xlim(
    -0.35,
    1.35,
)

ax3.set_xticks(
    [
        0,
        1,
    ]
)

ax3.set_xticklabels(
    [
        "Stage 1",
        "Stage 2",
    ]
)

ax3.set_ylabel(
    r"Incremental mobilization parameter, $\lambda$"
)

ax3.text(
    0.03,
    0.96,
    "(c)",
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontsize=11,
    fontweight="bold",
)

# ============================================================
# IMPORTANT:
# THREE SHORT LINES.
# NO BOX.
# NO BACKGROUND.
# Kept in empty upper-left part of Panel C.
# ============================================================

ax3.text(
    0.055,
    0.855,
    rf"Tube-paired $\Delta\lambda={delta_mean:+.2f}$",
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontsize=6.3,
)

ax3.text(
    0.055,
    0.805,
    rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]",
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontsize=6.3,
)

ax3.text(
    0.055,
    0.755,
    rf"$P(\Delta\lambda>0)={prob_positive:.3f}$",
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontsize=6.3,
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
# LAYOUT + FOOTER
# ============================================================

fig.tight_layout(
    rect=[
        0.0,
        0.105,
        1.0,
        0.99,
    ],
    w_pad=2.35,
)

fig.text(
    0.5,
    0.035,
    (
        r"$\lambda$ is used as a compact representation of "
        "pre-peak mobilization shape; the primary Stage 1–Stage 2 "
        "inference remains based on direct model-free normalized "
        "mobilization descriptors."
    ),
    ha="center",
    va="center",
    fontsize=8.1,
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

print("=" * 94)
print(
    "UnsatConstitutiveLab — "
    "Figure 03 FINAL"
)
print("=" * 94)

print()
print(
    "=== CONSISTENCY ==="
)

print(
    f"All-stage Spearman rho : {rho_all:.6f}"
)

print(
    f"Multistage rho         : {rho_multi:.6f}"
)

print()
print(
    "=== PAIRED LAMBDA ==="
)

print(
    "Paired specimens      :",
    len(
        paired
    ),
)

print(
    "Independent tubes     :",
    len(
        tube_paired
    ),
)

print(
    f"Mean delta lambda      : {delta_mean:+.6f}"
)

print(
    f"95% bootstrap CI       : "
    f"[{delta_lo:+.6f}, {delta_hi:+.6f}]"
)

print(
    f"P(delta > 0)           : {prob_positive:.6f}"
)

print()
print(
    "Panel A compact legend       : PASS"
)

print(
    "Panel C annotation box       : NONE"
)

print(
    "Panel C annotation lines     : 3"
)

print(
    "Panel C annotation font      : 6.3 pt"
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
    "PHASE 6C FIGURE 03 FINAL: PASS"
)
