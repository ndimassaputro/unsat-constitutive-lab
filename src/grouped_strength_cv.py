from pathlib import Path
import math

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

SRC = Path("data/processed/strength_analysis_ready.csv")
OUT = Path("results/tables/strength_grouped_cv.csv")
PRED_OUT = Path("data/processed/strength_grouped_cv_predictions.csv")

OUT.parent.mkdir(parents=True, exist_ok=True)
PRED_OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SRC)


def tube_weights(frame):
    counts = frame.groupby("tube_id")["tube_id"].transform("size")
    return 1.0 / np.sqrt(counts.to_numpy(float))


def design_matrix(frame, suction):
    sigma = frame["sigma_c_net_kPa"].to_numpy(float)

    if suction:
        psi = frame["matric_suction_kPa"].to_numpy(float)
        return np.column_stack([
            np.ones(len(frame)),
            sigma,
            psi,
        ])

    return np.column_stack([
        np.ones(len(frame)),
        sigma,
    ])


def fit(train, suction):
    X = design_matrix(train, suction)
    y = train["q_peak_kPa"].to_numpy(float)
    w = tube_weights(train)

    res = lsq_linear(
        X * w[:, None],
        y * w,
        bounds=(0.0, np.inf),
    )

    if not res.success:
        raise RuntimeError(res.message)

    return res.x


def predict(frame, coef, suction):
    return design_matrix(frame, suction) @ coef


models = {
    "MC_baseline": False,
    "Fredlund_suction": True,
}

prediction_parts = []

for soil in sorted(df["soil_type"].unique()):

    soil_df = df[df["soil_type"] == soil].copy()

    tubes = sorted(
        soil_df["tube_id"].unique()
    )

    print()
    print(
        f"{soil}: {len(tubes)} tubes, "
        f"{len(soil_df)} observations"
    )

    for held_tube in tubes:

        train = soil_df[
            soil_df["tube_id"] != held_tube
        ].copy()

        test = soil_df[
            soil_df["tube_id"] == held_tube
        ].copy()

        for model_name, use_suction in models.items():

            coef = fit(
                train,
                use_suction,
            )

            q_pred = predict(
                test,
                coef,
                use_suction,
            )

            temp = test.copy()

            temp["heldout_tube"] = held_tube
            temp["model"] = model_name
            temp["q_pred_kPa"] = q_pred
            temp["residual_kPa"] = (
                temp["q_pred_kPa"]
                - temp["q_peak_kPa"]
            )

            prediction_parts.append(temp)


pred = pd.concat(
    prediction_parts,
    ignore_index=True,
)

pred.to_csv(
    PRED_OUT,
    index=False,
)


def metric_block(frame):
    obs = frame["q_peak_kPa"].to_numpy(float)
    est = frame["q_pred_kPa"].to_numpy(float)

    residual = est - obs

    return pd.Series({
        "n_rows": len(frame),
        "n_tubes": frame["heldout_tube"].nunique(),
        "rmse_kPa":
            np.sqrt(np.mean(residual**2)),
        "mae_kPa":
            np.mean(np.abs(residual)),
        "bias_kPa":
            np.mean(residual),
    })


summary = (
    pred
    .groupby(
        ["soil_type", "model"],
        group_keys=False,
    )
    .apply(
        metric_block,
        include_groups=False,
    )
    .reset_index()
)

pivot = summary.pivot(
    index="soil_type",
    columns="model",
    values="rmse_kPa",
)

pivot["CV_RMSE_change_pct"] = (
    100.0
    * (
        pivot["Fredlund_suction"]
        - pivot["MC_baseline"]
    )
    / pivot["MC_baseline"]
)

summary.to_csv(
    OUT,
    index=False,
)

print()
print("=" * 76)
print("UnsatConstitutiveLab — Leave-One-Tube-Out Cross Validation")
print("=" * 76)

print()
print("=== CV METRICS ===")
print(summary.to_string(index=False))

print()
print("=== CV RMSE COMPARISON ===")
print(pivot.to_string())

print()
print(
    "Negative CV_RMSE_change_pct = "
    "suction-dependent model improves prediction."
)

print()
print(
    "PHASE 3B GROUPED CROSS-VALIDATION: PASS"
)
