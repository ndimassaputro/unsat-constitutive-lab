from pathlib import Path
import math

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

SRC = Path("data/processed/strength_analysis_ready.csv")
PARAM_OUT = Path("results/tables/strength_model_parameters.csv")
METRIC_OUT = Path("results/tables/strength_model_metrics.csv")
PRED_OUT = Path("data/processed/strength_model_predictions.csv")

PARAM_OUT.parent.mkdir(parents=True, exist_ok=True)
PRED_OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SRC)


def tube_weights(frame):
    counts = frame.groupby("tube_id")["tube_id"].transform("size")
    return 1.0 / np.sqrt(counts.to_numpy(dtype=float))


def fit_model(frame, include_suction):
    sigma = frame["sigma_c_net_kPa"].to_numpy(float)
    suction = frame["matric_suction_kPa"].to_numpy(float)
    q = frame["q_peak_kPa"].to_numpy(float)

    if include_suction:
        X = np.column_stack([
            np.ones(len(frame)),
            sigma,
            suction,
        ])
    else:
        X = np.column_stack([
            np.ones(len(frame)),
            sigma,
        ])

    w = tube_weights(frame)

    result = lsq_linear(
        X * w[:, None],
        q * w,
        bounds=(0.0, np.inf),
    )

    if not result.success:
        raise RuntimeError(result.message)

    return result.x


def predict(frame, coef, include_suction):
    sigma = frame["sigma_c_net_kPa"].to_numpy(float)
    suction = frame["matric_suction_kPa"].to_numpy(float)

    if include_suction:
        A, B, D = coef
        return A + B * sigma + D * suction

    A, B = coef
    return A + B * sigma


def physical_parameters(coef, include_suction):
    A = float(coef[0])
    B = float(coef[1])

    Nphi = B + 1.0

    sin_phi = (Nphi - 1.0) / (Nphi + 1.0)
    sin_phi = np.clip(sin_phi, -0.999999, 0.999999)

    phi_prime_deg = math.degrees(math.asin(sin_phi))
    c_prime_kPa = A / (2.0 * math.sqrt(Nphi))

    if include_suction:
        D = float(coef[2])
        tan_phi_b = D / (2.0 * math.sqrt(Nphi))
        phi_b_deg = math.degrees(math.atan(tan_phi_b))
    else:
        D = 0.0
        phi_b_deg = 0.0

    return {
        "A_kPa": A,
        "B_sigma": B,
        "D_suction": D,
        "c_prime_kPa": c_prime_kPa,
        "phi_prime_deg": phi_prime_deg,
        "phi_b_deg": phi_b_deg,
    }


def calc_metrics(obs, pred):
    obs = np.asarray(obs, float)
    pred = np.asarray(pred, float)

    residual = pred - obs

    rmse = float(np.sqrt(np.mean(residual**2)))
    mae = float(np.mean(np.abs(residual)))
    bias = float(np.mean(residual))

    if len(obs) >= 2 and np.ptp(obs) > 0:
        r2 = 1.0 - (
            np.sum((obs - pred)**2)
            / np.sum((obs - np.mean(obs))**2)
        )
        nrmse = rmse / np.ptp(obs)
    else:
        r2 = np.nan
        nrmse = np.nan

    return {
        "n_rows": len(obs),
        "rmse_kPa": rmse,
        "mae_kPa": mae,
        "bias_kPa": bias,
        "r2": float(r2),
        "nrmse_range": float(nrmse),
    }


def predictor_diagnostics(frame):
    sigma = frame["sigma_c_net_kPa"].to_numpy(float)
    suction = frame["matric_suction_kPa"].to_numpy(float)

    if len(frame) < 3:
        return np.nan, np.nan

    corr = float(np.corrcoef(sigma, suction)[0, 1])

    z_sigma = (
        (sigma - sigma.mean())
        / sigma.std(ddof=1)
    )
    z_suction = (
        (suction - suction.mean())
        / suction.std(ddof=1)
    )

    Z = np.column_stack([z_sigma, z_suction])
    condition = float(np.linalg.cond(Z))

    return corr, condition


parameter_rows = []
metric_rows = []
prediction_rows = []

for soil in sorted(df["soil_type"].unique()):

    sub = df[df["soil_type"] == soil].copy()

    calibration = sub[
        sub["proposed_split"] == "calibration"
    ].copy()

    holdout = sub[
        sub["proposed_split"] == "holdout"
    ].copy()

    corr, condition = predictor_diagnostics(calibration)

    MODELS = {
        "MC_baseline": False,
        "Fredlund_suction": True,
    }

    for model_name, include_suction in MODELS.items():

        coef = fit_model(
            calibration,
            include_suction,
        )

        pars = physical_parameters(
            coef,
            include_suction,
        )

        parameter_rows.append({
            "soil_type": soil,
            "model": model_name,
            "calibration_rows": len(calibration),
            "calibration_tubes":
                calibration["tube_id"].nunique(),
            **pars,
            "predictor_corr_sigma_suction": corr,
            "predictor_condition_standardized": condition,
            "qc_phi_b_gt_phi_prime":
                pars["phi_b_deg"] > pars["phi_prime_deg"],
        })

        for split_name, frame in [
            ("calibration", calibration),
            ("holdout", holdout),
        ]:

            if frame.empty:
                continue

            q_pred = predict(
                frame,
                coef,
                include_suction,
            )

            stats = calc_metrics(
                frame["q_peak_kPa"],
                q_pred,
            )

            metric_rows.append({
                "soil_type": soil,
                "model": model_name,
                "split": split_name,
                "n_tubes": frame["tube_id"].nunique(),
                **stats,
            })

            temp = frame.copy()
            temp["model"] = model_name
            temp["q_pred_kPa"] = q_pred
            temp["residual_kPa"] = (
                temp["q_pred_kPa"]
                - temp["q_peak_kPa"]
            )

            prediction_rows.append(temp)


params = pd.DataFrame(parameter_rows)
metrics = pd.DataFrame(metric_rows)
predictions = pd.concat(
    prediction_rows,
    ignore_index=True,
)

params.to_csv(PARAM_OUT, index=False)
metrics.to_csv(METRIC_OUT, index=False)
predictions.to_csv(PRED_OUT, index=False)


holdout_metrics = metrics[
    metrics["split"] == "holdout"
].copy()

comparison = holdout_metrics.pivot(
    index="soil_type",
    columns="model",
    values="rmse_kPa",
)

comparison["holdout_RMSE_change_pct"] = (
    100.0
    * (
        comparison["Fredlund_suction"]
        - comparison["MC_baseline"]
    )
    / comparison["MC_baseline"]
)


print("=" * 78)
print("UnsatConstitutiveLab — Phase 3A Strength Models")
print("=" * 78)

print()
print("=== PARAMETERS ===")

print(
    params[
        [
            "soil_type",
            "model",
            "calibration_rows",
            "calibration_tubes",
            "c_prime_kPa",
            "phi_prime_deg",
            "phi_b_deg",
            "predictor_corr_sigma_suction",
            "predictor_condition_standardized",
            "qc_phi_b_gt_phi_prime",
        ]
    ].to_string(index=False)
)

print()
print("=== HOLDOUT RMSE COMPARISON ===")
print(comparison.to_string())

print()
print(
    "Negative RMSE change = suction model improves "
    "holdout prediction."
)
print(
    "SC has only one holdout observation; "
    "treat SC validation as exploratory."
)

print()
print("PHASE 3A STRENGTH MODEL FITTING: PASS")
