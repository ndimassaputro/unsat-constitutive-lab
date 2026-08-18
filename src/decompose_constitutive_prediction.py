from pathlib import Path

import numpy as np
import pandas as pd

PARAM_PRED = Path(
    "data/processed/constitutive_logo_parameter_predictions.csv"
)

CURVE_FITS = Path(
    "data/processed/constitutive_curve_fit_predictions.csv"
)

PARAMS = Path(
    "results/tables/constitutive_curve_parameters.csv"
)

OUT = Path(
    "results/tables/constitutive_prediction_decomposition.csv"
)

PAIR_OUT = Path(
    "results/tables/constitutive_shape_pairwise.csv"
)

OUT.parent.mkdir(parents=True, exist_ok=True)
PAIR_OUT.parent.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(20260818)
N_BOOT = 10000

pred = pd.read_csv(PARAM_PRED)
curves = pd.read_csv(CURVE_FITS)
params = pd.read_csv(PARAMS)

MODELS = [
    "Mechanical",
    "Suction",
    "State",
    "StateInteraction",
    "StateHistory",
]


# ============================================================
# CURVE LOOKUP
# ============================================================

curve_meta = curves.merge(
    params[
        [
            "figure_id",
            "specimen_id",
            "stage",
            "stage_index",
            "tube_id",
            "soil_type",
            "strain_confidence",
            "q_peak_source_kPa",
            "eps_peak_pct",
            "lambda_mobilization",
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


# ============================================================
# HYPERBOLIC PRE-PEAK CURVE
# ============================================================

def hyperbolic_curve(
    eps,
    q_peak,
    eps_peak,
    lam,
):

    eps_peak = max(
        0.05,
        float(eps_peak),
    )

    lam = max(
        0.0,
        float(lam),
    )

    x = (
        np.asarray(
            eps,
            float,
        )
        / eps_peak
    )

    x = np.clip(
        x,
        0.0,
        1.0,
    )

    return (
        q_peak
        * x
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


def normalized_rmse(
    obs,
    estimate,
    normalizer,
):

    obs = np.asarray(
        obs,
        float,
    )

    estimate = np.asarray(
        estimate,
        float,
    )

    return float(
        np.sqrt(
            np.mean(
                (
                    (
                        estimate
                        - obs
                    )
                    / normalizer
                ) ** 2
            )
        )
    )


# ============================================================
# DECOMPOSITION
#
# FULL:
#   predicted q_peak + predicted eps_peak + predicted lambda
#
# STRENGTH ONLY:
#   predicted q_peak + observed curve shape
#
# SHAPE ONLY:
#   observed q_peak + predicted eps_peak + predicted lambda
#
# EPS ONLY:
#   observed q_peak + predicted eps_peak + observed lambda
#
# LAMBDA ONLY:
#   observed q_peak + observed eps_peak + predicted lambda
#
# This separates peak-strength prediction from constitutive
# shape-transfer prediction.
# ============================================================

rows = []

for _, pp in pred.iterrows():

    model = pp["model"]

    obs = curve_meta[
        (
            curve_meta["figure_id"]
            == pp["figure_id"]
        )
        & (
            curve_meta["specimen_id"]
            == pp["specimen_id"]
        )
        & (
            curve_meta["stage"].astype(str)
            == str(pp["stage"])
        )
    ].copy()

    if obs.empty:
        continue

    q_peak_obs = float(
        pp["q_obs_kPa"]
    )

    eps_peak_obs = float(
        pp["eps_peak_obs_pct"]
    )

    lambda_obs = float(
        pp["lambda_obs"]
    )

    q_peak_pred = float(
        pp["q_pred_kPa"]
    )

    eps_peak_pred = float(
        pp["eps_peak_pred_pct"]
    )

    lambda_pred = float(
        pp["lambda_pred"]
    )

    # Only evaluate experimentally observed pre-peak branch.
    obs = obs[
        obs["axial_strain_local_pct"]
        <= eps_peak_obs + 1e-9
    ].copy()

    if len(obs) < 10:
        continue

    eps = (
        obs[
            "axial_strain_local_pct"
        ]
        .to_numpy(float)
    )

    q_obs = (
        obs[
            "q_digitized_kPa"
        ]
        .to_numpy(float)
    )

    # Full prediction.
    q_full = hyperbolic_curve(
        eps,
        q_peak_pred,
        eps_peak_pred,
        lambda_pred,
    )

    # Strength-only error:
    # preserve observed normalized curve shape,
    # scale only by predicted peak strength.
    q_strength_only = (
        q_obs
        / q_peak_obs
        * q_peak_pred
    )

    # Shape-only:
    # exact measured peak strength,
    # predicted eps_peak + lambda.
    q_shape_only = hyperbolic_curve(
        eps,
        q_peak_obs,
        eps_peak_pred,
        lambda_pred,
    )

    # Peak-strain contribution only.
    q_eps_only = hyperbolic_curve(
        eps,
        q_peak_obs,
        eps_peak_pred,
        lambda_obs,
    )

    # Mobilization-curvature contribution only.
    q_lambda_only = hyperbolic_curve(
        eps,
        q_peak_obs,
        eps_peak_obs,
        lambda_pred,
    )

    metrics = {
        "full_curve_nrmse":
            normalized_rmse(
                q_obs,
                q_full,
                q_peak_obs,
            ),

        "strength_only_nrmse":
            normalized_rmse(
                q_obs,
                q_strength_only,
                q_peak_obs,
            ),

        "shape_only_nrmse":
            normalized_rmse(
                q_obs,
                q_shape_only,
                q_peak_obs,
            ),

        "eps_only_nrmse":
            normalized_rmse(
                q_obs,
                q_eps_only,
                q_peak_obs,
            ),

        "lambda_only_nrmse":
            normalized_rmse(
                q_obs,
                q_lambda_only,
                q_peak_obs,
            ),
    }

    rows.append({
        "model":
            model,

        "tube_id":
            pp["tube_id"],

        "figure_id":
            pp["figure_id"],

        "specimen_id":
            pp["specimen_id"],

        "stage":
            pp["stage"],

        "stage_index":
            pp["stage_index"],

        "soil_type":
            pp["soil_type"],

        "test_family":
            pp["test_family"],

        "strain_confidence":
            pp["strain_confidence"],

        **metrics,
    })


decomp = pd.DataFrame(
    rows
)

decomp.to_csv(
    OUT,
    index=False,
)


# ============================================================
# SUMMARY
# ============================================================

summary_rows = []

for model in MODELS:

    model_df = decomp[
        decomp["model"]
        == model
    ]

    for subset in [
        "all",
        "high_tick_only",
    ]:

        if subset == "all":
            frame = model_df
        else:
            frame = model_df[
                model_df[
                    "strain_confidence"
                ]
                == "high_tick_calibrated"
            ]

        if frame.empty:
            continue

        summary_rows.append({
            "model":
                model,

            "subset":
                subset,

            "n_stages":
                len(frame),

            "n_tubes":
                frame[
                    "tube_id"
                ].nunique(),

            "full_mean":
                frame[
                    "full_curve_nrmse"
                ].mean(),

            "strength_only_mean":
                frame[
                    "strength_only_nrmse"
                ].mean(),

            "shape_only_mean":
                frame[
                    "shape_only_nrmse"
                ].mean(),

            "eps_only_mean":
                frame[
                    "eps_only_nrmse"
                ].mean(),

            "lambda_only_mean":
                frame[
                    "lambda_only_nrmse"
                ].mean(),

            "shape_only_median":
                frame[
                    "shape_only_nrmse"
                ].median(),

            "shape_only_p90":
                frame[
                    "shape_only_nrmse"
                ].quantile(
                    0.90
                ),
        })


summary = pd.DataFrame(
    summary_rows
)


# ============================================================
# PAIRED CLUSTER BOOTSTRAP:
# SUCTION VS STATE / STATE-INTERACTION
# FOR SHAPE ONLY
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


def paired_bootstrap(
    baseline,
    candidate,
    subset,
    metric,
):

    base = decomp[
        decomp["model"]
        == baseline
    ].copy()

    cand = decomp[
        decomp["model"]
        == candidate
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
                metric
            ]
        ]
        .rename(
            columns={
                metric:
                    "baseline_error"
            }
        )
        .merge(
            cand[
                keys
                + [
                    metric
                ]
            ].rename(
                columns={
                    metric:
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

    b_mean = float(
        merged[
            "baseline_error"
        ].mean()
    )

    c_mean = float(
        merged[
            "candidate_error"
        ].mean()
    )

    point = (
        100.0
        * (
            c_mean
            - b_mean
        )
        / b_mean
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

        b_vals = []
        c_vals = []

        for tube in sampled:

            g = groups[tube]

            b_vals.extend(
                g[
                    "baseline_error"
                ].tolist()
            )

            c_vals.extend(
                g[
                    "candidate_error"
                ].tolist()
            )

        b = float(
            np.mean(
                b_vals
            )
        )

        c = float(
            np.mean(
                c_vals
            )
        )

        if b > 0:
            boot.append(
                100.0
                * (
                    c - b
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

        "metric":
            metric,

        "n_tubes":
            len(tubes),

        "n_stages":
            len(merged),

        "baseline_mean":
            b_mean,

        "candidate_mean":
            c_mean,

        "change_pct":
            point,

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


pair_rows = []

for metric in [
    "strength_only_nrmse",
    "shape_only_nrmse",
    "eps_only_nrmse",
    "lambda_only_nrmse",
]:

    for baseline, candidate in COMPARISONS:

        for subset in [
            "all",
            "high_tick_only",
        ]:

            result = paired_bootstrap(
                baseline,
                candidate,
                subset,
                metric,
            )

            if result is not None:
                pair_rows.append(
                    result
                )


pairwise = pd.DataFrame(
    pair_rows
)

pairwise.to_csv(
    PAIR_OUT,
    index=False,
)


# ============================================================
# REPORT
# ============================================================

print("=" * 88)
print(
    "UnsatConstitutiveLab — "
    "Phase 5C Constitutive Prediction Decomposition"
)
print("=" * 88)

print()
print("=== ERROR DECOMPOSITION ===")

print(
    summary.to_string(
        index=False
    )
)

print()
print(
    "=== SHAPE-ONLY PAIRWISE TESTS ==="
)

shape = pairwise[
    pairwise["metric"]
    == "shape_only_nrmse"
]

print(
    shape.to_string(
        index=False
    )
)

print()
print(
    "=== STRENGTH-ONLY PAIRWISE TESTS ==="
)

strength_part = pairwise[
    pairwise["metric"]
    == "strength_only_nrmse"
]

print(
    strength_part.to_string(
        index=False
    )
)

print()
print(
    "Interpretation:"
)

print(
    "- strength_only = effect from q_peak prediction only."
)

print(
    "- shape_only = q_peak is known exactly; only "
    "eps_peak + lambda must transfer to unseen tubes."
)

print(
    "- If state information improves shape_only, "
    "the benefit is genuinely constitutive-shape related."
)

print(
    "- If state improves strength_only but not shape_only, "
    "the whole-curve advantage is mainly a strength effect."
)

print()
print(
    "Outputs:"
)

print(
    " ",
    OUT,
)

print(
    " ",
    PAIR_OUT,
)

print()
print(
    "PHASE 5C CONSTITUTIVE DECOMPOSITION: PASS"
)
