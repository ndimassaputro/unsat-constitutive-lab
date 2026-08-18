from pathlib import Path
import re

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

SRC = Path("data/processed/strength_analysis_ready.csv")

OUT_PERF = Path(
    "results/tables/novelty_mc_vs_fredlund_bootstrap.csv"
)
OUT_STATE = Path(
    "results/tables/novelty_state_model_cv.csv"
)
OUT_STAGE = Path(
    "results/tables/novelty_stage_history_cv.csv"
)
OUT_STAGE_RESID = Path(
    "results/tables/novelty_stage_residuals.csv"
)
OUT_PRED = Path(
    "data/processed/novelty_cv_predictions.csv"
)

OUT_PERF.parent.mkdir(parents=True, exist_ok=True)
OUT_PRED.parent.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(20260818)
N_BOOT = 3000

df = pd.read_csv(SRC)


# ==============================================================
# BASIC HELPERS
# ==============================================================

def stage_number(value):
    text = str(value).strip().lower()

    if text == "single":
        return 1

    match = re.match(r"(\d+)", text)

    if match:
        return int(match.group(1))

    mapping = {
        "1st": 1,
        "2nd": 2,
        "3rd": 3,
        "4th": 4,
    }

    if text in mapping:
        return mapping[text]

    raise ValueError(f"Cannot parse stage: {value!r}")


df["stage_index"] = df["stage"].map(stage_number)


def tube_weights(frame):
    counts = (
        frame.groupby("tube_id")["tube_id"]
        .transform("size")
        .to_numpy(float)
    )

    return 1.0 / np.sqrt(counts)


def rmse(obs, pred):
    obs = np.asarray(obs, float)
    pred = np.asarray(pred, float)

    return float(
        np.sqrt(
            np.mean(
                (pred - obs) ** 2
            )
        )
    )


def mae(obs, pred):
    obs = np.asarray(obs, float)
    pred = np.asarray(pred, float)

    return float(
        np.mean(
            np.abs(pred - obs)
        )
    )


# ==============================================================
# MODEL DEFINITIONS
#
# Base triaxial form:
#
# q = A + B*sigma_c_net + D*suction
#
# State/history extensions add centered predictors.
#
# A, B, D constrained nonnegative.
# Extra empirical diagnostic coefficients are unconstrained.
#
# These extensions are DIAGNOSTIC models, not proposed
# constitutive laws.
# ==============================================================

MODEL_FEATURES = {
    "MC_baseline": [
        "sigma_c_net_kPa",
    ],
    "Fredlund": [
        "sigma_c_net_kPa",
        "matric_suction_kPa",
    ],
    "Fredlund_plus_Sr": [
        "sigma_c_net_kPa",
        "matric_suction_kPa",
        "degree_saturation",
    ],
    "Fredlund_plus_gamma": [
        "sigma_c_net_kPa",
        "matric_suction_kPa",
        "gamma_d_g_cm3",
    ],
    "Fredlund_plus_state": [
        "sigma_c_net_kPa",
        "matric_suction_kPa",
        "degree_saturation",
        "gamma_d_g_cm3",
    ],
    "Fredlund_plus_stage": [
        "sigma_c_net_kPa",
        "matric_suction_kPa",
        "stage_index",
    ],
}


def prepare_design(train, test, model_name):
    features = MODEL_FEATURES[model_name]

    X_train_cols = [
        np.ones(len(train))
    ]
    X_test_cols = [
        np.ones(len(test))
    ]

    centers = {}

    for feature in features:

        train_values = (
            train[feature]
            .to_numpy(float)
        )

        test_values = (
            test[feature]
            .to_numpy(float)
        )

        # Core physical variables stay uncentered.
        if feature in {
            "sigma_c_net_kPa",
            "matric_suction_kPa",
        }:
            X_train_cols.append(
                train_values
            )
            X_test_cols.append(
                test_values
            )
            centers[feature] = 0.0

        else:
            center = float(
                np.mean(train_values)
            )

            centers[feature] = center

            X_train_cols.append(
                train_values - center
            )
            X_test_cols.append(
                test_values - center
            )

    X_train = np.column_stack(
        X_train_cols
    )
    X_test = np.column_stack(
        X_test_cols
    )

    return X_train, X_test, centers


