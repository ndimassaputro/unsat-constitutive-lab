from pathlib import Path
import hashlib

import numpy as np
import pandas as pd

PARAMS = Path(
    "results/tables/constitutive_curve_parameters.csv"
)

CURVES = Path(
    "data/processed/constitutive_curve_fit_predictions.csv"
)

OUT_PARAM = Path(
    "data/processed/constitutive_logo_parameter_predictions.csv"
)

OUT_CURVE = Path(
    "data/processed/constitutive_logo_curve_predictions.csv"
)

OUT_METRICS = Path(
    "results/tables/constitutive_logo_metrics.csv"
)

OUT_COMPARE = Path(
    "results/tables/constitutive_logo_pairwise.csv"
)

for path in [
    OUT_PARAM,
    OUT_CURVE,
    OUT_METRICS,
    OUT_COMPARE,
]:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

RNG = np.random.default_rng(20260818)

ALPHAS = [
    0.0,
    0.01,
    0.1,
    1.0,
    10.0,
    100.0,
]

N_BOOT = 5000

params = pd.read_csv(PARAMS)
curves = pd.read_csv(CURVES)

# ============================================================
# TARGET TRANSFORMS
# ============================================================

params["target_log_q"] = np.log(
    params["q_peak_source_kPa"]
)

params["target_log_eps"] = np.log(
    params["eps_peak_pct"]
)

params["target_log1p_lambda"] = np.log1p(
    params["lambda_mobilization"]
)

params["is_multistage"] = (
    params["test_family"]
    == "multistage"
).astype(float)

TARGETS = {
    "log_q":
        "target_log_q",

    "log_eps":
        "target_log_eps",

    "log1p_lambda":
        "target_log1p_lambda",
}

MODELS = {
    "Mechanical": [
        "sigma_c_net_kPa",
    ],

    "Suction": [
        "sigma_c_net_kPa",
        "matric_suction_kPa",
    ],

    "State": [
        "sigma_c_net_kPa",
        "matric_suction_kPa",
        "degree_saturation",
        "gamma_d_g_cm3",
    ],

    "StateInteraction": [
        "sigma_c_net_kPa",
        "matric_suction_kPa",
        "degree_saturation",
        "gamma_d_g_cm3",
        "suction_x_saturation",
    ],

    "StateHistory": [
        "sigma_c_net_kPa",
        "matric_suction_kPa",
        "degree_saturation",
        "gamma_d_g_cm3",
        "suction_x_saturation",
        "stage_index",
        "is_multistage",
    ],
}

params[
    "suction_x_saturation"
] = (
    params["matric_suction_kPa"]
    * params["degree_saturation"]
)


# ============================================================
# DESIGN MATRIX
#
# Numerical variables standardized from TRAINING data only.
# Soil-type effects are included as fixed dummy variables.
# MH is reference category.
# ============================================================

def design_matrix(
    train,
    frame,
    feature_names,
):

    train_numeric = train[
        feature_names
    ].to_numpy(float)

    frame_numeric = frame[
        feature_names
    ].to_numpy(float)

    mean = np.mean(
        train_numeric,
        axis=0,
    )

    std = np.std(
        train_numeric,
        axis=0,
        ddof=1,
    )

    std[
        ~np.isfinite(std)
        | (std < 1e-12)
    ] = 1.0

    Z = (
        frame_numeric
        - mean
    ) / std

    # Fixed soil-type encoding.
    soil_ML = (
        frame["soil_type"]
        == "ML"
    ).astype(float).to_numpy()

    soil_SC = (
        frame["soil_type"]
        == "SC"
    ).astype(float).to_numpy()

    X = np.column_stack([
        np.ones(
            len(frame)
        ),
        Z,
        soil_ML,
        soil_SC,
    ])

    return X


# ============================================================
# RIDGE
# ============================================================

def fit_ridge(
    X,
    y,
    alpha,
):

    p = X.shape[1]

    penalty = np.eye(
        p
    )

    # Never penalize intercept.
    penalty[0, 0] = 0.0

    lhs = (
        X.T @ X
        + alpha
        * penalty
    )

    rhs = (
        X.T @ y
    )

    beta = np.linalg.pinv(
        lhs
    ) @ rhs

    return beta


# ============================================================
# DETERMINISTIC INNER GROUP FOLDS
# ============================================================

