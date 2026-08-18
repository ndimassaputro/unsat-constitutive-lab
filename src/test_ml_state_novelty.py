from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

SRC = Path("data/processed/strength_analysis_ready.csv")
OUT = Path("results/tables/ml_state_novelty_test.csv")
PRED_OUT = Path("data/processed/ml_state_novelty_predictions.csv")

OUT.parent.mkdir(parents=True, exist_ok=True)
PRED_OUT.parent.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(20260818)
N_BOOT = 5000

df = pd.read_csv(SRC)

df = df[
    df["soil_type"] == "ML"
].copy()

print("=" * 78)
print("UnsatConstitutiveLab — ML Matched-Complexity State Test")
print("=" * 78)
print()
print("Rows :", len(df))
print("Tubes:", df["tube_id"].nunique())


def weights(frame):
    n = (
        frame.groupby("tube_id")["tube_id"]
        .transform("size")
        .to_numpy(float)
    )
    return 1.0 / np.sqrt(n)


def matrices(train, test, model):

    sigma_tr = train["sigma_c_net_kPa"].to_numpy(float)
    psi_tr = train["matric_suction_kPa"].to_numpy(float)
    sr_tr = train["degree_saturation"].to_numpy(float)
    gd_tr = train["gamma_d_g_cm3"].to_numpy(float)

    sigma_te = test["sigma_c_net_kPa"].to_numpy(float)
    psi_te = test["matric_suction_kPa"].to_numpy(float)
    sr_te = test["degree_saturation"].to_numpy(float)
    gd_te = test["gamma_d_g_cm3"].to_numpy(float)

    psi_scale = np.std(psi_tr, ddof=1)
    sr_mean = np.mean(sr_tr)
    gd_mean = np.mean(gd_tr)

    if psi_scale <= 0:
        raise ValueError("Zero suction variance.")

    psi_tr_z = psi_tr / psi_scale
    psi_te_z = psi_te / psi_scale

    base_tr = [
        np.ones(len(train)),
        sigma_tr,
        psi_tr,
    ]

    base_te = [
        np.ones(len(test)),
        sigma_te,
        psi_te,
    ]

    if model == "Fredlund":
        pass

    elif model == "Nonlinear_suction":
        base_tr.append(psi_tr_z ** 2)
        base_te.append(psi_te_z ** 2)

    elif model == "Saturation_additive":
        base_tr.append(sr_tr - sr_mean)
        base_te.append(sr_te - sr_mean)

    elif model == "Saturation_interaction":
        base_tr.append(
            psi_tr_z * (sr_tr - sr_mean)
        )
        base_te.append(
            psi_te_z * (sr_te - sr_mean)
        )

    elif model == "Density_additive":
        base_tr.append(gd_tr - gd_mean)
        base_te.append(gd_te - gd_mean)

    else:
        raise ValueError(model)

    return (
        np.column_stack(base_tr),
        np.column_stack(base_te),
    )


def fit_predict(train, test, model):
    Xtr, Xte = matrices(
        train,
        test,
        model,
    )

    y = train["q_peak_kPa"].to_numpy(float)
    w = weights(train)

    ncoef = Xtr.shape[1]

    lower = np.full(ncoef, -np.inf)
    upper = np.full(ncoef, np.inf)

    # Intercept, net-stress coefficient,
    # and base suction coefficient nonnegative.
    lower[0:3] = 0.0

    fit = lsq_linear(
        Xtr * w[:, None],
        y * w,
        bounds=(lower, upper),
    )

    if not fit.success:
        raise RuntimeError(fit.message)

    return Xte @ fit.x


MODELS = [
    "Fredlund",
    "Nonlinear_suction",
    "Saturation_additive",
    "Saturation_interaction",
    "Density_additive",
]

parts = []

for heldout_tube in sorted(
    df["tube_id"].unique()
):
    train = df[
        df["tube_id"] != heldout_tube
    ].copy()

    test = df[
        df["tube_id"] == heldout_tube
    ].copy()

    for model in MODELS:
        pred = fit_predict(
            train,
            test,
            model,
        )

        temp = test[
            [
                "tube_id",
                "specimen_id",
                "stage",
                "q_peak_kPa",
            ]
        ].copy()

        temp["heldout_tube"] = heldout_tube
        temp["model"] = model
        temp["q_pred_kPa"] = pred
        temp["residual_kPa"] = (
            pred
            - temp["q_peak_kPa"].to_numpy(float)
        )

        parts.append(temp)