def coefficient_bounds(model_name):
    features = MODEL_FEATURES[model_name]

    ncoef = 1 + len(features)

    lower = np.full(
        ncoef,
        -np.inf,
        dtype=float,
    )

    upper = np.full(
        ncoef,
        np.inf,
        dtype=float,
    )

    # Intercept >= 0
    lower[0] = 0.0

    # sigma coefficient >= 0
    sigma_position = (
        1
        + features.index(
            "sigma_c_net_kPa"
        )
    )
    lower[sigma_position] = 0.0

    # suction coefficient >= 0 when present
    if "matric_suction_kPa" in features:
        suction_position = (
            1
            + features.index(
                "matric_suction_kPa"
            )
        )
        lower[suction_position] = 0.0

    return lower, upper


def fit_predict_fold(
    train,
    test,
    model_name,
):
    X_train, X_test, centers = (
        prepare_design(
            train,
            test,
            model_name,
        )
    )

    y_train = (
        train["q_peak_kPa"]
        .to_numpy(float)
    )

    weights = tube_weights(train)

    lower, upper = coefficient_bounds(
        model_name
    )

    result = lsq_linear(
        X_train * weights[:, None],
        y_train * weights,
        bounds=(lower, upper),
        method="trf",
    )

    if not result.success:
        raise RuntimeError(
            f"{model_name}: "
            f"{result.message}"
        )

    prediction = (
        X_test @ result.x
    )

    return prediction, result.x, centers


def grouped_cv(
    frame,
    model_names,
):
    parts = []

    tubes = sorted(
        frame["tube_id"]
        .unique()
    )

    for held_tube in tubes:

        train = frame[
            frame["tube_id"]
            != held_tube
        ].copy()

        test = frame[
            frame["tube_id"]
            == held_tube
        ].copy()

        if train["tube_id"].nunique() < 2:
            continue

        for model_name in model_names:

            pred, coef, centers = (
                fit_predict_fold(
                    train,
                    test,
                    model_name,
                )
            )

            temp = test.copy()

            temp["heldout_tube"] = (
                held_tube
            )
            temp["model"] = model_name
            temp["q_pred_kPa"] = pred

            temp["residual_kPa"] = (
                temp["q_pred_kPa"]
                - temp["q_peak_kPa"]
            )

            parts.append(temp)

    if not parts:
        return pd.DataFrame()

    return pd.concat(
        parts,
        ignore_index=True,
    )


# ==============================================================
# CLUSTER BOOTSTRAP OF RMSE DIFFERENCE
#
# Resample held-out tubes, not individual rows.
#
# delta < 0 means candidate model improves RMSE.
# ==============================================================

def bootstrap_rmse_difference(
    pred,
    baseline_model,
    candidate_model,
    n_boot=N_BOOT,
):
    base = pred[
        pred["model"]
        == baseline_model
    ].copy()

    candidate = pred[
        pred["model"]
        == candidate_model
    ].copy()

    key = [
        "tube_id",
        "specimen_id",
        "stage",
    ]

    base = base[
        key
        + [
            "q_peak_kPa",
            "q_pred_kPa",
        ]
    ].rename(
        columns={
            "q_pred_kPa":
                "q_base_kPa"
        }
    )

    candidate = candidate[
        key
        + [
            "q_pred_kPa",
        ]
    ].rename(
        columns={
            "q_pred_kPa":
                "q_candidate_kPa"
        }
    )

    merged = base.merge(
        candidate,
        on=key,
        how="inner",
        validate="one_to_one",
    )

    tubes = sorted(
        merged["tube_id"]
        .unique()
    )

    if len(tubes) < 2:
        return {
            "n_tubes": len(tubes),
            "rmse_baseline_kPa": np.nan,
            "rmse_candidate_kPa": np.nan,
            "rmse_change_pct": np.nan,
            "bootstrap_change_p025_pct": np.nan,
            "bootstrap_change_p975_pct": np.nan,
            "bootstrap_prob_improvement": np.nan,
        }

    base_rmse = rmse(
        merged["q_peak_kPa"],
        merged["q_base_kPa"],
    )

    candidate_rmse = rmse(
        merged["q_peak_kPa"],
        merged["q_candidate_kPa"],
    )

    point_change = (
        100.0
        * (
            candidate_rmse
            - base_rmse
        )
        / base_rmse
    )

    boot_changes = []

    grouped = {
        tube: merged[
            merged["tube_id"]
            == tube
        ]
        for tube in tubes
    }

    for _ in range(n_boot):

        sampled_tubes = RNG.choice(
            tubes,
            size=len(tubes),
            replace=True,
        )

        obs_parts = []
        base_parts = []
        cand_parts = []

        for tube in sampled_tubes:
            g = grouped[tube]

            obs_parts.append(
                g["q_peak_kPa"]
                .to_numpy(float)
            )
            base_parts.append(
                g["q_base_kPa"]
                .to_numpy(float)
            )
            cand_parts.append(
                g["q_candidate_kPa"]
                .to_numpy(float)
            )

        obs = np.concatenate(obs_parts)
        p_base = np.concatenate(base_parts)
        p_cand = np.concatenate(cand_parts)

        r0 = rmse(obs, p_base)
        r1 = rmse(obs, p_cand)

        if r0 > 0:
            boot_changes.append(
                100.0
                * (r1 - r0)
                / r0
            )

    boot_changes = np.asarray(
        boot_changes,
        float,
    )

    return {
        "n_tubes": len(tubes),
        "rmse_baseline_kPa":
            base_rmse,
        "rmse_candidate_kPa":
            candidate_rmse,
        "rmse_change_pct":
            point_change,
        "bootstrap_change_p025_pct":
            float(
                np.quantile(
                    boot_changes,
                    0.025,
                )
            ),
        "bootstrap_change_p975_pct":
            float(
                np.quantile(
                    boot_changes,
                    0.975,
                )
            ),
        "bootstrap_prob_improvement":
            float(
                np.mean(
                    boot_changes < 0
                )
            ),
    }


