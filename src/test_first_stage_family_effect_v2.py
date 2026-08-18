from pathlib import Path

import numpy as np
import pandas as pd

PARAMS = Path(
    "results/tables/constitutive_curve_parameters.csv"
)

HISTORY_PRED = Path(
    "data/processed/history_signal_predictions.csv"
)

OUT_GROUPS = Path(
    "results/tables/first_stage_family_group_summary_v2.csv"
)

OUT_TESTS = Path(
    "results/tables/first_stage_family_bootstrap_tests_v2.csv"
)

OUT_PAIRED = Path(
    "results/tables/multistage_paired_history_tests_v2.csv"
)

OUT_LABELS = Path(
    "results/tables/test_family_label_audit.csv"
)

for path in [
    OUT_GROUPS,
    OUT_TESTS,
    OUT_PAIRED,
    OUT_LABELS,
]:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

RNG = np.random.default_rng(
    20260818
)

N_BOOT = 30000

params = pd.read_csv(
    PARAMS
)

pred = pd.read_csv(
    HISTORY_PRED
)

# ============================================================
# LABEL AUDIT
# ============================================================

label_audit = (
    params[
        "test_family"
    ]
    .astype(str)
    .value_counts(
        dropna=False
    )
    .rename_axis(
        "test_family"
    )
    .reset_index(
        name="n_stages"
    )
)

label_audit.to_csv(
    OUT_LABELS,
    index=False,
)

print("=" * 92)
print(
    "UnsatConstitutiveLab — "
    "Phase 5E-v2 Protocol + Paired History Falsification"
)
print("=" * 92)

print()
print(
    "=== TEST FAMILY LABEL AUDIT ==="
)

print(
    label_audit.to_string(
        index=False
    )
)


# ============================================================
# BASELINE MODEL
# ============================================================

base = pred[
    pred["model"]
    == "StateInteraction"
].copy()


# ============================================================
# ROBUST FAMILY NORMALIZATION
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

    while "--" in text:
        text = text.replace(
            "--",
            "-"
        )

    if (
        "multi" in text
        or "stagewise" in text
    ):
        return "multistage"

    if (
        "single" in text
        or text in {
            "ss",
            "1-stage",
            "1stage",
        }
    ):
        return "single"

    return "unknown"


base[
    "family_normalized"
] = (
    base[
        "test_family"
    ].apply(
        normalize_family
    )
)

unknown = base[
    base[
        "family_normalized"
    ]
    == "unknown"
]

if not unknown.empty:

    print()
    print(
        "UNKNOWN FAMILY LABELS:"
    )

    print(
        unknown[
            [
                "test_family",
                "specimen_id",
            ]
        ]
        .drop_duplicates()
        .to_string(
            index=False
        )
    )

    raise SystemExit(
        "PHASE 5E-v2: UNKNOWN TEST FAMILY"
    )


# ============================================================
# PROTOCOL GROUP
# ============================================================

def classify(
    row,
):

    family = row[
        "family_normalized"
    ]

    stage = int(
        row[
            "stage_index"
        ]
    )

    if family == "single":
        return (
            "single_stage"
        )

    if (
        family
        == "multistage"
        and stage == 1
    ):
        return (
            "multistage_stage1"
        )

    if (
        family
        == "multistage"
        and stage >= 2
    ):
        return (
            "multistage_later"
        )

    return "other"


base[
    "protocol_group"
] = base.apply(
    classify,
    axis=1,
)


# ============================================================
# TRANSFORMED RESIDUALS
# ============================================================

base[
    "eps_log_residual"
] = (
    np.log(
        base[
            "eps_obs"
        ]
    )
    - np.log(
        base[
            "eps_pred"
        ]
    )
)

base[
    "lambda_log_residual"
] = (
    np.log1p(
        base[
            "lambda_obs"
        ]
    )
    - np.log1p(
        np.maximum(
            base[
                "lambda_pred"
            ],
            0.0,
        )
    )
)

base[
    "joint_absolute_shape_error"
] = (
    0.5
    * np.abs(
        base[
            "eps_log_residual"
        ]
    )
    + 0.5
    * np.abs(
        base[
            "lambda_log_residual"
        ]
    )
)


# ============================================================
# GROUP SUMMARY
# ============================================================

summary_rows = []

for group_name in [
    "single_stage",
    "multistage_stage1",
    "multistage_later",
]:

    frame = base[
        base[
            "protocol_group"
        ]
        == group_name
    ]

    if frame.empty:
        continue

    summary_rows.append({
        "group":
            group_name,

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

        "median_eps_peak_pct":
            frame[
                "eps_obs"
            ].median(),

        "median_lambda":
            frame[
                "lambda_obs"
            ].median(),

        "mean_eps_log_residual":
            frame[
                "eps_log_residual"
            ].mean(),

        "mean_lambda_log_residual":
            frame[
                "lambda_log_residual"
            ].mean(),

        "median_lambda_log_residual":
            frame[
                "lambda_log_residual"
            ].median(),

        "mean_joint_abs_shape_error":
            frame[
                "joint_absolute_shape_error"
            ].mean(),

        "n_high_tick":
            int(
                (
                    frame[
                        "strain_confidence"
                    ]
                    == "high_tick_calibrated"
                ).sum()
            ),
    })


summary = pd.DataFrame(
    summary_rows
)

summary.to_csv(
    OUT_GROUPS,
    index=False,
)


# ============================================================
# INDEPENDENT CLUSTER BOOTSTRAP
#
# Used only for:
# single-stage vs multistage-stage1 protocol comparison.
#
# Tubes can overlap between source families, so we bootstrap
# tube-level means rather than individual stages.
# ============================================================

