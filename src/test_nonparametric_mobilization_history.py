from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

CURVES = Path(
    "data/processed/stress_strain_master_v2.csv"
)

PARAMS = Path(
    "results/tables/incremental_mobilization_parameters.csv"
)

OUT_DESC = Path(
    "results/tables/nonparametric_mobilization_descriptors.csv"
)

OUT_GROUP = Path(
    "results/tables/nonparametric_mobilization_group_summary.csv"
)

OUT_STAGE = Path(
    "results/tables/nonparametric_mobilization_stage_summary.csv"
)

OUT_PAIRED = Path(
    "results/tables/nonparametric_mobilization_paired_tests.csv"
)

OUT_CORR = Path(
    "results/tables/lambda_nonparametric_consistency.csv"
)

for path in [
    OUT_DESC,
    OUT_GROUP,
    OUT_STAGE,
    OUT_PAIRED,
    OUT_CORR,
]:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

RNG = np.random.default_rng(
    20260818
)

N_BOOT = 50000

curves = pd.read_csv(
    CURVES
)

params = pd.read_csv(
    PARAMS
)

# ============================================================
# MERGE ONLY THE 84 REPARAMETERIZED / USABLE STAGES
# ============================================================

meta_cols = [
    "figure_id",
    "specimen_id",
    "stage_index",
    "stage",
    "tube_id",
    "soil_type",
    "family_normalized",
    "protocol_group",
    "strain_confidence",
    "q_peak_kPa",
    "eps_peak_pct",
    "q0_kPa",
    "q0_over_qpeak",
    "lambda_absolute_recomputed",
    "lambda_incremental",
    "incremental_prepeak_nrmse",
]

data = curves.merge(
    params[
        meta_cols
    ],
    on=[
        "figure_id",
        "specimen_id",
        "stage_index",
        "stage",
    ],
    how="inner",
    validate="many_to_one",
)

# ============================================================
# NONPARAMETRIC DESCRIPTORS
#
# x = eps / eps_peak
# y = (q - q0) / (q_peak - q0)
#
# No constitutive equation is fitted here.
#
# y25:
#   fraction of peak stress increment mobilized
#   at 25% of peak strain.
#
# Larger y25/y50/y75 = earlier/faster mobilization.
#
# mean_y_10_90:
#   average normalized mobilization over
#   x = 0.10 ... 0.90.
# ============================================================

TARGET_X = [
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
]

GRID = np.linspace(
    0.10,
    0.90,
    161,
)

descriptor_rows = []

group_cols = [
    "figure_id",
    "specimen_id",
    "stage_index",
    "stage",
]

