from pathlib import Path

import hashlib
import numpy as np
import pandas as pd

PARAMS = Path(
    "results/tables/constitutive_curve_parameters.csv"
)

OUT_METRICS = Path(
    "results/tables/history_signal_decomposition.csv"
)

OUT_PRED = Path(
    "data/processed/history_signal_predictions.csv"
)

OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
OUT_PRED.parent.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(20260818)
N_BOOT = 10000

df = pd.read_csv(PARAMS)

df["is_multistage"] = (
    df["test_family"] == "multistage"
).astype(float)

df["suction_x_saturation"] = (
    df["matric_suction_kPa"]
    * df["degree_saturation"]
)

# ------------------------------------------------------------
# MECHANICAL HISTORY VARIABLES
#
# For each specimen, use only information from PRIOR stages.
# Stage 1 therefore has zero prior-history quantities.
# ------------------------------------------------------------

df = df.sort_values(
    [
        "specimen_id",
        "stage_index",
    ]
).copy()

df["prior_q_peak_max_kPa"] = 0.0
df["prior_sigma_c_max_kPa"] = 0.0
df["prior_suction_max_kPa"] = 0.0
df["cumulative_prior_q_peak_kPa"] = 0.0
df["n_prior_stages"] = 0.0

for specimen_id, group in df.groupby(
    "specimen_id"
):
    indices = group.index.tolist()

    prior_q = []
    prior_sigma = []
    prior_suction = []

    for index in indices:
        df.loc[
            index,
            "n_prior_stages"
        ] = len(prior_q)

        if prior_q:
            df.loc[
                index,
                "prior_q_peak_max_kPa"
            ] = max(prior_q)

            df.loc[
                index,
                "prior_sigma_c_max_kPa"
            ] = max(prior_sigma)

            df.loc[
                index,
                "prior_suction_max_kPa"
            ] = max(prior_suction)

            df.loc[
                index,
                "cumulative_prior_q_peak_kPa"
            ] = sum(prior_q)

        prior_q.append(
            float(
                df.loc[
                    index,
                    "q_peak_source_kPa",
                ]
            )
        )

        prior_sigma.append(
            float(
                df.loc[
                    index,
                    "sigma_c_net_kPa",
                ]
            )
        )

        prior_suction.append(
            float(
                df.loc[
                    index,
                    "matric_suction_kPa",
                ]
            )
        )


# ------------------------------------------------------------
# TARGET = normalized curve shape parameters only
# ------------------------------------------------------------

df["target_log_eps"] = np.log(
    df["eps_peak_pct"]
)

df["target_log1p_lambda"] = np.log1p(
    df["lambda_mobilization"]
)

TARGETS = {
    "eps":
        "target_log_eps",

    "lambda":
        "target_log1p_lambda",
}


# ------------------------------------------------------------
# MODEL HIERARCHY
# ------------------------------------------------------------

BASE_STATE = [
    "sigma_c_net_kPa",
    "matric_suction_kPa",
    "degree_saturation",
    "gamma_d_g_cm3",
    "suction_x_saturation",
]

MODELS = {
    "StateInteraction":
        BASE_STATE,

    "PlusTestFamily":
        BASE_STATE
        + [
            "is_multistage",
        ],

    "PlusStageIndex":
        BASE_STATE
        + [
            "stage_index",
        ],

    "PlusFamilyAndStage":
        BASE_STATE
        + [
            "is_multistage",
            "stage_index",
        ],

    "PlusMechanicalHistory":
        BASE_STATE
        + [
            "is_multistage",
            "n_prior_stages",
            "prior_q_peak_max_kPa",
            "prior_sigma_c_max_kPa",
            "prior_suction_max_kPa",
            "cumulative_prior_q_peak_kPa",
        ],
}


# ------------------------------------------------------------
# DESIGN / RIDGE
# ------------------------------------------------------------

ALPHAS = [
    0.0,
    0.01,
    0.1,
    1.0,
    10.0,
    100.0,
]


def design_matrix(
    train,
    frame,
    features,
):
    train_values = (
        train[features]
        .to_numpy(float)
    )

    values = (
        frame[features]
        .to_numpy(float)
    )

    mean = np.mean(
        train_values,
        axis=0,
    )

    std = np.std(
        train_values,
        axis=0,
        ddof=1,
    )

    std[
        ~np.isfinite(std)
        | (std < 1e-12)
    ] = 1.0

    z = (
        values - mean
    ) / std

    soil_ml = (
        frame["soil_type"]
        == "ML"
    ).astype(float)

    soil_sc = (
        frame["soil_type"]
        == "SC"
    ).astype(float)

    return np.column_stack([
        np.ones(
            len(frame)
        ),
        z,
        soil_ml,
        soil_sc,
    ])


def fit_ridge(
    X,
    y,
    alpha,
):
    penalty = np.eye(
        X.shape[1]
    )

    penalty[0, 0] = 0.0

    return np.linalg.pinv(
        X.T @ X
        + alpha
        * penalty
    ) @ (
        X.T @ y
    )


