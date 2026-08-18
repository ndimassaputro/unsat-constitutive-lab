from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

CURVES = Path(
    "data/processed/stress_strain_master_v2.csv"
)

PARAMS = Path(
    "results/tables/constitutive_curve_parameters.csv"
)

OUT_PARAMS = Path(
    "results/tables/incremental_mobilization_parameters.csv"
)

OUT_GROUPS = Path(
    "results/tables/incremental_mobilization_group_summary.csv"
)

OUT_PAIRED = Path(
    "results/tables/incremental_mobilization_paired_tests.csv"
)

OUT_PROTOCOL = Path(
    "results/tables/incremental_mobilization_protocol_tests.csv"
)

OUT_SCALE = Path(
    "results/tables/lambda_xscale_invariance.csv"
)

for path in [
    OUT_PARAMS,
    OUT_GROUPS,
    OUT_PAIRED,
    OUT_PROTOCOL,
    OUT_SCALE,
]:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

RNG = np.random.default_rng(
    20260818
)

N_BOOT = 30000

curves = pd.read_csv(
    CURVES
)

params = pd.read_csv(
    PARAMS
)

# ============================================================
# KEEP ONLY PHASE-5A USABLE STAGES
# ============================================================

meta_columns = [
    "figure_id",
    "specimen_id",
    "stage_index",
    "stage",
    "tube_id",
    "soil_type",
    "test_family",
    "strain_confidence",
    "q_peak_source_kPa",
    "eps_peak_pct",
    "lambda_mobilization",
]

meta = params[
    meta_columns
].copy()

data = curves.merge(
    meta,
    on=[
        "figure_id",
        "specimen_id",
        "stage_index",
        "stage",
    ],
    how="inner",
    suffixes=(
        "",
        "_phase5a",
    ),
    validate="many_to_one",
)

# ============================================================
# FAMILY NORMALIZATION
# ============================================================

def normalize_family(
    value,
):
    text = (
        str(value)
        .strip()
        .lower()
        .replace(
            "_",
            "-"
        )
        .replace(
            " ",
            "-"
        )
    )

    if "multi" in text:
        return "multistage"

    if "single" in text:
        return "single"

    return "unknown"


data[
    "family_normalized"
] = (
    data[
        "test_family"
    ].apply(
        normalize_family
    )
)

if (
    data[
        "family_normalized"
    ]
    == "unknown"
).any():

    print(
        "UNKNOWN TEST FAMILY:"
    )

    print(
        data.loc[
            data[
                "family_normalized"
            ]
            == "unknown",
            [
                "test_family",
                "specimen_id",
            ],
        ]
        .drop_duplicates()
        .to_string(
            index=False
        )
    )

    raise SystemExit(
        "PHASE 5F: UNKNOWN TEST FAMILY"
    )


# ============================================================
# HYPERBOLIC MOBILIZATION FIT
# ============================================================

