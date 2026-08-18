from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CURVES = Path(
    "data/processed/stress_strain_master_v2.csv"
)

PARAMS = Path(
    "results/tables/incremental_mobilization_parameters.csv"
)

Q0_DESC = Path(
    "results/tables/stage1_stage2_q0_sensitivity_descriptors.csv"
)

ROBUSTNESS = Path(
    "results/tables/stage1_stage2_q0_sensitivity_tests.csv"
)

OUT_DIR = Path(
    "results/figures/final"
)

OUT_PNG = OUT_DIR / (
    "figure_01_normalized_mobilization.png"
)

OUT_PDF = OUT_DIR / (
    "figure_01_normalized_mobilization.pdf"
)

OUT_DATA = Path(
    "results/tables/figure_01_curve_band.csv"
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

# Full normalized domain for publication figure.
GRID = np.linspace(
    0.0,
    1.0,
    201,
)

COLOR_STAGE1 = "#4C78A8"
COLOR_STAGE2 = "#D55E00"
COLOR_DELTA = "#2F4B7C"
COLOR_REFERENCE = "#777777"

curves = pd.read_csv(
    CURVES
)

params = pd.read_csv(
    PARAMS
)

q0_desc = pd.read_csv(
    Q0_DESC
)

robustness = pd.read_csv(
    ROBUSTNESS
)

# ============================================================
# PRIMARY q0 DEFINITION = 5% OF PEAK STRAIN
# ============================================================

q0 = q0_desc[
    np.isclose(
        q0_desc[
            "q0_fraction"
        ],
        0.05,
    )
].copy()

q0 = q0[
    q0[
        "stage_index"
    ].isin(
        [
            1,
            2,
        ]
    )
].copy()

pair_counts = (
    q0.groupby(
        "specimen_id"
    )[
        "stage_index"
    ]
    .nunique()
)

valid_specimens = (
    pair_counts[
        pair_counts == 2
    ]
    .index
    .tolist()
)

q0 = q0[
    q0[
        "specimen_id"
    ].isin(
        valid_specimens
    )
].copy()

# ============================================================
# ADD q_peak AND eps_peak
# ============================================================

meta = params[
    [
        "figure_id",
        "specimen_id",
        "stage_index",
        "q_peak_kPa",
        "eps_peak_pct",
    ]
].drop_duplicates()

q0 = q0.merge(
    meta,
    on=[
        "figure_id",
        "specimen_id",
        "stage_index",
    ],
    how="left",
    validate="one_to_one",
)

if (
    q0[
        [
            "q_peak_kPa",
            "eps_peak_pct",
        ]
    ]
    .isna()
    .any()
    .any()
):
    raise SystemExit(
        "FIGURE 01 FAIL: unresolved peak metadata."
    )

# ============================================================
# RECONSTRUCT NORMALIZED CURVES
#
# x = eps / eps_peak
#
# y = (q - q0) / (q_peak - q0)
#
# Endpoints are normalization anchors:
#
#   x = 0 -> y = 0
#   x = 1 -> y = 1
#
# Interior curve remains directly reconstructed from data.
# ============================================================

specimen_curve_rows = []

for _, row in q0.iterrows():

    frame = curves[
        (
            curves[
                "figure_id"
            ]
            == row[
                "figure_id"
            ]
        )
        & (
            curves[
                "specimen_id"
            ]
            == row[
                "specimen_id"
            ]
        )
        & (
            curves[
                "stage_index"
            ]
            == row[
                "stage_index"
            ]
        )
    ].copy()

    if frame.empty:
        continue

    frame = (
        frame.dropna(
            subset=[
                "axial_strain_local_pct",
                "q_smooth_kPa",
            ]
        )
        .sort_values(
            "axial_strain_local_pct"
        )
    )

    eps_peak = float(
        row[
            "eps_peak_pct"
        ]
    )

    q_peak = float(
        row[
            "q_peak_kPa"
        ]
    )

    q_start = float(
        row[
            "q0_kPa"
        ]
    )

    delta_q_peak = (
        q_peak
        - q_start
    )

    if (
        eps_peak <= 0
        or delta_q_peak <= 0
    ):
        continue

    frame = frame[
        frame[
            "axial_strain_local_pct"
        ]
        <= eps_peak
        + 1e-9
    ].copy()

    frame[
        "x_norm"
    ] = (
        frame[
            "axial_strain_local_pct"
        ]
        / eps_peak
    )

    frame[
        "y_norm"
    ] = (
        (
            frame[
                "q_smooth_kPa"
            ]
            - q_start
        )
        / delta_q_peak
    )

    frame = frame[
        (
            frame[
                "x_norm"
            ]
            >= -0.02
        )
        & (
            frame[
                "x_norm"
            ]
            <= 1.02
        )
    ].copy()

    frame[
        "x_round"
    ] = (
        frame[
            "x_norm"
        ].round(
            6
        )
    )

    compact = (
        frame.groupby(
            "x_round",
            as_index=False,
        )
        .agg(
            x_norm=(
                "x_norm",
                "mean",
            ),
            y_norm=(
                "y_norm",
                "median",
            ),
        )
        .sort_values(
            "x_norm"
        )
    )

    x_raw = compact[
        "x_norm"
    ].to_numpy(
        float
    )

    y_raw = compact[
        "y_norm"
    ].to_numpy(
        float
    )

    if (
        len(x_raw) < 20
        or x_raw.min() > 0.10
        or x_raw.max() < 0.90
    ):
        continue

    # --------------------------------------------------------
    # Explicit normalization endpoints.
    #
    # Do not extrapolate the digitized curve beyond its
    # reliable interior range. Instead, append the two
    # normalization-defining anchors.
    # --------------------------------------------------------

    interior = (
        (x_raw > 0.0)
        & (x_raw < 1.0)
    )

    x_augmented = np.concatenate(
        [
            np.array(
                [0.0]
            ),
            x_raw[
                interior
            ],
            np.array(
                [1.0]
            ),
        ]
    )

    y_augmented = np.concatenate(
        [
            np.array(
                [0.0]
            ),
            y_raw[
                interior
            ],
            np.array(
                [1.0]
            ),
        ]
    )

    order = np.argsort(
        x_augmented
    )

    x_augmented = (
        x_augmented[
            order
        ]
    )

    y_augmented = (
        y_augmented[
            order
        ]
    )

    y_grid = np.interp(
        GRID,
        x_augmented,
        y_augmented,
    )

    for xx, yy in zip(
        GRID,
        y_grid,
    ):

        specimen_curve_rows.append({
            "specimen_id":
                row[
                    "specimen_id"
                ],

            "tube_id":
                row[
                    "tube_id"
                ],

            "soil_type":
                row[
                    "soil_type"
                ],

            "stage_index":
                int(
                    row[
                        "stage_index"
                    ]
                ),

            "x_norm":
                xx,

            "y_norm":
                yy,
        })


specimen_curves = pd.DataFrame(
    specimen_curve_rows
)

# ============================================================
# STRICT COVERAGE QC
# ============================================================

coverage = (
    specimen_curves[
        [
            "specimen_id",
            "stage_index",
        ]
    ]
    .drop_duplicates()
)

coverage_count = (
    coverage.groupby(
        "specimen_id"
    )[
        "stage_index"
    ]
    .nunique()
)

complete_specimens = (
    coverage_count[
        coverage_count == 2
    ]
    .index
)

specimen_curves = specimen_curves[
    specimen_curves[
        "specimen_id"
    ].isin(
        complete_specimens
    )
].copy()

n_specimens = len(
    complete_specimens
)

n_tubes = (
    specimen_curves[
        "tube_id"
    ]
    .nunique()
)

if n_specimens != 25:

    raise SystemExit(
        "FIGURE 01 FAIL: "
        f"expected 25 paired specimens, found {n_specimens}."
    )

if n_tubes != 18:

    raise SystemExit(
        "FIGURE 01 FAIL: "
        f"expected 18 independent tubes, found {n_tubes}."
    )

# ============================================================
# TUBE-LEVEL AVERAGING
# ============================================================

tube_curves = (
    specimen_curves.groupby(
        [
            "tube_id",
            "stage_index",
            "x_norm",
        ],
        as_index=False,
    )
    .agg(
        y_norm=(
            "y_norm",
            "mean",
        )
    )
)

tube_arrays = {}

for tube_id, frame in tube_curves.groupby(
    "tube_id"
):

    stage1 = (
        frame[
            frame[
                "stage_index"
            ]
            == 1
        ]
        .sort_values(
            "x_norm"
        )
    )

    stage2 = (
        frame[
            frame[
                "stage_index"
            ]
            == 2
        ]
        .sort_values(
            "x_norm"
        )
    )

    if (
        len(stage1) != len(GRID)
        or len(stage2) != len(GRID)
    ):
        continue

    tube_arrays[
        tube_id
    ] = {
        "stage1":
            stage1[
                "y_norm"
            ].to_numpy(
                float
            ),

        "stage2":
            stage2[
                "y_norm"
            ].to_numpy(
                float
            ),
    }


tubes = sorted(
    tube_arrays.keys()
)

if len(tubes) != 18:

    raise SystemExit(
        "FIGURE 01 FAIL: "
        f"expected 18 paired tube curves, found {len(tubes)}."
    )

Y1 = np.vstack(
    [
        tube_arrays[
            tube
        ][
            "stage1"
        ]
        for tube in tubes
    ]
)

Y2 = np.vstack(
    [
        tube_arrays[
            tube
        ][
            "stage2"
        ]
        for tube in tubes
    ]
)

DELTA = (
    Y2
    - Y1
)

# ============================================================
# TUBE-CLUSTER BOOTSTRAP
# ============================================================

boot_stage1 = np.empty(
    (
        N_BOOT,
        len(GRID),
    ),
    dtype=np.float32,
)

boot_stage2 = np.empty(
    (
        N_BOOT,
        len(GRID),
    ),
    dtype=np.float32,
)

boot_delta = np.empty(
    (
        N_BOOT,
        len(GRID),
    ),
    dtype=np.float32,
)

for i in range(
    N_BOOT
):

    indices = RNG.integers(
        0,
        len(tubes),
        size=len(tubes),
    )

    b1 = Y1[
        indices
    ].mean(
        axis=0
    )

    b2 = Y2[
        indices
    ].mean(
        axis=0
    )

    boot_stage1[
        i
    ] = b1

    boot_stage2[
        i
    ] = b2

    boot_delta[
        i
    ] = (
        b2
        - b1
    )


stage1_mean = Y1.mean(
    axis=0
)

stage2_mean = Y2.mean(
    axis=0
)

delta_mean = DELTA.mean(
    axis=0
)

stage1_lo = np.quantile(
    boot_stage1,
    0.025,
    axis=0,
)

stage1_hi = np.quantile(
    boot_stage1,
    0.975,
    axis=0,
)

stage2_lo = np.quantile(
    boot_stage2,
    0.025,
    axis=0,
)

stage2_hi = np.quantile(
    boot_stage2,
    0.975,
    axis=0,
)

delta_lo = np.quantile(
    boot_delta,
    0.025,
    axis=0,
)

delta_hi = np.quantile(
    boot_delta,
    0.975,
    axis=0,
)

# ============================================================
# SAVE FIGURE DATA
# ============================================================

figure_data = pd.DataFrame({
    "x_norm":
        GRID,

    "stage1_mean":
        stage1_mean,

    "stage1_p025":
        stage1_lo,

    "stage1_p975":
        stage1_hi,

    "stage2_mean":
        stage2_mean,

    "stage2_p025":
        stage2_lo,

    "stage2_p975":
        stage2_hi,

    "delta_mean":
        delta_mean,

    "delta_p025":
        delta_lo,

    "delta_p975":
        delta_hi,
})

figure_data.to_csv(
    OUT_DATA,
    index=False,
)

# ============================================================
# LOCKED EFFECT-SIZE TABLE
# ============================================================

effect = robustness[
    np.isclose(
        robustness[
            "q0_fraction"
        ],
        0.05,
    )
].copy()

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

effect = (
    effect.set_index(
        "metric"
    )
    .loc[
        metric_order
    ]
    .reset_index()
)

# ============================================================
# QC
# ============================================================

print("=" * 88)
print(
    "UnsatConstitutiveLab — "
    "Figure 01 Normalized Mobilization V2"
)
print("=" * 88)

print()
print(
    "=== COVERAGE ==="
)

print(
    "Paired specimens :",
    n_specimens,
)

print(
    "Independent tubes:",
    n_tubes,
)

print(
    "Displayed x-range : 0.0 to 1.0"
)

print(
    "Normalization     : "
    "(0,0) stage start; (1,1) stage peak"
)

print()
print(
    "=== LOCKED EFFECT SIZES ==="
)

print(
    effect[
        [
            "metric",
            "mean_delta",
            "bootstrap_p025",
            "bootstrap_p975",
            "fraction_specimens_positive",
        ]
    ].to_string(
        index=False
    )
)

# Interior values must still reproduce locked analysis.
for metric, x_target in [
    (
        "y25",
        0.25,
    ),
    (
        "y50",
        0.50,
    ),
    (
        "y75",
        0.75,
    ),
]:

    j = int(
        np.argmin(
            np.abs(
                GRID
                - x_target
            )
        )
    )

    curve_value = float(
        delta_mean[
            j
        ]
    )

    locked_value = float(
        effect.loc[
            effect[
                "metric"
            ]
            == metric,
            "mean_delta",
        ].iloc[0]
    )

    difference = abs(
        curve_value
        - locked_value
    )

    print(
        f"{metric} curve-vs-locked difference:"
        f" {difference:.6f}"
    )

    if difference > 0.015:

        raise SystemExit(
            "FIGURE 01 FAIL: "
            f"{metric} reconstruction mismatch."
        )

# Endpoint invariance.
if not (
    np.allclose(
        Y1[
            :,
            0
        ],
        0.0,
    )
    and np.allclose(
        Y2[
            :,
            0
        ],
        0.0,
    )
    and np.allclose(
        Y1[
            :,
            -1
        ],
        1.0,
    )
    and np.allclose(
        Y2[
            :,
            -1
        ],
        1.0,
    )
):

    raise SystemExit(
        "FIGURE 01 FAIL: endpoint normalization failed."
    )

# ============================================================
# PUBLICATION STYLE
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
        1.8,

    "pdf.fonttype":
        42,

    "ps.fonttype":
        42,
})