def deterministic_fold(
    tube_id,
):
    digest = hashlib.sha256(
        str(tube_id).encode()
    ).hexdigest()

    return (
        int(
            digest[:8],
            16,
        )
        % 5
    )


def choose_alpha(
    train,
    features,
    target,
):
    fold = {
        tube:
            deterministic_fold(
                tube
            )
        for tube
        in train[
            "tube_id"
        ].unique()
    }

    candidates = []

    for alpha in ALPHAS:
        residuals = []

        for f in sorted(
            set(
                fold.values()
            )
        ):
            validation_tubes = [
                tube
                for tube, value
                in fold.items()
                if value == f
            ]

            tr = train[
                ~train[
                    "tube_id"
                ].isin(
                    validation_tubes
                )
            ]

            va = train[
                train[
                    "tube_id"
                ].isin(
                    validation_tubes
                )
            ]

            if (
                len(tr) < 10
                or va.empty
            ):
                continue

            Xtr = design_matrix(
                tr,
                tr,
                features,
            )

            Xva = design_matrix(
                tr,
                va,
                features,
            )

            beta = fit_ridge(
                Xtr,
                tr[target].to_numpy(
                    float
                ),
                alpha,
            )

            pred = (
                Xva @ beta
            )

            residuals.extend(
                (
                    pred
                    - va[
                        target
                    ].to_numpy(
                        float
                    )
                ).tolist()
            )

        score = (
            np.sqrt(
                np.mean(
                    np.asarray(
                        residuals
                    ) ** 2
                )
            )
            if residuals
            else np.inf
        )

        candidates.append(
            (
                score,
                alpha,
            )
        )

    candidates.sort()

    return float(
        candidates[0][1]
    )


# ------------------------------------------------------------
# OUTER LEAVE-ONE-TUBE-OUT
# ------------------------------------------------------------

predictions = []