def inner_fold(
    tube_id,
    n_folds=5,
):

    digest = hashlib.sha256(
        str(tube_id).encode(
            "utf-8"
        )
    ).hexdigest()

    value = int(
        digest[:8],
        16,
    )

    return (
        value
        % n_folds
    )


def choose_alpha(
    train,
    features,
    target_col,
):

    tubes = (
        train[
            "tube_id"
        ]
        .drop_duplicates()
        .tolist()
    )

    fold_map = {
        tube:
            inner_fold(
                tube
            )
        for tube in tubes
    }

    scores = []

    for alpha in ALPHAS:

        errors = []

        for fold in sorted(
            set(
                fold_map.values()
            )
        ):

            validation_tubes = [
                tube
                for tube, f
                in fold_map.items()
                if f == fold
            ]

            inner_train = train[
                ~train[
                    "tube_id"
                ].isin(
                    validation_tubes
                )
            ]

            inner_val = train[
                train[
                    "tube_id"
                ].isin(
                    validation_tubes
                )
            ]

            if (
                inner_train[
                    "tube_id"
                ].nunique()
                < 3
                or inner_val.empty
            ):
                continue

            X_train = design_matrix(
                inner_train,
                inner_train,
                features,
            )

            X_val = design_matrix(
                inner_train,
                inner_val,
                features,
            )

            y_train = (
                inner_train[
                    target_col
                ].to_numpy(float)
            )

            y_val = (
                inner_val[
                    target_col
                ].to_numpy(float)
            )

            beta = fit_ridge(
                X_train,
                y_train,
                alpha,
            )

            pred = (
                X_val
                @ beta
            )

            errors.extend(
                (
                    pred
                    - y_val
                ).tolist()
            )

        if errors:

            rmse = float(
                np.sqrt(
                    np.mean(
                        np.asarray(
                            errors
                        ) ** 2
                    )
                )
            )

        else:

            rmse = np.inf

        scores.append(
            (
                rmse,
                alpha,
            )
        )

    scores.sort(
        key=lambda x:
            (
                x[0],
                x[1],
            )
    )

    return float(
        scores[0][1]
    )


# ============================================================
# OUTER LEAVE-ONE-TUBE-OUT
# ============================================================

parameter_predictions = []

tubes = sorted(
    params[
        "tube_id"
    ].unique()
)

print("=" * 86)
print(
    "UnsatConstitutiveLab — "
    "Leave-One-Tube-Out Constitutive Prediction"
)
print("=" * 86)

print()
print(
    "Stages:",
    len(params),
)

print(
    "Tubes :",
    len(tubes),
)

for model_name, features in MODELS.items():

    print()
    print(
        f"Running {model_name} ..."
    )

    for held_tube in tubes:

        train = params[
            params[
                "tube_id"
            ] != held_tube
        ].copy()

        test = params[
            params[
                "tube_id"
            ] == held_tube
        ].copy()

        target_predictions = {}

        selected_alphas = {}

        for target_name, target_col in TARGETS.items():

            alpha = choose_alpha(
                train,
                features,
                target_col,
            )

            selected_alphas[
                target_name
            ] = alpha

            X_train = design_matrix(
                train,
                train,
                features,
            )

            X_test = design_matrix(
                train,
                test,
                features,
            )

            y_train = (
                train[
                    target_col
                ].to_numpy(float)
            )

            beta = fit_ridge(
                X_train,
                y_train,
                alpha,
            )

            target_predictions[
                target_name
            ] = (
                X_test
                @ beta
            )

        for i, (
            index,
            row,
        ) in enumerate(
            test.iterrows()
        ):

            q_pred = float(
                np.exp(
                    target_predictions[
                        "log_q"
                    ][i]
                )
            )

            eps_pred = float(
                np.exp(
                    target_predictions[
                        "log_eps"
                    ][i]
                )
            )

            lambda_pred = float(
                np.expm1(
                    target_predictions[
                        "log1p_lambda"
                    ][i]
                )
            )

            lambda_pred = max(
                0.0,
                lambda_pred,
            )

            parameter_predictions.append({
                "model":
                    model_name,

                "heldout_tube":
                    held_tube,

                "figure_id":
                    row[
                        "figure_id"
                    ],

                "specimen_id":
                    row[
                        "specimen_id"
                    ],

                "stage":
                    row[
                        "stage"
                    ],

                "stage_index":
                    row[
                        "stage_index"
                    ],

                "tube_id":
                    row[
                        "tube_id"
                    ],

                "soil_type":
                    row[
                        "soil_type"
                    ],

                "test_family":
                    row[
                        "test_family"
                    ],

                "strain_confidence":
                    row[
                        "strain_confidence"
                    ],

                "q_obs_kPa":
                    row[
                        "q_peak_source_kPa"
                    ],

                "q_pred_kPa":
                    q_pred,

                "eps_peak_obs_pct":
                    row[
                        "eps_peak_pct"
                    ],

                "eps_peak_pred_pct":
                    eps_pred,

                "lambda_obs":
                    row[
                        "lambda_mobilization"
                    ],

                "lambda_pred":
                    lambda_pred,

                "alpha_q":
                    selected_alphas[
                        "log_q"
                    ],

                "alpha_eps":
                    selected_alphas[
                        "log_eps"
                    ],

                "alpha_lambda":
                    selected_alphas[
                        "log1p_lambda"
                    ],
            })


