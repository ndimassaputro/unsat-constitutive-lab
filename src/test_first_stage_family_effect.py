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
    "results/tables/first_stage_family_group_summary.csv"
)

OUT_TESTS = Path(
    "results/tables/first_stage_family_bootstrap_tests.csv"
)

OUT_RESID = Path(
    "results/tables/first_stage_family_residuals.csv"
)

for path in [
    OUT_GROUPS,
    OUT_TESTS,
    OUT_RESID,
]:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

RNG = np.random.default_rng(
    20260818
)

N_BOOT = 20000

params = pd.read_csv(
    PARAMS
)

pred = pd.read_csv(
    HISTORY_PRED
)

# ============================================================
# USE STATE-INTERACTION AS BASELINE
#
# We ask:
#
# After accounting for current:
#   sigma_net
#   suction
#   saturation
#   density
#   soil type
#
# where are the remaining shape errors located?
#
# The Stage-1 multistage group has NO prior shearing stage.
# ============================================================

base = pred[
    pred["model"]
    == "StateInteraction"
].copy()

# ------------------------------------------------------------
# Define protocol/history groups.
# ------------------------------------------------------------

def classify(row):

    family = str(
        row["test_family"]
    )

    stage_index = int(
        row["stage_index"]
    )

    if family == "single":
        return "single_stage"

    if (
        family == "multistage"
        and stage_index == 1
    ):
        return "multistage_stage1"

    if (
        family == "multistage"
        and stage_index >= 2
    ):
        return "multistage_later"

    return "other"


base["protocol_group"] = (
    base.apply(
        classify,
        axis=1,
    )
)

# ============================================================
# TRANSFORMED RESIDUALS
#
# log eps:
#   positive = model underpredicted observed peak strain
#
# log(1+lambda):
#   positive = model underpredicted observed curvature parameter
# ============================================================

base["log_eps_obs"] = np.log(
    base["eps_obs"]
)

base["log_eps_pred"] = np.log(
    base["eps_pred"]
)

base["eps_log_residual"] = (
    base["log_eps_obs"]
    - base["log_eps_pred"]
)

base["log1p_lambda_obs"] = np.log1p(
    base["lambda_obs"]
)

base["log1p_lambda_pred"] = np.log1p(
    np.maximum(
        base["lambda_pred"],
        0.0,
    )
)

base["lambda_log_residual"] = (
    base["log1p_lambda_obs"]
    - base["log1p_lambda_pred"]
)