def tube_level_frame(
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


def bootstrap_independent(
    A,
    B,
    metric,
):

    A_tube = tube_level_frame(
        A,
        metric,
    )

    B_tube = tube_level_frame(
        B,
        metric,
    )

    if (
        len(A_tube) < 3
        or len(B_tube) < 3
    ):
        return None

    a = (
        A_tube[
            "value"
        ].to_numpy(float)
    )

    b = (
        B_tube[
            "value"
        ].to_numpy(float)
    )

    point = (
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
        "mean_A":
            float(
                a.mean()
            ),

        "mean_B":
            float(
                b.mean()
            ),

        "difference_B_minus_A":
            float(
                point
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

        "prob_B_greater":
            float(
                np.mean(
                    boot > 0
                )
            ),
    }


protocol_rows = []

single = base[
    base[
        "protocol_group"
    ]
    == "single_stage"
].copy()

multi1 = base[
    base[
        "protocol_group"
    ]
    == "multistage_stage1"
].copy()

for metric in [
    "eps_log_residual",
    "lambda_log_residual",
    "joint_absolute_shape_error",
]:

    result = (
        bootstrap_independent(
            single,
            multi1,
            metric,
        )
    )

    if result is None:
        continue

    protocol_rows.append({
        "comparison":
            "single_vs_multistage_stage1",

        "metric":
            metric,

        "n_single_stages":
            len(single),

        "n_single_tubes":
            single[
                "tube_id"
            ].nunique(),

        "n_multi1_stages":
            len(multi1),

        "n_multi1_tubes":
            multi1[
                "tube_id"
            ].nunique(),

        **result,
    })


protocol_tests = pd.DataFrame(
    protocol_rows
)

protocol_tests.to_csv(
    OUT_TESTS,
    index=False,
)


# ============================================================
# PAIRED WITHIN-SPECIMEN HISTORY TEST
#
# For every multistage specimen:
#
#   stage-1 residual
#          versus
#   mean residual of its own later stages
#
# This removes between-specimen offsets.
# ============================================================

multi = base[
    base[
        "family_normalized"
    ]
    == "multistage"
].copy()

paired_rows = []

for specimen_id, frame in multi.groupby(
    "specimen_id"
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

        "stage1_eps_residual":
            float(
                stage1[
                    "eps_log_residual"
                ].mean()
            ),

        "later_eps_residual":
            float(
                later[
                    "eps_log_residual"
                ].mean()
            ),

        "stage1_lambda_residual":
            float(
                stage1[
                    "lambda_log_residual"
                ].mean()
            ),

        "later_lambda_residual":
            float(
                later[
                    "lambda_log_residual"
                ].mean()
            ),

        "stage1_joint_error":
            float(
                stage1[
                    "joint_absolute_shape_error"
                ].mean()
            ),

        "later_joint_error":
            float(
                later[
                    "joint_absolute_shape_error"
                ].mean()
            ),
    })


paired = pd.DataFrame(
    paired_rows
)

for name in [
    "eps",
    "lambda",
    "joint",
]:

    paired[
        f"delta_{name}"
    ] = (
        paired[
            f"later_{name}_residual"
            if name != "joint"
            else "later_joint_error"
        ]
        - paired[
            f"stage1_{name}_residual"
            if name != "joint"
            else "stage1_joint_error"
        ]
    )


# ============================================================
# PAIRED TUBE-CLUSTER BOOTSTRAP
#
# Multiple specimens may originate from same tube.
# First average specimen deltas within tube.
# ============================================================

paired_test_rows = []

for metric in [
    "delta_eps",
    "delta_lambda",
    "delta_joint",
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
        ].to_numpy(float)
    )

    if len(values) < 3:
        continue

    observed = float(
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

        boot[i] = (
            sample.mean()
        )

    paired_test_rows.append({
        "metric":
            metric,

        "n_multistage_specimens":
            len(
                paired
            ),

        "n_tubes":
            len(
                tube_delta
            ),

        "mean_later_minus_stage1":
            observed,

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
# REPORT
# ============================================================

print()
print(
    "=== GROUP SUMMARY V2 ==="
)

print(
    summary.to_string(
        index=False
    )
)

print()
print(
    "=== PROTOCOL TEST: SINGLE VS MULTISTAGE STAGE 1 ==="
)

if protocol_tests.empty:

    print(
        "No valid protocol tests."
    )

else:

    print(
        protocol_tests.to_string(
            index=False
        )
    )

print()
print(
    "=== PAIRED WITHIN-MULTISTAGE HISTORY TEST ==="
)

print(
    paired_tests.to_string(
        index=False
    )
)

print()
print(
    "=== MULTISTAGE X-AXIS CONFIDENCE ==="
)

multi_conf = (
    multi[
        "strain_confidence"
    ]
    .value_counts()
)

print(
    multi_conf.to_string()
)

print()
print(
    "DECISION RULES"
)

print(
    "1. Protocol lambda difference already at stage 1:"
)

print(
    "   family/protocol effect exists before repeated shearing."
)

print()

print(
    "2. Paired delta_lambda CI entirely above/below zero:"
)

print(
    "   strong within-specimen evidence that later stages "
    "systematically shift mobilization curvature."
)

print()

print(
    "3. Paired eps/joint unchanged while lambda shifts:"
)

print(
    "   history effect is parameter-specific, not generic "
    "whole-shape improvement."
)

print()

print(
    "4. All multistage axes template-calibrated:"
)

print(
    "   preserve the lambda-history result as provisional "
    "until x-axis sensitivity is validated."
)

print()
print(
    "PHASE 5E-v2 PROTOCOL + PAIRED HISTORY TEST: PASS"
)