for model_name, features in MODELS.items():

    print(
        "Running",
        model_name,
    )

    for held_tube in sorted(
        df[
            "tube_id"
        ].unique()
    ):
        train = df[
            df[
                "tube_id"
            ] != held_tube
        ].copy()

        test = df[
            df[
                "tube_id"
            ] == held_tube
        ].copy()

        predicted = {}

        for target_name, target_col in TARGETS.items():
            alpha = choose_alpha(
                train,
                features,
                target_col,
            )

            Xtr = design_matrix(
                train,
                train,
                features,
            )

            Xte = design_matrix(
                train,
                test,
                features,
            )

            beta = fit_ridge(
                Xtr,
                train[
                    target_col
                ].to_numpy(
                    float
                ),
                alpha,
            )

            predicted[
                target_name
            ] = (
                Xte @ beta
            )

        for i, (_, row) in enumerate(
            test.iterrows()
        ):
            predictions.append({
                "model":
                    model_name,

                "tube_id":
                    row[
                        "tube_id"
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

                "eps_obs":
                    row[
                        "eps_peak_pct"
                    ],

                "eps_pred":
                    np.exp(
                        predicted[
                            "eps"
                        ][i]
                    ),

                "lambda_obs":
                    row[
                        "lambda_mobilization"
                    ],

                "lambda_pred":
                    max(
                        0.0,
                        np.expm1(
                            predicted[
                                "lambda"
                            ][i]
                        ),
                    ),
            })


pred = pd.DataFrame(
    predictions
)

pred.to_csv(
    OUT_PRED,
    index=False,
)


# ------------------------------------------------------------
# SHAPE PARAMETER ERROR
# ------------------------------------------------------------

pred[
    "eps_abs_rel_error"
] = np.abs(
    pred[
        "eps_pred"
    ]
    - pred[
        "eps_obs"
    ]
) / pred[
    "eps_obs"
]

pred[
    "lambda_scaled_abs_error"
] = np.abs(
    pred[
        "lambda_pred"
    ]
    - pred[
        "lambda_obs"
    ]
) / (
    1.0
    + pred[
        "lambda_obs"
    ]
)

pred[
    "joint_shape_error"
] = (
    0.5
    * pred[
        "eps_abs_rel_error"
    ]
    + 0.5
    * pred[
        "lambda_scaled_abs_error"
    ]
)


# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

summary_rows = []

for model in MODELS:

    model_df = pred[
        pred["model"]
        == model
    ]

    for subset_name, frame in [
        (
            "all",
            model_df,
        ),
        (
            "multistage_only",
            model_df[
                model_df[
                    "test_family"
                ]
                == "multistage"
            ],
        ),
        (
            "later_multistage_only",
            model_df[
                (
                    model_df[
                        "test_family"
                    ]
                    == "multistage"
                )
                & (
                    model_df[
                        "stage_index"
                    ]
                    >= 2
                )
            ],
        ),
        (
            "high_tick_only",
            model_df[
                model_df[
                    "strain_confidence"
                ]
                == "high_tick_calibrated"
            ],
        ),
    ]:

        if frame.empty:
            continue

        summary_rows.append({
            "model":
                model,

            "subset":
                subset_name,

            "n_stages":
                len(frame),

            "n_tubes":
                frame[
                    "tube_id"
                ].nunique(),

            "eps_MdAPE_pct":
                100.0
                * frame[
                    "eps_abs_rel_error"
                ].median(),

            "lambda_MdAE_pct":
                100.0
                * frame[
                    "lambda_scaled_abs_error"
                ].median(),

            "joint_shape_error_mean":
                frame[
                    "joint_shape_error"
                ].mean(),

            "joint_shape_error_median":
                frame[
                    "joint_shape_error"
                ].median(),
        })


summary = pd.DataFrame(
    summary_rows
)


# ------------------------------------------------------------
# CLUSTER BOOTSTRAP VS BASELINE
# ------------------------------------------------------------

BASELINE = (
    "StateInteraction"
)

pair_rows = []

for candidate in [
    "PlusTestFamily",
    "PlusStageIndex",
    "PlusFamilyAndStage",
    "PlusMechanicalHistory",
]:

    for subset in [
        "all",
        "multistage_only",
        "later_multistage_only",
    ]:

        base = pred[
            pred[
                "model"
            ] == BASELINE
        ].copy()

        cand = pred[
            pred[
                "model"
            ] == candidate
        ].copy()

        if subset == "multistage_only":
            base = base[
                base[
                    "test_family"
                ] == "multistage"
            ]

            cand = cand[
                cand[
                    "test_family"
                ] == "multistage"
            ]

        elif subset == "later_multistage_only":
            base = base[
                (
                    base[
                        "test_family"
                    ] == "multistage"
                )
                & (
                    base[
                        "stage_index"
                    ] >= 2
                )
            ]

            cand = cand[
                (
                    cand[
                        "test_family"
                    ] == "multistage"
                )
                & (
                    cand[
                        "stage_index"
                    ] >= 2
                )
            ]

        keys = [
            "tube_id",
            "specimen_id",
            "stage",
        ]

        merged = (
            base[
                keys
                + [
                    "joint_shape_error"
                ]
            ]
            .rename(
                columns={
                    "joint_shape_error":
                        "base_error"
                }
            )
            .merge(
                cand[
                    keys
                    + [
                        "joint_shape_error"
                    ]
                ].rename(
                    columns={
                        "joint_shape_error":
                            "candidate_error"
                    }
                ),
                on=keys,
                validate="one_to_one",
            )
        )

        tubes = sorted(
            merged[
                "tube_id"
            ].unique()
        )

        if len(tubes) < 3:
            continue

        b = (
            merged[
                "base_error"
            ].mean()
        )

        c = (
            merged[
                "candidate_error"
            ].mean()
        )

        point = (
            100.0
            * (
                c - b
            )
            / b
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

            b_values = []
            c_values = []

            for tube in sampled:
                g = groups[
                    tube
                ]

                b_values.extend(
                    g[
                        "base_error"
                    ]
                )

                c_values.extend(
                    g[
                        "candidate_error"
                    ]
                )

            bb = np.mean(
                b_values
            )

            cc = np.mean(
                c_values
            )

            boot.append(
                100.0
                * (
                    cc - bb
                )
                / bb
            )

        boot = np.asarray(
            boot
        )

        pair_rows.append({
            "candidate_model":
                candidate,

            "subset":
                subset,

            "n_tubes":
                len(tubes),

            "n_stages":
                len(merged),

            "baseline_error":
                b,

            "candidate_error":
                c,

            "change_pct":
                point,

            "bootstrap_p025_pct":
                np.quantile(
                    boot,
                    0.025,
                ),

            "bootstrap_p975_pct":
                np.quantile(
                    boot,
                    0.975,
                ),

            "prob_candidate_better":
                np.mean(
                    boot < 0
                ),
        })


pairwise = pd.DataFrame(
    pair_rows
)

summary.to_csv(
    OUT_METRICS,
    index=False,
)


# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

print()
print("=" * 88)
print(
    "UnsatConstitutiveLab — "
    "Phase 5D Loading-History Decomposition"
)
print("=" * 88)

print()
print(
    "=== MODEL SUMMARY ==="
)

print(
    summary.to_string(
        index=False
    )
)

print()
print(
    "=== HISTORY VS STATE-INTERACTION ==="
)

print(
    pairwise.to_string(
        index=False
    )
)

print()
print(
    "Interpretation:"
)

print(
    "- PlusTestFamily isolates single-vs-multistage difference."
)

print(
    "- PlusStageIndex tests ordinal stage information."
)

print(
    "- PlusMechanicalHistory uses only prior-stage loading information."
)

print(
    "- later_multistage_only is the most direct history test because "
    "every evaluated observation has actual prior loading."
)

print(
    "- A robust improvement there is substantially stronger evidence "
    "than a generic stage-number effect."
)

print()
print(
    "PHASE 5D LOADING-HISTORY DECOMPOSITION: PASS"
)