# Joint signed summary is NOT used as the main test.
# Keep individual parameters separate.
base["joint_absolute_shape_error"] = (
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

base.to_csv(
    OUT_RESID,
    index=False,
)

# ============================================================
# GROUP SUMMARY
# ============================================================

summary_rows = []

for group_name, frame in (
    base.groupby(
        "protocol_group"
    )
):

    if group_name == "other":
        continue

    summary_rows.append({
        "group":
            group_name,

        "n_stages":
            len(frame),

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

        "median_eps_log_residual":
            frame[
                "eps_log_residual"
            ].median(),

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

        "median_joint_abs_shape_error":
            frame[
                "joint_absolute_shape_error"
            ].median(),

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
# CLUSTER BOOTSTRAP DIFFERENCE
#
# We compare mean residuals between groups.
# Resample tubes, not individual stages.
# ============================================================

def cluster_bootstrap_difference(
    frame_a,
    frame_b,
    metric,
):

    tubes_a = sorted(
        frame_a[
            "tube_id"
        ].unique()
    )

    tubes_b = sorted(
        frame_b[
            "tube_id"
        ].unique()
    )

    if (
        len(tubes_a) < 3
        or len(tubes_b) < 3
    ):
        return None

    groups_a = {
        tube:
            frame_a[
                frame_a[
                    "tube_id"
                ]
                == tube
            ][metric].to_numpy(
                float
            )
        for tube in tubes_a
    }

    groups_b = {
        tube:
            frame_b[
                frame_b[
                    "tube_id"
                ]
                == tube
            ][metric].to_numpy(
                float
            )
        for tube in tubes_b
    }

    observed_a = float(
        frame_a[
            metric
        ].mean()
    )

    observed_b = float(
        frame_b[
            metric
        ].mean()
    )

    observed_difference = (
        observed_b
        - observed_a
    )

    boot = []

    for _ in range(
        N_BOOT
    ):

        sampled_a = RNG.choice(
            tubes_a,
            size=len(
                tubes_a
            ),
            replace=True,
        )

        sampled_b = RNG.choice(
            tubes_b,
            size=len(
                tubes_b
            ),
            replace=True,
        )

        values_a = np.concatenate([
            groups_a[
                tube
            ]
            for tube in sampled_a
        ])

        values_b = np.concatenate([
            groups_b[
                tube
            ]
            for tube in sampled_b
        ])

        boot.append(
            float(
                np.mean(
                    values_b
                )
                - np.mean(
                    values_a
                )
            )
        )

    boot = np.asarray(
        boot,
        float,
    )

    return {
        "mean_A":
            observed_a,

        "mean_B":
            observed_b,

        "difference_B_minus_A":
            observed_difference,

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

        "prob_B_lower":
            float(
                np.mean(
                    boot < 0
                )
            ),
    }


# ============================================================
# THREE DECISIVE COMPARISONS
#
# 1. single vs multistage stage 1
#    -> protocol/pre-existing family effect
#
# 2. multistage stage 1 vs later stages
#    -> accumulated-stage effect
#
# 3. single vs later multistage
#    -> total family/history contrast
# ============================================================

COMPARISONS = [
    (
        "single_stage",
        "multistage_stage1",
        "protocol_test",
    ),
    (
        "multistage_stage1",
        "multistage_later",
        "within_multistage_history_test",
    ),
    (
        "single_stage",
        "multistage_later",
        "total_contrast",
    ),
]

METRICS = [
    "eps_log_residual",
    "lambda_log_residual",
    "joint_absolute_shape_error",
]

test_rows = []

for (
    group_a,
    group_b,
    comparison_name,
) in COMPARISONS:

    A = base[
        base[
            "protocol_group"
        ]
        == group_a
    ].copy()

    B = base[
        base[
            "protocol_group"
        ]
        == group_b
    ].copy()

    for metric in METRICS:

        result = (
            cluster_bootstrap_difference(
                A,
                B,
                metric,
            )
        )

        if result is None:
            continue

        test_rows.append({
            "comparison":
                comparison_name,

            "group_A":
                group_a,

            "group_B":
                group_b,

            "metric":
                metric,

            "n_A":
                len(A),

            "tubes_A":
                A[
                    "tube_id"
                ].nunique(),

            "n_B":
                len(B),

            "tubes_B":
                B[
                    "tube_id"
                ].nunique(),

            **result,
        })


tests = pd.DataFrame(
    test_rows
)


# ============================================================
# HIGH-TICK SENSITIVITY WHERE SAMPLE SIZE ALLOWS
# ============================================================

for (
    group_a,
    group_b,
    comparison_name,
) in COMPARISONS:

    A = base[
        (
            base[
                "protocol_group"
            ]
            == group_a
        )
        & (
            base[
                "strain_confidence"
            ]
            == "high_tick_calibrated"
        )
    ].copy()

    B = base[
        (
            base[
                "protocol_group"
            ]
            == group_b
        )
        & (
            base[
                "strain_confidence"
            ]
            == "high_tick_calibrated"
        )
    ].copy()

    if (
        A[
            "tube_id"
        ].nunique()
        < 3
        or B[
            "tube_id"
        ].nunique()
        < 3
    ):
        continue

    for metric in METRICS:

        result = (
            cluster_bootstrap_difference(
                A,
                B,
                metric,
            )
        )

        if result is None:
            continue

        tests = pd.concat(
            [
                tests,
                pd.DataFrame([
                    {
                        "comparison":
                            comparison_name
                            + "_high_tick",

                        "group_A":
                            group_a,

                        "group_B":
                            group_b,

                        "metric":
                            metric,

                        "n_A":
                            len(A),

                        "tubes_A":
                            A[
                                "tube_id"
                            ].nunique(),

                        "n_B":
                            len(B),

                        "tubes_B":
                            B[
                                "tube_id"
                            ].nunique(),

                        **result,
                    }
                ]),
            ],
            ignore_index=True,
        )


tests.to_csv(
    OUT_TESTS,
    index=False,
)


# ============================================================
# REPORT
# ============================================================

print("=" * 90)
print(
    "UnsatConstitutiveLab — "
    "Phase 5E First-Stage Falsification Test"
)
print("=" * 90)

print()
print(
    "=== GROUP SUMMARY ==="
)

print(
    summary.to_string(
        index=False
    )
)

print()
print(
    "=== FIRST-STAGE FALSIFICATION TESTS ==="
)

print(
    tests.to_string(
        index=False
    )
)

print()
print(
    "DECISION LOGIC"
)

print(
    "1) protocol_test significant:"
)

print(
    "   multistage stage 1 already differs from single-stage;"
)

print(
    "   do NOT interpret family effect as accumulated loading history."
)

print()

print(
    "2) within_multistage_history_test significant:"
)

print(
    "   later stages differ from multistage stage 1;"
)

print(
    "   this supports an accumulated-stage/history component."
)

print()

print(
    "3) both significant:"
)

print(
    "   protocol/family offset exists AND later loading adds another effect."
)

print()

print(
    "4) neither significant:"
)

print(
    "   previous family signal is unstable; do not build a mechanism claim."
)

print()
print(
    "Outputs:"
)

print(
    " ",
    OUT_GROUPS,
)

print(
    " ",
    OUT_TESTS,
)

print(
    " ",
    OUT_RESID,
)

print()
print(
    "PHASE 5E FIRST-STAGE FALSIFICATION: PASS"
)