fig, axes = plt.subplots(
    1,
    3,
    figsize=(
        10.8,
        3.55,
    ),
)

ax1, ax2, ax3 = axes

# ============================================================
# PANEL A
# ============================================================

ax1.fill_between(
    GRID,
    stage1_lo,
    stage1_hi,
    color=COLOR_STAGE1,
    alpha=0.16,
    linewidth=0,
)

ax1.fill_between(
    GRID,
    stage2_lo,
    stage2_hi,
    color=COLOR_STAGE2,
    alpha=0.16,
    linewidth=0,
)

ax1.plot(
    GRID,
    stage1_mean,
    color=COLOR_STAGE1,
    label="Stage 1",
)

ax1.plot(
    GRID,
    stage2_mean,
    color=COLOR_STAGE2,
    label="Stage 2",
)

ax1.plot(
    GRID,
    GRID,
    color=COLOR_REFERENCE,
    linestyle="--",
    linewidth=1.0,
    alpha=0.75,
    label=r"Linear reference $y=x$",
)

ax1.set_xlim(
    0.0,
    1.0,
)

ax1.set_ylim(
    0.0,
    1.05,
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
    r"Normalized axial strain, "
    r"$x=\varepsilon_a/\varepsilon_{a,p}$"
)

ax1.set_ylabel(
    r"Normalized stress mobilization, "
    r"$y=(q-q_0)/(q_p-q_0)$"
)