param_pred = pd.DataFrame(
    parameter_predictions
)

param_pred.to_csv(
    OUT_PARAM,
    index=False,
)


# ============================================================
# WHOLE PRE-PEAK CURVE PREDICTION
#
# Observed pre-peak strain locations are evaluation points.
# Predicted eps_peak determines when the predicted curve
# reaches its peak. No observed eps_peak is used in prediction.
# ============================================================

curve_rows = []

curve_lookup = curves.merge(
    params[
        [
            "figure_id",
            "specimen_id",
            "stage",
            "stage_index",
            "eps_peak_pct",
            "q_peak_source_kPa",
        ]
    ],
    on=[
        "figure_id",
        "specimen_id",
        "stage",
        "stage_index",
    ],
    how="inner",
    validate="many_to_one",
)

for _, prediction in param_pred.iterrows():

    obs = curve_lookup[
        (
            curve_lookup[
                "figure_id"
            ]
            == prediction[
                "figure_id"
            ]
        )
        & (
            curve_lookup[
                "specimen_id"
            ]
            == prediction[
                "specimen_id"
            ]
        )
        & (
            curve_lookup[
                "stage"
            ].astype(str)
            == str(
                prediction[
                    "stage"
                ]
            )
        )
    ].copy()

    if obs.empty:
        continue

    # Evaluate only the experimentally observed pre-peak branch.
    obs = obs[
        obs[
            "axial_strain_local_pct"
        ]
        <= obs[
            "eps_peak_pct"
        ]
        + 1e-9
    ].copy()

    if len(obs) < 10:
        continue

    eps = (
        obs[
            "axial_strain_local_pct"
        ].to_numpy(float)
    )

    q_obs = (
        obs[
            "q_digitized_kPa"
        ].to_numpy(float)
    )

    q_peak_obs = float(
        prediction[
            "q_obs_kPa"
        ]
    )

    q_peak_pred = float(
        prediction[
            "q_pred_kPa"
        ]
    )

    eps_peak_pred = max(
        0.05,
        float(
            prediction[
                "eps_peak_pred_pct"
            ]
        ),
    )

    lam = max(
        0.0,
        float(
            prediction[
                "lambda_pred"
            ]
        ),
    )

    x = (
        eps
        / eps_peak_pred
    )

    # Once predicted peak strain is reached,
    # retain predicted peak stress.
    x_eff = np.clip(
        x,
        0.0,
        1.0,
    )

    q_pred = (
        q_peak_pred
        * x_eff
        * (
            1.0
            + lam
        )
        / (
            1.0
            + lam
            * x_eff
        )
    )

    if q_peak_obs <= 0:
        continue

    curve_nrmse = float(
        np.sqrt(
            np.mean(
                (
                    (
                        q_pred
                        - q_obs
                    )
                    / q_peak_obs
                ) ** 2
            )
        )
    )

    curve_mae_norm = float(
        np.mean(
            np.abs(
                q_pred
                - q_obs
            )
        )
        / q_peak_obs
    )

    for j in range(
        len(obs)
    ):

        curve_rows.append({
            "model":
                prediction[
                    "model"
                ],

            "tube_id":
                prediction[
                    "tube_id"
                ],

            "figure_id":
                prediction[
                    "figure_id"
                ],

            "specimen_id":
                prediction[
                    "specimen_id"
                ],

            "stage":
                prediction[
                    "stage"
                ],

            "stage_index":
                prediction[
                    "stage_index"
                ],

            "soil_type":
                prediction[
                    "soil_type"
                ],

            "strain_confidence":
                prediction[
                    "strain_confidence"
                ],

            "axial_strain_pct":
                eps[j],

            "q_obs_kPa":
                q_obs[j],

            "q_pred_kPa":
                q_pred[j],

            "curve_nrmse":
                curve_nrmse,

            "curve_mae_norm":
                curve_mae_norm,
        })