for keys, frame in data.groupby(
    group_cols,
    sort=False,
):

    (
        figure_id,
        specimen_id,
        stage_index,
        stage,
    ) = keys

    first = frame.iloc[0]

    q_peak = float(
        first[
            "q_peak_kPa"
        ]
    )

    q0 = float(
        first[
            "q0_kPa"
        ]
    )

    eps_peak = float(
        first[
            "eps_peak_pct"
        ]
    )

    delta_q_peak = (
        q_peak
        - q0
    )

    if (
        delta_q_peak <= 0
        or eps_peak <= 0
    ):
        continue

    pre = frame[
        frame[
            "axial_strain_local_pct"
        ]
        <= eps_peak
        + 1e-9
    ].copy()

    if len(pre) < 20:
        continue

    pre[
        "x_norm"
    ] = (
        pre[
            "axial_strain_local_pct"
        ]
        / eps_peak
    )

    pre[
        "y_norm"
    ] = (
        (
            pre[
                "q_smooth_kPa"
            ]
            - q0
        )
        / delta_q_peak
    )

    pre = pre[
        np.isfinite(
            pre[
                "x_norm"
            ]
        )
        & np.isfinite(
            pre[
                "y_norm"
            ]
        )
        & (
            pre[
                "x_norm"
            ]
            >= -0.02
        )
        & (
            pre[
                "x_norm"
            ]
            <= 1.02
        )
    ].copy()

    if len(pre) < 20:
        continue

    # Collapse duplicate x positions.
    pre[
        "x_round"
    ] = (
        pre[
            "x_norm"
        ].round(
            6
        )
    )

    curve = (
        pre.groupby(
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

    x = (
        curve[
            "x_norm"
        ]
        .to_numpy(float)
    )

    y = (
        curve[
            "y_norm"
        ]
        .to_numpy(float)
    )

    # Require enough observed coverage.
    if (
        x.min() > 0.10
        or x.max() < 0.90
    ):
        continue

    values = {}

    for target in TARGET_X:

        values[
            target
        ] = float(
            np.interp(
                target,
                x,
                y,
            )
        )

    y_grid = np.interp(
        GRID,
        x,
        y,
    )

    mean_y = float(
        np.mean(
            y_grid
        )
    )

    partial_auc = float(
        np.trapezoid(
            y_grid,
            GRID,
        )
    )

    # A straight-line mobilization y=x has
    # mean value 0.5 over 0.1 <= x <= 0.9.
    mobilization_excess = (
        mean_y
        - 0.5
    )

    descriptor_rows.append({
        "figure_id":
            figure_id,

        "specimen_id":
            specimen_id,

        "stage_index":
            int(
                stage_index
            ),

        "stage":
            stage,

        "tube_id":
            first[
                "tube_id"
            ],

        "soil_type":
            first[
                "soil_type"
            ],

        "family_normalized":
            first[
                "family_normalized"
            ],

        "protocol_group":
            first[
                "protocol_group"
            ],

        "strain_confidence":
            first[
                "strain_confidence"
            ],

        "q0_over_qpeak":
            first[
                "q0_over_qpeak"
            ],

        "lambda_incremental":
            first[
                "lambda_incremental"
            ],

        "incremental_prepeak_nrmse":
            first[
                "incremental_prepeak_nrmse"
            ],

        "y10":
            values[
                0.10
            ],

        "y25":
            values[
                0.25
            ],

        "y50":
            values[
                0.50
            ],

        "y75":
            values[
                0.75
            ],

        "y90":
            values[
                0.90
            ],

        "mean_y_10_90":
            mean_y,

        "partial_auc_10_90":
            partial_auc,

        "mobilization_excess":
            mobilization_excess,

        "n_prepeak_points":
            len(
                curve
            ),
    })


desc = pd.DataFrame(
    descriptor_rows
)

desc.to_csv(
    OUT_DESC,
    index=False,
)

# ============================================================
# COVERAGE CHECK
# ============================================================

if len(desc) < 75:

    raise SystemExit(
        "PHASE 5G FAIL: "
        f"only {len(desc)} stages have adequate normalized coverage."
    )

# ============================================================
# GROUP SUMMARY
# ============================================================

DESCRIPTORS = [
    "y25",
    "y50",
    "y75",
    "mean_y_10_90",
    "mobilization_excess",
]

group_rows = []

for group in [
    "single_stage",
    "multistage_stage1",
    "multistage_later",
]:

    frame = desc[
        desc[
            "protocol_group"
        ]
        == group
    ]

    if frame.empty:
        continue

    row = {
        "group":
            group,

        "n_stages":
            len(frame),

        "n_specimens":
            frame[
                "specimen_id"
            ].nunique(),

        "n_tubes":
            frame[
                "tube_id"
            ].nunique(),

        "median_lambda_incremental":
            frame[
                "lambda_incremental"
            ].median(),

        "median_incremental_nrmse":
            frame[
                "incremental_prepeak_nrmse"
            ].median(),
    }

    for metric in DESCRIPTORS:

        row[
            f"median_{metric}"
        ] = (
            frame[
                metric
            ].median()
        )

        row[
            f"mean_{metric}"
        ] = (
            frame[
                metric
            ].mean()
        )

    group_rows.append(
        row
    )


group_summary = pd.DataFrame(
    group_rows
)

group_summary.to_csv(
    OUT_GROUP,
    index=False,
)

# ============================================================
# MULTISTAGE SUMMARY BY ORDINAL STAGE
#
# Descriptive only.
# We do NOT treat shrinking stage-3/4 sample sizes as
# independent evidence.
# ============================================================

multi = desc[
    desc[
        "family_normalized"
    ]
    == "multistage"
].copy()

stage_rows = []

for stage_index, frame in (
    multi.groupby(
        "stage_index"
    )
):

    row = {
        "stage_index":
            int(
                stage_index
            ),

        "n_stages":
            len(frame),

        "n_specimens":
            frame[
                "specimen_id"
            ].nunique(),

        "n_tubes":
            frame[
                "tube_id"
            ].nunique(),

        "median_lambda_incremental":
            frame[
                "lambda_incremental"
            ].median(),
    }

    for metric in DESCRIPTORS:

        row[
            f"median_{metric}"
        ] = (
            frame[
                metric
            ].median()
        )

    stage_rows.append(
        row
    )


stage_summary = pd.DataFrame(
    stage_rows
)

stage_summary.to_csv(
    OUT_STAGE,
    index=False,
)

# ============================================================
# PAIRED WITHIN-SPECIMEN DELTAS
#
# Each multistage specimen:
#
#     stage 1
#        versus
#     mean of its OWN later stages
#
# Then average specimens belonging to the same tube before
# bootstrap resampling.
# ============================================================

paired_rows = []

for specimen_id, frame in (
    multi.groupby(
        "specimen_id"
    )
):

    stage1 = frame[
        frame[
            "stage_index"
        ]
        == 1
    ]

    later = frame[
        frame[
            "stage_index"
        ]
        >= 2
    ]

    if (
        stage1.empty
        or later.empty
    ):
        continue

    first = stage1.iloc[0]

    row = {
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

        "n_later_stages":
            len(later),
    }

    for metric in DESCRIPTORS:

        stage1_value = float(
            stage1[
                metric
            ].mean()
        )

        later_value = float(
            later[
                metric
            ].mean()
        )

        row[
            f"stage1_{metric}"
        ] = stage1_value

        row[
            f"later_{metric}"
        ] = later_value

        row[
            f"delta_{metric}"
        ] = (
            later_value
            - stage1_value
        )

    paired_rows.append(
        row
    )


paired = pd.DataFrame(
    paired_rows
)

# ============================================================
# TUBE-CLUSTERED BOOTSTRAP
# ============================================================

test_rows = []

for metric in DESCRIPTORS:

    delta_col = (
        f"delta_{metric}"
    )

    tube = (
        paired.groupby(
            "tube_id",
            as_index=False,
        )
        .agg(
            delta=(
                delta_col,
                "mean",
            ),
            n_specimens=(
                "specimen_id",
                "nunique",
            ),
        )
    )

    values = (
        tube[
            "delta"
        ].to_numpy(float)
    )

    if len(values) < 3:
        continue

    observed_mean = float(
        values.mean()
    )

    boot = np.empty(
        N_BOOT,
        dtype=float,
    )

    for i in range(
        N_BOOT
    ):

        sample = RNG.choice(
            values,
            size=len(values),
            replace=True,
        )

        boot[i] = float(
            sample.mean()
        )

    specimen_delta = (
        paired[
            delta_col
        ].to_numpy(float)
    )

    test_rows.append({
        "metric":
            metric,

        "n_specimens":
            len(
                paired
            ),

        "n_tubes":
            len(
                tube
            ),

        "mean_later_minus_stage1":
            observed_mean,

        "median_later_minus_stage1":
            float(
                np.median(
                    specimen_delta
                )
            ),

        "bootstrap_p025":
            float(
                np.quantile(
                    boot,
                    0.025,
                )
            ),

        "bootstrap_p975":
            float(
                np.quantile(
                    boot,
                    0.975,
                )
            ),

        "prob_positive":
            float(
                np.mean(
                    boot > 0
                )
            ),

        "prob_negative":
            float(
                np.mean(
                    boot < 0
                )
            ),

        "fraction_specimens_positive":
            float(
                np.mean(
                    specimen_delta > 0
                )
            ),

        "fraction_specimens_negative":
            float(
                np.mean(
                    specimen_delta < 0
                )
            ),
    })


paired_tests = pd.DataFrame(
    test_rows
)

paired_tests.to_csv(
    OUT_PAIRED,
    index=False,
)

# ============================================================
# DOES LAMBDA TRACK THE DIRECT, MODEL-FREE SHAPE?
#
# If lambda is meaningful, it should correlate strongly with
# y25/y50/AUC-like descriptors.
# ============================================================

corr_rows = []

for subset_name, frame in [
    (
        "all",
        desc,
    ),
    (
        "multistage_only",
        multi,
    ),
]:

    for metric in [
        "y25",
        "y50",
        "y75",
        "mean_y_10_90",
    ]:

        rho, pvalue = spearmanr(
            frame[
                "lambda_incremental"
            ],
            frame[
                metric
            ],
            nan_policy="omit",
        )

        corr_rows.append({
            "subset":
                subset_name,

            "metric":
                metric,

            "n_stages":
                len(frame),

            "spearman_rho":
                float(
                    rho
                ),

            "pvalue":
                float(
                    pvalue
                ),
        })


correlations = pd.DataFrame(
    corr_rows
)

correlations.to_csv(
    OUT_CORR,
    index=False,
)

# ============================================================
# REPORT
# ============================================================

print("=" * 94)
print(
    "UnsatConstitutiveLab — "
    "Phase 5G Nonparametric Mobilization Falsification"
)
print("=" * 94)

print()
print(
    "=== COVERAGE ==="
)

print(
    "Normalized stages :",
    len(
        desc
    ),
)

print(
    "Specimens         :",
    desc[
        "specimen_id"
    ].nunique(),
)

print(
    "Tubes             :",
    desc[
        "tube_id"
    ].nunique(),
)

print()
print(
    "=== GROUP SUMMARY ==="
)

print(
    group_summary.to_string(
        index=False
    )
)

print()
print(
    "=== MULTISTAGE BY STAGE ==="
)

print(
    stage_summary.to_string(
        index=False
    )
)

print()
print(
    "=== MODEL-FREE PAIRED HISTORY TEST ==="
)

print(
    paired_tests.to_string(
        index=False
    )
)

print()
print(
    "=== LAMBDA VS DIRECT SHAPE CONSISTENCY ==="
)

print(
    correlations.to_string(
        index=False
    )
)

print()
print(
    "DECISION LOGIC"
)

print(
    "If delta_y25/y50/y75 and delta_mean_y_10_90 "
    "are robustly positive:"
)

print(
    "  later stages directly mobilize a larger fraction "
    "of their peak stress at the same normalized strain."
)

print()

print(
    "This conclusion does NOT depend on the hyperbolic "
    "lambda parameter."
)

print()

print(
    "If lambda also correlates strongly with these direct "
    "descriptors, lambda is a compact representation of "
    "a shape shift already visible in the reconstructed data."
)

print()

print(
    "If the direct descriptors show no paired shift:"
)

print(
    "  reject lambda-history as a model-dependent artifact."
)

print()
print(
    "Outputs:"
)

for path in [
    OUT_DESC,
    OUT_GROUP,
    OUT_STAGE,
    OUT_PAIRED,
    OUT_CORR,
]:
    print(
        " ",
        path,
    )

print()
print(
    "PHASE 5G NONPARAMETRIC MOBILIZATION FALSIFICATION: PASS"
)