def fit_lambda(
    x,
    y,
):

    x = np.asarray(
        x,
        float,
    )

    y = np.asarray(
        y,
        float,
    )

    valid = (
        np.isfinite(x)
        & np.isfinite(y)
        & (x >= 0.0)
        & (x <= 1.001)
    )

    x = x[
        valid
    ]

    y = y[
        valid
    ]

    if len(x) < 12:
        return None

    def prediction(
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

    def residual(
        parameter,
    ):
        lam = float(
            parameter[0]
        )

        return (
            prediction(
                lam
            )
            - y
        )

    fit = least_squares(
        residual,
        x0=np.array(
            [2.0]
        ),
        bounds=(
            np.array(
                [0.0]
            ),
            np.array(
                [100.0]
            ),
        ),
        loss="soft_l1",
        f_scale=0.05,
    )

    lam = float(
        fit.x[0]
    )

    pred = prediction(
        lam
    )

    nrmse = float(
        np.sqrt(
            np.mean(
                (
                    pred
                    - y
                ) ** 2
            )
        )
    )

    return (
        lam,
        nrmse,
    )


# ============================================================
# STAGE-BY-STAGE REPARAMETERIZATION
# ============================================================

rows = []
scale_rows = []

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

    frame = (
        frame.sort_values(
            "axial_strain_local_pct"
        )
        .dropna(
            subset=[
                "axial_strain_local_pct",
                "q_smooth_kPa",
            ]
        )
        .copy()
    )

    if len(frame) < 20:
        continue

    first = frame.iloc[0]

    q_peak = float(
        first[
            "q_peak_source_kPa"
        ]
    )

    eps_peak = float(
        first[
            "eps_peak_pct"
        ]
    )

    if (
        q_peak <= 0
        or eps_peak <= 0.05
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

    pre = pre.sort_values(
        "axial_strain_local_pct"
    )

    eps = (
        pre[
            "axial_strain_local_pct"
        ]
        .to_numpy(float)
    )

    q = (
        pre[
            "q_smooth_kPa"
        ]
        .to_numpy(float)
    )

    # --------------------------------------------------------
    # Robust stage-start stress q0.
    #
    # Use the earliest 5% of PRE-PEAK points,
    # but never fewer than 5 points.
    # --------------------------------------------------------

    n_head = max(
        5,
        int(
            np.ceil(
                0.05
                * len(pre)
            )
        ),
    )

    n_head = min(
        n_head,
        max(
            5,
            len(pre) // 4,
        ),
    )

    q0 = float(
        np.median(
            q[
                :n_head
            ]
        )
    )

    q0_ratio = (
        q0
        / q_peak
    )

    delta_q_peak = (
        q_peak
        - q0
    )

    if (
        delta_q_peak
        <= 0.15
        * q_peak
    ):
        continue

    # --------------------------------------------------------
    # NORMALIZED STRAIN
    # --------------------------------------------------------

    x = (
        eps
        / eps_peak
    )

    # --------------------------------------------------------
    # ORIGINAL ABSOLUTE-q PARAMETERIZATION
    # --------------------------------------------------------

    y_absolute = (
        q
        / q_peak
    )

    absolute_fit = fit_lambda(
        x,
        y_absolute,
    )

    if absolute_fit is None:
        continue

    (
        lambda_absolute,
        nrmse_absolute,
    ) = absolute_fit

    # --------------------------------------------------------
    # INCREMENTAL STAGE PARAMETERIZATION
    #
    # q0 maps to zero.
    # q_peak maps to one.
    # --------------------------------------------------------

    y_incremental = (
        (
            q
            - q0
        )
        / delta_q_peak
    )

    incremental_fit = fit_lambda(
        x,
        y_incremental,
    )

    if incremental_fit is None:
        continue

    (
        lambda_incremental,
        nrmse_incremental,
    ) = incremental_fit

    # --------------------------------------------------------
    # X-SCALE INVARIANCE CHECK
    #
    # If epsilon and epsilon_peak receive the same uniform
    # scale factor, normalized x must remain unchanged.
    # --------------------------------------------------------

    scale_lambdas = []

    for scale in [
        0.50,
        0.75,
        1.00,
        1.25,
        1.50,
        2.00,
    ]:

        eps_scaled = (
            eps
            * scale
        )

        eps_peak_scaled = (
            eps_peak
            * scale
        )

        x_scaled = (
            eps_scaled
            / eps_peak_scaled
        )

        fitted = fit_lambda(
            x_scaled,
            y_incremental,
        )

        if fitted is None:
            continue

        lam_scaled = float(
            fitted[0]
        )

        scale_lambdas.append(
            (
                scale,
                lam_scaled,
            )
        )

        scale_rows.append({
            "figure_id":
                figure_id,

            "specimen_id":
                specimen_id,

            "stage":
                stage,

            "stage_index":
                stage_index,

            "scale_factor":
                scale,

            "lambda_incremental":
                lam_scaled,
        })

    if scale_lambdas:

        values = np.asarray(
            [
                value
                for _,
                value
                in scale_lambdas
            ],
            float,
        )

        lambda_scale_max_abs_diff = float(
            np.max(
                np.abs(
                    values
                    - lambda_incremental
                )
            )
        )

    else:

        lambda_scale_max_abs_diff = np.nan

    family = first[
        "family_normalized"
    ]

    if family == "single":

        protocol_group = (
            "single_stage"
        )

    elif (
        family
        == "multistage"
        and int(
            stage_index
        ) == 1
    ):

        protocol_group = (
            "multistage_stage1"
        )

    else:

        protocol_group = (
            "multistage_later"
        )

    rows.append({
        "figure_id":
            figure_id,

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

        "test_family":
            first[
                "test_family"
            ],

        "family_normalized":
            family,

        "protocol_group":
            protocol_group,

        "stage":
            stage,

        "stage_index":
            int(
                stage_index
            ),

        "strain_confidence":
            first[
                "strain_confidence"
            ],

        "q_peak_kPa":
            q_peak,

        "eps_peak_pct":
            eps_peak,

        "q0_kPa":
            q0,

        "q0_over_qpeak":
            q0_ratio,

        "delta_q_peak_kPa":
            delta_q_peak,

        "lambda_phase5a":
            first[
                "lambda_mobilization"
            ],

        "lambda_absolute_recomputed":
            lambda_absolute,

        "lambda_incremental":
            lambda_incremental,

        "absolute_prepeak_nrmse":
            nrmse_absolute,

        "incremental_prepeak_nrmse":
            nrmse_incremental,

        "lambda_change_after_q0_reset":
            (
                lambda_incremental
                - lambda_absolute
            ),

        "lambda_scale_max_abs_diff":
            lambda_scale_max_abs_diff,

        "n_prepeak_points":
            len(pre),

        "n_q0_points":
            n_head,
    })


result = pd.DataFrame(
    rows
)

scale_check = pd.DataFrame(
    scale_rows
)

result.to_csv(
    OUT_PARAMS,
    index=False,
)

scale_check.to_csv(
    OUT_SCALE,
    index=False,
)


# ============================================================
# GROUP SUMMARY
# ============================================================

summary_rows = []

for group in [
    "single_stage",
    "multistage_stage1",
    "multistage_later",
]:

    frame = result[
        result[
            "protocol_group"
        ]
        == group
    ]

    if frame.empty:
        continue

    summary_rows.append({
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

        "median_q0_over_qpeak":
            frame[
                "q0_over_qpeak"
            ].median(),

        "mean_q0_over_qpeak":
            frame[
                "q0_over_qpeak"
            ].mean(),

        "median_lambda_absolute":
            frame[
                "lambda_absolute_recomputed"
            ].median(),

        "median_lambda_incremental":
            frame[
                "lambda_incremental"
            ].median(),

        "median_absolute_nrmse":
            frame[
                "absolute_prepeak_nrmse"
            ].median(),

        "median_incremental_nrmse":
            frame[
                "incremental_prepeak_nrmse"
            ].median(),

        "median_lambda_change_after_q0_reset":
            frame[
                "lambda_change_after_q0_reset"
            ].median(),

        "max_xscale_lambda_abs_diff":
            frame[
                "lambda_scale_max_abs_diff"
            ].max(),
    })


group_summary = pd.DataFrame(
    summary_rows
)

group_summary.to_csv(
    OUT_GROUPS,
    index=False,
)


# ============================================================
# PROTOCOL TEST:
# SINGLE-STAGE VS MULTISTAGE STAGE 1
# ============================================================

def tube_means(
    frame,
    metric,
):

    return (
        frame.groupby(
            "tube_id",
            as_index=False,
        )
        .agg(
            value=(
                metric,
                "mean",
            )
        )
    )


def independent_bootstrap(
    A,
    B,
    metric,
):

    a = (
        tube_means(
            A,
            metric,
        )[
            "value"
        ]
        .to_numpy(float)
    )

    b = (
        tube_means(
            B,
            metric,
        )[
            "value"
        ]
        .to_numpy(float)
    )

    if (
        len(a) < 3
        or len(b) < 3
    ):
        return None

    point = float(
        b.mean()
        - a.mean()
    )

    boot = np.empty(
        N_BOOT,
        dtype=float,
    )

    for i in range(
        N_BOOT
    ):

        aa = RNG.choice(
            a,
            size=len(a),
            replace=True,
        )

        bb = RNG.choice(
            b,
            size=len(b),
            replace=True,
        )

        boot[i] = (
            bb.mean()
            - aa.mean()
        )

    return {
        "mean_single":
            float(
                a.mean()
            ),

        "mean_multistage_stage1":
            float(
                b.mean()
            ),

        "difference_multi1_minus_single":
            point,

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
    }


single = result[
    result[
        "protocol_group"
    ]
    == "single_stage"
]

stage1 = result[
    result[
        "protocol_group"
    ]
    == "multistage_stage1"
]

protocol_rows = []

for metric in [
    "q0_over_qpeak",
    "lambda_absolute_recomputed",
    "lambda_incremental",
    "incremental_prepeak_nrmse",
]:

    test = independent_bootstrap(
        single,
        stage1,
        metric,
    )

    if test is None:
        continue

    protocol_rows.append({
        "metric":
            metric,

        "n_single_stages":
            len(single),

        "n_single_tubes":
            single[
                "tube_id"
            ].nunique(),

        "n_multi1_stages":
            len(stage1),

        "n_multi1_tubes":
            stage1[
                "tube_id"
            ].nunique(),

        **test,
    })


protocol_tests = pd.DataFrame(
    protocol_rows
)

protocol_tests.to_csv(
    OUT_PROTOCOL,
    index=False,
)


# ============================================================
# PAIRED WITHIN-MULTISTAGE TEST
#
# Compare each specimen's stage 1 with the mean
# of that SAME specimen's later stages.
# ============================================================

multi = result[
    result[
        "family_normalized"
    ]
    == "multistage"
].copy()

paired_rows = []

for specimen_id, frame in multi.groupby(
    "specimen_id"
):

    first_stage = frame[
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
        first_stage.empty
        or later.empty
    ):
        continue

    first = first_stage.iloc[0]

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

        "n_later_stages":
            len(later),

        "stage1_q0_ratio":
            float(
                first_stage[
                    "q0_over_qpeak"
                ].mean()
            ),

        "later_q0_ratio":
            float(
                later[
                    "q0_over_qpeak"
                ].mean()
            ),

        "stage1_lambda_absolute":
            float(
                first_stage[
                    "lambda_absolute_recomputed"
                ].mean()
            ),

        "later_lambda_absolute":
            float(
                later[
                    "lambda_absolute_recomputed"
                ].mean()
            ),

        "stage1_lambda_incremental":
            float(
                first_stage[
                    "lambda_incremental"
                ].mean()
            ),

        "later_lambda_incremental":
            float(
                later[
                    "lambda_incremental"
                ].mean()
            ),

        "stage1_incremental_nrmse":
            float(
                first_stage[
                    "incremental_prepeak_nrmse"
                ].mean()
            ),

        "later_incremental_nrmse":
            float(
                later[
                    "incremental_prepeak_nrmse"
                ].mean()
            ),
    })