# ==============================================================
# PART A
# MC VS FREDLUND ROBUSTNESS
# ==============================================================

perf_rows = []
all_predictions = []

for soil in sorted(
    df["soil_type"].unique()
):

    soil_df = df[
        df["soil_type"] == soil
    ].copy()

    pred = grouped_cv(
        soil_df,
        [
            "MC_baseline",
            "Fredlund",
        ],
    )

    all_predictions.append(pred)

    stats = bootstrap_rmse_difference(
        pred,
        "MC_baseline",
        "Fredlund",
    )

    perf_rows.append({
        "soil_type": soil,
        "comparison":
            "Fredlund_vs_MC",
        **stats,
    })

perf = pd.DataFrame(perf_rows)
perf.to_csv(
    OUT_PERF,
    index=False,
)


# ==============================================================
# PART B
# CURRENT-STATE AUGMENTATION
# ==============================================================

state_rows = []

for soil in sorted(
    df["soil_type"].unique()
):

    soil_df = df[
        df["soil_type"] == soil
    ].copy()

    model_names = [
        "Fredlund",
        "Fredlund_plus_Sr",
        "Fredlund_plus_gamma",
        "Fredlund_plus_state",
    ]

    pred = grouped_cv(
        soil_df,
        model_names,
    )

    all_predictions.append(pred)

    for candidate in model_names[1:]:

        stats = bootstrap_rmse_difference(
            pred,
            "Fredlund",
            candidate,
        )

        state_rows.append({
            "soil_type": soil,
            "candidate_model": candidate,
            **stats,
        })

state = pd.DataFrame(state_rows)
state.to_csv(
    OUT_STATE,
    index=False,
)


# ==============================================================
# PART C
# MULTISTAGE STAGE-ORDER / HISTORY-PROXY TEST
#
# Only multistage specimens are used here.
#
# Question:
# After current net stress and current suction are known,
# does stage order still improve prediction?
#
# If yes, stage order is evidence of omitted history/state
# information. It is NOT proof of a physical mechanism.
# ==============================================================

stage_rows = []
stage_residual_parts = []