pred = pd.concat(
    parts,
    ignore_index=True,
)

pred.to_csv(
    PRED_OUT,
    index=False,
)


def rmse(frame):
    return float(
        np.sqrt(
            np.mean(
                frame["residual_kPa"].to_numpy(float) ** 2
            )
        )
    )


baseline = pred[
    pred["model"] == "Fredlund"
].copy()

baseline_rmse = rmse(baseline)

rows = []

for model in MODELS:

    candidate = pred[
        pred["model"] == model
    ].copy()

    candidate_rmse = rmse(candidate)

    change = (
        100.0
        * (
            candidate_rmse
            - baseline_rmse
        )
        / baseline_rmse
    )

    if model == "Fredlund":
        rows.append({
            "model": model,
            "rmse_kPa": candidate_rmse,
            "rmse_change_vs_Fredlund_pct": 0.0,
            "bootstrap_p025_pct": 0.0,
            "bootstrap_p975_pct": 0.0,
            "bootstrap_prob_improvement": np.nan,
        })
        continue

    merged = (
        baseline[
            [
                "tube_id",
                "specimen_id",
                "stage",
                "q_peak_kPa",
                "q_pred_kPa",
            ]
        ]
        .rename(
            columns={
                "q_pred_kPa": "base_pred"
            }
        )
        .merge(
            candidate[
                [
                    "tube_id",
                    "specimen_id",
                    "stage",
                    "q_pred_kPa",
                ]
            ].rename(
                columns={
                    "q_pred_kPa": "candidate_pred"
                }
            ),
            on=[
                "tube_id",
                "specimen_id",
                "stage",
            ],
            validate="one_to_one",
        )
    )

    tubes = sorted(
        merged["tube_id"].unique()
    )

    groups = {
        tube: merged[
            merged["tube_id"] == tube
        ]
        for tube in tubes
    }

    boot = []

    for _ in range(N_BOOT):

        sampled = RNG.choice(
            tubes,
            size=len(tubes),
            replace=True,
        )

        obs = []
        base_values = []
        candidate_values = []

        for tube in sampled:
            g = groups[tube]

            obs.append(
                g["q_peak_kPa"].to_numpy(float)
            )

            base_values.append(
                g["base_pred"].to_numpy(float)
            )

            candidate_values.append(
                g["candidate_pred"].to_numpy(float)
            )

        obs = np.concatenate(obs)
        base_values = np.concatenate(base_values)
        candidate_values = np.concatenate(candidate_values)

        r0 = np.sqrt(
            np.mean(
                (base_values - obs) ** 2
            )
        )

        r1 = np.sqrt(
            np.mean(
                (candidate_values - obs) ** 2
            )
        )

        boot.append(
            100.0 * (r1 - r0) / r0
        )

    boot = np.asarray(boot)

    rows.append({
        "model": model,
        "rmse_kPa": candidate_rmse,
        "rmse_change_vs_Fredlund_pct": change,
        "bootstrap_p025_pct":
            np.quantile(boot, 0.025),
        "bootstrap_p975_pct":
            np.quantile(boot, 0.975),
        "bootstrap_prob_improvement":
            np.mean(boot < 0),
    })


result = pd.DataFrame(rows)

result.to_csv(
    OUT,
    index=False,
)

print()
print("=== MATCHED-COMPLEXITY CV RESULTS ===")
print(
    result.to_string(
        index=False
    )
)

print()
print("Interpretation:")
print(
    "- If Nonlinear_suction wins, Sr may only proxy "
    "nonlinear suction response."
)
print(
    "- If Saturation_additive or Saturation_interaction "
    "beats Nonlinear_suction robustly, Sr carries "
    "additional predictive information."
)
print(
    "- Saturation_interaction specifically tests whether "
    "the suction contribution changes with saturation state."
)
print(
    "- Density_additive is a confounding-control model."
)

print()
print(
    "PHASE 3D ML STATE NOVELTY TEST: PASS"
)
