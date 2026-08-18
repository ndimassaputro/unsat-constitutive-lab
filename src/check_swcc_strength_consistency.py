from pathlib import Path

import numpy as np
import pandas as pd

STRENGTH = Path(
    "data/processed/strength_analysis_ready.csv"
)
SWCC = Path(
    "data/processed/swcc_e3_parameters.csv"
)

OUT = Path(
    "data/processed/swcc_strength_matched.csv"
)
SUMMARY_OUT = Path(
    "results/tables/swcc_strength_consistency.csv"
)

OUT.parent.mkdir(parents=True, exist_ok=True)
SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)

PSI_R_KPA = 3000.0
PSI_ZERO_KPA = 1.0e6

strength = pd.read_csv(STRENGTH)
swcc = pd.read_csv(SWCC)

# ------------------------------------------------------------
# MATCH
# Many triaxial stages may map to one SWCC tube.
# ------------------------------------------------------------

matched = strength.merge(
    swcc,
    on="tube_id",
    how="inner",
    suffixes=("_triaxial", "_swcc"),
    validate="many_to_one",
)

if matched.empty:
    raise SystemExit(
        "No matching strength/SWCC tubes."
    )

# ------------------------------------------------------------
# Fredlund-Xing (1994) SWCC
#
# theta(psi) / theta_s =
#
# C(psi) /
# [ ln(e + (psi/a)^n) ]^m
#
# C(psi) =
# 1 - ln(1 + psi/psi_r) /
#     ln(1 + 1e6/psi_r)
#
# We call this normalized water content Theta_FX.
# It is compared with measured degree of saturation as
# a consistency diagnostic, not assumed identical a priori.
# ------------------------------------------------------------

psi = matched[
    "matric_suction_kPa"
].to_numpy(float)

a = matched[
    "a_kPa"
].to_numpy(float)

n = matched[
    "n"
].to_numpy(float)

m = matched[
    "m"
].to_numpy(float)

correction = (
    1.0
    - np.log(
        1.0 + psi / PSI_R_KPA
    )
    / np.log(
        1.0 + PSI_ZERO_KPA / PSI_R_KPA
    )
)

denominator = (
    np.log(
        np.e
        + (psi / a) ** n
    )
    ** m
)

theta_norm_fx = (
    correction
    / denominator
)

matched[
    "fx_normalized_water_content"
] = theta_norm_fx

matched[
    "fx_theta_volumetric"
] = (
    matched["theta_s"]
    * matched[
        "fx_normalized_water_content"
    ]
)

matched[
    "fx_minus_measured_S"
] = (
    matched[
        "fx_normalized_water_content"
    ]
    - matched[
        "degree_saturation"
    ]
)

matched[
    "rho_d_difference_g_cm3"
] = (
    matched[
        "gamma_d_g_cm3"
    ]
    - matched[
        "rho_d_g_cm3"
    ]
)

# ------------------------------------------------------------
# QC
# ------------------------------------------------------------

if (
    matched[
        "fx_normalized_water_content"
    ] < 0
).any():
    raise SystemExit(
        "Negative FX normalized water content found."
    )

if (
    matched[
        "fx_normalized_water_content"
    ] > 1.05
).any():
    print(
        "WARNING: FX normalized water content "
        "exceeds 1.05 for at least one row."
    )

matched.to_csv(
    OUT,
    index=False,
)


def summarize(group):
    err = group[
        "fx_minus_measured_S"
    ].to_numpy(float)

    measured = group[
        "degree_saturation"
    ].to_numpy(float)

    predicted = group[
        "fx_normalized_water_content"
    ].to_numpy(float)

    rho_diff = group[
        "rho_d_difference_g_cm3"
    ].to_numpy(float)

    if (
        len(group) >= 2
        and np.std(measured) > 0
        and np.std(predicted) > 0
    ):
        corr = np.corrcoef(
            measured,
            predicted,
        )[0, 1]
    else:
        corr = np.nan

    return pd.Series({
        "n_rows":
            len(group),

        "n_tubes":
            group[
                "tube_id"
            ].nunique(),

        "S_RMSE":
            np.sqrt(
                np.mean(
                    err ** 2
                )
            ),

        "S_MAE":
            np.mean(
                np.abs(err)
            ),

        "S_bias_FX_minus_measured":
            np.mean(err),

        "S_correlation":
            corr,

        "rho_d_MAE_g_cm3":
            np.mean(
                np.abs(
                    rho_diff
                )
            ),

        "suction_min_kPa":
            group[
                "matric_suction_kPa"
            ].min(),

        "suction_max_kPa":
            group[
                "matric_suction_kPa"
            ].max(),
    })


summary = (
    matched
    .groupby(
        "soil_type",
        group_keys=False,
    )
    .apply(
        summarize,
        include_groups=False,
    )
    .reset_index()
)

summary.to_csv(
    SUMMARY_OUT,
    index=False,
)

print("=" * 78)
print(
    "UnsatConstitutiveLab — "
    "SWCC / Triaxial Consistency Audit"
)
print("=" * 78)

print()
print("Matched rows :", len(matched))
print(
    "Matched tubes:",
    matched["tube_id"].nunique(),
)

print()
print("=== MATCHED TUBES ===")

tube_table = (
    matched[
        [
            "soil_type",
            "tube_id",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        [
            "soil_type",
            "tube_id",
        ]
    )
)

print(
    tube_table.to_string(
        index=False
    )
)

print()
print("=== CONSISTENCY SUMMARY ===")
print(
    summary.to_string(
        index=False
    )
)

print()
print("=== ML ROW PREVIEW ===")

ml = matched[
    matched["soil_type"]
    == "ML"
][
    [
        "tube_id",
        "specimen_id",
        "stage",
        "matric_suction_kPa",
        "degree_saturation",
        "fx_normalized_water_content",
        "fx_minus_measured_S",
        "gamma_d_g_cm3",
        "rho_d_g_cm3",
        "rho_d_difference_g_cm3",
    ]
]

print(
    ml.to_string(
        index=False
    )
)

print()
print(
    "PHASE 3G SWCC-STRENGTH CONSISTENCY: PASS"
)