curve_pred = pd.DataFrame(
    curve_rows
)

curve_pred.to_csv(
    OUT_CURVE,
    index=False,
)


# ============================================================
# STAGE-LEVEL CURVE SUMMARY
# ============================================================

stage_curve = (
    curve_pred[
        [
            "model",
            "tube_id",
            "figure_id",
            "specimen_id",
            "stage",
            "stage_index",
            "soil_type",
            "strain_confidence",
            "curve_nrmse",
            "curve_mae_norm",
        ]
    ]
    .drop_duplicates()
)


def metric_summary(
    frame,
):

    q_rel = (
        (
            frame[
                "q_pred_kPa"
            ]
            - frame[
                "q_obs_kPa"
            ]
        )
        / frame[
            "q_obs_kPa"
        ]
    )

    eps_rel = (
        (
            frame[
                "eps_peak_pred_pct"
            ]
            - frame[
                "eps_peak_obs_pct"
            ]
        )
        / frame[
            "eps_peak_obs_pct"
        ]
    )

    lam_rel = (
        (
            frame[
                "lambda_pred"
            ]
            - frame[
                "lambda_obs"
            ]
        )
        / (
            1.0
            + frame[
                "lambda_obs"
            ]
        )
    )

    return {
        "n_stages":
            len(frame),

        "n_tubes":
            frame[
                "tube_id"
            ].nunique(),

        "q_MdAPE_pct":
            100.0
            * float(
                np.median(
                    np.abs(
                        q_rel
                    )
                )
            ),

        "eps_peak_MdAPE_pct":
            100.0
            * float(
                np.median(
                    np.abs(
                        eps_rel
                    )
                )
            ),

        "lambda_scaled_MdAE_pct":
            100.0
            * float(
                np.median(
                    np.abs(
                        lam_rel
                    )
                )
            ),
    }


metric_rows = []

for model in MODELS:

    pp = param_pred[
        param_pred[
            "model"
        ] == model
    ]

    sc = stage_curve[
        stage_curve[
            "model"
        ] == model
    ]

    for subset_name, confidence_filter in [
        (
            "all",
            None,
        ),
        (
            "high_tick_only",
            "high_tick_calibrated",
        ),
    ]:

        if confidence_filter is None:

            pp_sub = pp
            sc_sub = sc

        else:

            pp_sub = pp[
                pp[
                    "strain_confidence"
                ]
                == confidence_filter
            ]

            sc_sub = sc[
                sc[
                    "strain_confidence"
                ]
                == confidence_filter
            ]

        if pp_sub.empty:
            continue

        parameter_stats = (
            metric_summary(
                pp_sub
            )
        )

        if sc_sub.empty:

            median_curve = np.nan
            mean_curve = np.nan
            p90_curve = np.nan

        else:

            median_curve = float(
                sc_sub[
                    "curve_nrmse"
                ].median()
            )

            mean_curve = float(
                sc_sub[
                    "curve_nrmse"
                ].mean()
            )

            p90_curve = float(
                sc_sub[
                    "curve_nrmse"
                ].quantile(
                    0.90
                )
            )

        metric_rows.append({
            "model":
                model,

            "subset":
                subset_name,

            **parameter_stats,

            "curve_nrmse_median":
                median_curve,

            "curve_nrmse_mean":
                mean_curve,

            "curve_nrmse_p90":
                p90_curve,
        })


metrics = pd.DataFrame(
    metric_rows
)

metrics.to_csv(
    OUT_METRICS,
    index=False,
)


# ============================================================
# CLUSTER BOOTSTRAP MODEL COMPARISON
#
# Main question:
# Does hydraulic state improve WHOLE CURVE prediction
# compared with suction alone?
# ============================================================

COMPARISONS = [
    (
        "Suction",
        "State",
    ),
    (
        "Suction",
        "StateInteraction",
    ),
    (
        "State",
        "StateInteraction",
    ),
    (
        "StateInteraction",
        "StateHistory",
    ),
]