for soil in sorted(
    df["soil_type"].unique()
):

    multi = df[
        (df["soil_type"] == soil)
        & (
            df["test_family"]
            == "multistage"
        )
    ].copy()

    n_tubes = (
        multi["tube_id"]
        .nunique()
    )

    if n_tubes < 3:
        stage_rows.append({
            "soil_type": soil,
            "n_multistage_tubes":
                n_tubes,
            "status":
                "insufficient_tubes",
            "rmse_baseline_kPa":
                np.nan,
            "rmse_stage_kPa":
                np.nan,
            "rmse_change_pct":
                np.nan,
            "bootstrap_change_p025_pct":
                np.nan,
            "bootstrap_change_p975_pct":
                np.nan,
            "bootstrap_prob_improvement":
                np.nan,
        })
        continue

    pred = grouped_cv(
        multi,
        [
            "Fredlund",
            "Fredlund_plus_stage",
        ],
    )

    all_predictions.append(pred)

    stats = bootstrap_rmse_difference(
        pred,
        "Fredlund",
        "Fredlund_plus_stage",
    )

    stage_rows.append({
        "soil_type": soil,
        "n_multistage_tubes":
            n_tubes,
        "status":
            "evaluated",
        "rmse_baseline_kPa":
            stats[
                "rmse_baseline_kPa"
            ],
        "rmse_stage_kPa":
            stats[
                "rmse_candidate_kPa"
            ],
        "rmse_change_pct":
            stats[
                "rmse_change_pct"
            ],
        "bootstrap_change_p025_pct":
            stats[
                "bootstrap_change_p025_pct"
            ],
        "bootstrap_change_p975_pct":
            stats[
                "bootstrap_change_p975_pct"
            ],
        "bootstrap_prob_improvement":
            stats[
                "bootstrap_prob_improvement"
            ],
    })

    base = pred[
        pred["model"] == "Fredlund"
    ].copy()

    grouped_resid = (
        base.groupby("stage_index")
        .agg(
            n_rows=(
                "residual_kPa",
                "size",
            ),
            n_tubes=(
                "tube_id",
                "nunique",
            ),
            mean_residual_kPa=(
                "residual_kPa",
                "mean",
            ),
            median_residual_kPa=(
                "residual_kPa",
                "median",
            ),
            mean_abs_residual_kPa=(
                "residual_kPa",
                lambda x:
                    np.mean(
                        np.abs(x)
                    ),
            ),
        )
        .reset_index()
    )

    grouped_resid.insert(
        0,
        "soil_type",
        soil,
    )

    stage_residual_parts.append(
        grouped_resid
    )

stage = pd.DataFrame(stage_rows)
stage.to_csv(
    OUT_STAGE,
    index=False,
)

if stage_residual_parts:
    stage_resid = pd.concat(
        stage_residual_parts,
        ignore_index=True,
    )
else:
    stage_resid = pd.DataFrame()

stage_resid.to_csv(
    OUT_STAGE_RESID,
    index=False,
)


# ==============================================================
# SAVE ALL PREDICTIONS
# ==============================================================

predictions = pd.concat(
    all_predictions,
    ignore_index=True,
)

predictions.to_csv(
    OUT_PRED,
    index=False,
)


# ==============================================================
# REPORT
# ==============================================================

print("=" * 80)
print(
    "UnsatConstitutiveLab — Phase 3C Novelty Diagnostics"
)
print("=" * 80)

print()
print(
    "=== A. FREDLUND VS MC: "
    "BOOTSTRAP ROBUSTNESS ==="
)

print(
    perf[
        [
            "soil_type",
            "n_tubes",
            "rmse_baseline_kPa",
            "rmse_candidate_kPa",
            "rmse_change_pct",
            "bootstrap_change_p025_pct",
            "bootstrap_change_p975_pct",
            "bootstrap_prob_improvement",
        ]
    ].to_string(index=False)
)

print()
print(
    "=== B. OMITTED STATE VARIABLE TEST ==="
)

print(
    state[
        [
            "soil_type",
            "candidate_model",
            "n_tubes",
            "rmse_candidate_kPa",
            "rmse_change_pct",
            "bootstrap_change_p025_pct",
            "bootstrap_change_p975_pct",
            "bootstrap_prob_improvement",
        ]
    ].to_string(index=False)
)

print()
print(
    "=== C. MULTISTAGE STAGE-ORDER "
    "PROXY TEST ==="
)

print(
    stage.to_string(
        index=False
    )
)

print()
print(
    "=== D. FREDLUND CV RESIDUALS "
    "BY MULTISTAGE ORDER ==="
)

if stage_resid.empty:
    print(
        "No soil group had enough "
        "multistage tubes."
    )
else:
    print(
        stage_resid.to_string(
            index=False
        )
    )

print()
print("INTERPRETATION")
print(
    "1) Negative RMSE change means "
    "candidate improves leave-one-tube-out prediction."
)
print(
    "2) Bootstrap probability near 1.0 means "
    "improvement is consistent across resampled tubes."
)
print(
    "3) A stage-order improvement is only a "
    "loading-history proxy signal, not proof of mechanism."
)
print(
    "4) A state-variable improvement indicates that "
    "current stress+suction alone omit predictive information."
)
print(
    "5) Scientific novelty is NOT claimed until the "
    "strongest signal is checked against prior literature."
)

print()
print(
    "PHASE 3C NOVELTY DIAGNOSTICS: PASS"
)