ax1.legend(
    frameon=False,
    loc="lower right",
)

ax1.text(
    0.02,
    0.96,
    "(a)",
    transform=ax1.transAxes,
    ha="left",
    va="top",
    fontweight="bold",
)

# ============================================================
# PANEL B
# ============================================================

ax2.fill_between(
    GRID,
    delta_lo,
    delta_hi,
    color=COLOR_DELTA,
    alpha=0.18,
    linewidth=0,
)

ax2.plot(
    GRID,
    delta_mean,
    color=COLOR_DELTA,
)

ax2.axhline(
    0.0,
    color=COLOR_REFERENCE,
    linestyle="--",
    linewidth=1.0,
)

ax2.set_xlim(
    0.0,
    1.0,
)

# Slight negative margin so y=0 is visible inside the frame.
ax2.set_ylim(
    -0.01,
    max(
        0.23,
        float(
            np.max(
                delta_hi
            )
            * 1.05
        ),
    ),
)

ax2.set_xticks(
    np.arange(
        0.0,
        1.01,
        0.2,
    )
)

ax2.set_xlabel(
    r"Normalized axial strain, $x$"
)

ax2.set_ylabel(
    r"Paired mobilization shift, "
    r"$\Delta y=y_2-y_1$"
)

ax2.text(
    0.02,
    0.96,
    "(b)",
    transform=ax2.transAxes,
    ha="left",
    va="top",
    fontweight="bold",
)