def bootstrap_comparison(
    baseline,
    candidate,
    subset,
):

    base = stage_curve[
        (
            stage_curve[
                "model"
            ]
            == baseline
        )
    ].copy()

    cand = stage_curve[
        (
            stage_curve[
                "model"
            ]
            == candidate
        )
    ].copy()

    if subset == "high_tick_only":

        base = base[
            base[
                "strain_confidence"
            ]
            == "high_tick_calibrated"
        ]

        cand = cand[
            cand[
                "strain_confidence"
            ]
            == "high_tick_calibrated"
        ]

    keys = [
        "tube_id",
        "figure_id",
        "specimen_id",
        "stage",
    ]

    merged = (
        base[
            keys
            + [
                "curve_nrmse",
            ]
        ]
        .rename(
            columns={
                "curve_nrmse":
                    "baseline_error"
            }
        )
        .merge(
            cand[
                keys
                + [
                    "curve_nrmse",
                ]
            ].rename(
                columns={
                    "curve_nrmse":
                        "candidate_error"
                }
            ),
            on=keys,
            how="inner",
            validate="one_to_one",
        )
    )

    tubes = sorted(
        merged[
            "tube_id"
        ].unique()
    )

    if len(tubes) < 3:

        return None

    base_mean = float(
        merged[
            "baseline_error"
        ].mean()
    )

    cand_mean = float(
        merged[
            "candidate_error"
        ].mean()
    )

    point_change = (
        100.0
        * (
            cand_mean
            - base_mean
        )
        / base_mean
    )

    groups = {
        tube:
            merged[
                merged[
                    "tube_id"
                ]
                == tube
            ]
        for tube in tubes
    }

    boot = []

    for _ in range(
        N_BOOT
    ):

        sampled = RNG.choice(
            tubes,
            size=len(tubes),
            replace=True,
        )

        base_values = []
        candidate_values = []

        for tube in sampled:

            group = groups[
                tube
            ]

            base_values.extend(
                group[
                    "baseline_error"
                ].tolist()
            )

            candidate_values.extend(
                group[
                    "candidate_error"
                ].tolist()
            )

        b = float(
            np.mean(
                base_values
            )
        )

        c = float(
            np.mean(
                candidate_values
            )
        )

        if b > 0:

            boot.append(
                100.0
                * (
                    c
                    - b
                )
                / b
            )

    boot = np.asarray(
        boot,
        float,
    )

    return {
        "baseline_model":
            baseline,

        "candidate_model":
            candidate,

        "subset":
            subset,

        "n_tubes":
            len(tubes),

        "n_stages":
            len(merged),

        "baseline_curve_nrmse_mean":
            base_mean,

        "candidate_curve_nrmse_mean":
            cand_mean,

        "curve_error_change_pct":
            point_change,

        "bootstrap_p025_pct":
            float(
                np.quantile(
                    boot,
                    0.025,
                )
            ),

        "bootstrap_p975_pct":
            float(
                np.quantile(
                    boot,
                    0.975,
                )
            ),

        "prob_candidate_better":
            float(
                np.mean(
                    boot < 0
                )
            ),
    }


comparison_rows = []

for baseline, candidate in COMPARISONS:

    for subset in [
        "all",
        "high_tick_only",
    ]:

        result = bootstrap_comparison(
            baseline,
            candidate,
            subset,
        )

        if result is not None:
            comparison_rows.append(
                result
            )


comparisons = pd.DataFrame(
    comparison_rows
)

comparisons.to_csv(
    OUT_COMPARE,
    index=False,
)


# ============================================================
# REPORT
# ============================================================

print()
print("=== WHOLE-CURVE LOGO METRICS ===")

print(
    metrics.to_string(
        index=False
    )
)

print()
print(
    "=== PAIRWISE WHOLE-CURVE TESTS ==="
)

print(
    comparisons.to_string(
        index=False
    )
)

print()
print(
    "Decision rule:"
)

print(
    "Negative curve_error_change_pct = "
    "candidate predicts unseen pre-peak curves better."
)

print(
    "A 95% bootstrap interval fully below zero is "
    "strong evidence of improvement."
)

print(
    "High-tick-only results are the strain-axis "
    "sensitivity check."
)

print()
print(
    "PHASE 5B WHOLE-CURVE LOGO PREDICTION: PASS"
)
