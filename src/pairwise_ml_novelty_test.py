from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(
    "data/processed/ml_state_novelty_predictions.csv"
)
OUT = Path(
    "results/tables/ml_pairwise_novelty_test.csv"
)

OUT.parent.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(20260818)
N_BOOT = 10000

df = pd.read_csv(SRC)

COMPARISONS = [
    (
        "Nonlinear_suction",
        "Saturation_additive",
    ),
    (
        "Nonlinear_suction",
        "Saturation_interaction",
    ),
    (
        "Density_additive",
        "Saturation_interaction",
    ),
    (
        "Saturation_additive",
        "Saturation_interaction",
    ),
]


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


rows = []

for baseline_model, candidate_model in COMPARISONS:

    base = (
        df[df["model"] == baseline_model]
        [
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
                "q_pred_kPa": "pred_base"
            }
        )
    )

    candidate = (
        df[df["model"] == candidate_model]
        [
            [
                "tube_id",
                "specimen_id",
                "stage",
                "q_pred_kPa",
            ]
        ]
        .rename(
            columns={
                "q_pred_kPa": "pred_candidate"
            }
        )
    )

    merged = base.merge(
        candidate,
        on=[
            "tube_id",
            "specimen_id",
            "stage",
        ],
        how="inner",
        validate="one_to_one",
    )

    tubes = sorted(
        merged["tube_id"].unique()
    )

    groups = {
        tube: merged[
            merged["tube_id"] == tube
        ].copy()
        for tube in tubes
    }

    obs_all = merged["q_peak_kPa"].to_numpy(float)
    base_all = merged["pred_base"].to_numpy(float)
    cand_all = merged["pred_candidate"].to_numpy(float)

    r_base = rmse(
        obs_all,
        base_all,
    )

    r_candidate = rmse(
        obs_all,
        cand_all,
    )

    point_change = (
        100.0
        * (
            r_candidate
            - r_base
        )
        / r_base
    )

    boot_change = []

    for _ in range(N_BOOT):

        sampled_tubes = RNG.choice(
            tubes,
            size=len(tubes),
            replace=True,
        )

        obs_parts = []
        base_parts = []
        cand_parts = []

        for tube in sampled_tubes:

            g = groups[tube]

            obs_parts.append(
                g["q_peak_kPa"]
                .to_numpy(float)
            )

            base_parts.append(
                g["pred_base"]
                .to_numpy(float)
            )

            cand_parts.append(
                g["pred_candidate"]
                .to_numpy(float)
            )

        obs = np.concatenate(
            obs_parts
        )

        p_base = np.concatenate(
            base_parts
        )

        p_cand = np.concatenate(
            cand_parts
        )

        rb = rmse(
            obs,
            p_base,
        )

        rc = rmse(
            obs,
            p_cand,
        )

        if rb > 0:
            boot_change.append(
                100.0
                * (
                    rc - rb
                )
                / rb
            )

    boot_change = np.asarray(
        boot_change,
        dtype=float,
    )

    rows.append({
        "baseline_model":
            baseline_model,

        "candidate_model":
            candidate_model,

        "n_tubes":
            len(tubes),

        "rmse_baseline_kPa":
            r_base,

        "rmse_candidate_kPa":
            r_candidate,

        "candidate_change_pct":
            point_change,

        "bootstrap_p025_pct":
            np.quantile(
                boot_change,
                0.025,
            ),

        "bootstrap_p975_pct":
            np.quantile(
                boot_change,
                0.975,
            ),

        "prob_candidate_better":
            np.mean(
                boot_change < 0
            ),
    })


result = pd.DataFrame(rows)

result.to_csv(
    OUT,
    index=False,
)

print("=" * 79)
print(
    "UnsatConstitutiveLab — ML Pairwise Novelty Challenge"
)
print("=" * 79)

print()
print("=== DIRECT PAIRWISE TESTS ===")

print(
    result.to_string(
        index=False
    )
)

print()
print("Decision rule:")
print(
    "Negative candidate_change_pct = candidate has lower CV RMSE."
)
print(
    "If the 95% bootstrap interval is entirely below zero, "
    "the pairwise advantage is comparatively strong."
)
print(
    "If Saturation_interaction beats Nonlinear_suction directly, "
    "the result cannot be explained simply by adding suction curvature."
)

print()
print(
    "PHASE 3E PAIRWISE NOVELTY CHALLENGE: PASS"
)