ax2.text(
    0.97,
    0.05,
    "95% tube-cluster\nbootstrap band",
    transform=ax2.transAxes,
    ha="right",
    va="bottom",
    fontsize=8,
)

# ============================================================
# PANEL C
# ============================================================

positions = np.arange(
    len(
        effect
    )
)

means = (
    effect[
        "mean_delta"
    ].to_numpy(float)
)

lower = (
    means
    - effect[
        "bootstrap_p025"
    ].to_numpy(float)
)

upper = (
    effect[
        "bootstrap_p975"
    ].to_numpy(float)
    - means
)

ax3.errorbar(
    means,
    positions,
    xerr=np.vstack(
        [
            lower,
            upper,
        ]
    ),
    fmt="o",
    color=COLOR_DELTA,
    ecolor=COLOR_DELTA,
    elinewidth=1.4,
    capsize=3.5,
    markersize=5.5,
)

ax3.axvline(
    0.0,
    color=COLOR_REFERENCE,
    linestyle="--",
    linewidth=1.0,
)

ax3.set_yticks(
    positions
)

ax3.set_yticklabels(
    [
        metric_labels[
            metric
        ]
        for metric in effect[
            "metric"
        ]
    ]
)

ax3.invert_yaxis()

ax3.set_xlim(
    -0.01,
    0.22,
)

ax3.set_xlabel(
    r"Stage 2 $-$ Stage 1"
)

ax3.set_ylabel(
    "Direct mobilization descriptor"
)

ax3.text(
    0.02,
    0.96,
    "(c)",
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontweight="bold",
)

# ============================================================
# FULL BOXED ENGINEERING AXES
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

fig.text(
    0.5,
    0.01,
    (
        "25 paired specimens from 18 independent tubes; "
        r"primary $q_0$ estimated over "
        r"$\varepsilon_a \leq 0.05\,\varepsilon_{a,p}$"
    ),
    ha="center",
    va="bottom",
    fontsize=8.5,
)

fig.tight_layout(
    rect=[
        0.0,
        0.055,
        1.0,
        1.0,
    ],
    w_pad=2.1,
)

fig.savefig(
    OUT_PNG,
    dpi=600,
    bbox_inches="tight",
)

fig.savefig(
    OUT_PDF,
    bbox_inches="tight",
)

plt.close(
    fig
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

print(
    "Figure data:",
    OUT_DATA,
)

print()
print(
    "PHASE 6A FIGURE 01 V2: PASS"
)