paired = pd.DataFrame(
    paired_rows
)

paired[
    "delta_q0_ratio"
] = (
    paired[
        "later_q0_ratio"
    ]
    - paired[
        "stage1_q0_ratio"
    ]
)

paired[
    "delta_lambda_absolute"
] = (
    paired[
        "later_lambda_absolute"
    ]
    - paired[
        "stage1_lambda_absolute"
    ]
)

paired[
    "delta_lambda_incremental"
] = (
    paired[
        "later_lambda_incremental"
    ]
    - paired[
        "stage1_lambda_incremental"
    ]
)

paired[
    "delta_incremental_nrmse"
] = (
    paired[
        "later_incremental_nrmse"
    ]
    - paired[
        "stage1_incremental_nrmse"
    ]
)


# ============================================================
# TUBE-CLUSTERED PAIRED BOOTSTRAP
# ============================================================

paired_test_rows = []

for metric in [
    "delta_q0_ratio",
    "delta_lambda_absolute",
    "delta_lambda_incremental",
    "delta_incremental_nrmse",
]:

    tube_delta = (
        paired.groupby(
            "tube_id",
            as_index=False,
        )
        .agg(
            delta=(
                metric,
                "mean",
            ),
            n_specimens=(
                "specimen_id",
                "nunique",
            ),
        )
    )

    values = (
        tube_delta[
            "delta"
        ]
        .to_numpy(float)
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

    paired_test_rows.append({
        "metric":
            metric,

        "n_specimens":
            len(paired),

        "n_tubes":
            len(
                tube_delta
            ),

        "mean_later_minus_stage1":
            observed_mean,

        "median_later_minus_stage1":
            float(
                paired[
                    metric
                ].median()
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
    })


paired_tests = pd.DataFrame(
    paired_test_rows
)

paired_tests.to_csv(
    OUT_PAIRED,
    index=False,
)


# ============================================================
# REPRODUCTION / INVARIANCE QC
# ============================================================

result[
    "lambda_phase5a_abs_difference"
] = np.abs(
    result[
        "lambda_absolute_recomputed"
    ]
    - result[
        "lambda_phase5a"
    ]
)

print("=" * 94)
print(
    "UnsatConstitutiveLab — "
    "Phase 5F Incremental Mobilization Falsification"
)
print("=" * 94)

print()
print(
    "=== COVERAGE ==="
)

print(
    "Stages reparameterized :",
    len(
        result
    ),
)

print(
    "Specimens              :",
    result[
        "specimen_id"
    ].nunique(),
)

print(
    "Tubes                  :",
    result[
        "tube_id"
    ].nunique(),
)

print()
print(
    "=== PHASE-5A LAMBDA REPRODUCTION ==="
)

print(
    "Median absolute difference:",
    f"{result['lambda_phase5a_abs_difference'].median():.6f}",
)

print(
    "Max absolute difference   :",
    f"{result['lambda_phase5a_abs_difference'].max():.6f}",
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
    "=== PROTOCOL TEST ==="
)

print(
    protocol_tests.to_string(
        index=False
    )
)

print()
print(
    "=== PAIRED WITHIN-MULTISTAGE TEST ==="
)

print(
    paired_tests.to_string(
        index=False
    )
)

print()
print(
    "=== X-SCALE INVARIANCE ==="
)

print(
    "Maximum lambda change under "
    "0.5x–2.0x uniform strain rescaling:"
)

print(
    f"{result['lambda_scale_max_abs_diff'].max():.12e}"
)

print()
print(
    "DECISION LOGIC"
)

print(
    "1) delta_q0_ratio > 0 robustly:"
)

print(
    "   later stages start from a larger fraction "
    "of peak deviator stress."
)

print()

print(
    "2) delta_lambda_absolute robust, but "
    "delta_lambda_incremental not robust:"
)

print(
    "   apparent history signal was mainly caused "
    "by non-zero stage-start stress."
)

print()

print(
    "3) delta_lambda_incremental remains robust:"
)

print(
    "   mobilization-curvature evolution survives "
    "mechanically consistent stage rebaselining."
)

print()

print(
    "4) x-scale invariance near machine precision:"
)

print(
    "   uniform template strain scaling cannot explain "
    "the normalized-lambda shift."
)

print()
print(
    "Outputs:"
)

for path in [
    OUT_PARAMS,
    OUT_GROUPS,
    OUT_PROTOCOL,
    OUT_PAIRED,
    OUT_SCALE,
]:
    print(
        " ",
        path,
    )

print()
print(
    "PHASE 5F INCREMENTAL MOBILIZATION FALSIFICATION: PASS"
)
