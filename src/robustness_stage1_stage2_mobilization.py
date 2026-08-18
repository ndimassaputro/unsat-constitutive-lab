from pathlib import Path

import numpy as np
import pandas as pd

CURVES = Path(
    "data/processed/stress_strain_master_v2.csv"
)

PARAMS = Path(
    "results/tables/incremental_mobilization_parameters.csv"
)

OUT_DESC = Path(
    "results/tables/stage1_stage2_q0_sensitivity_descriptors.csv"
)

OUT_TESTS = Path(
    "results/tables/stage1_stage2_q0_sensitivity_tests.csv"
)

OUT_SOIL = Path(
    "results/tables/stage1_stage2_soil_stratified_tests.csv"
)

for path in [
    OUT_DESC,
    OUT_TESTS,
    OUT_SOIL,
]:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

RNG = np.random.default_rng(
    20260818
)

N_BOOT = 50000

curves = pd.read_csv(
    CURVES
)

params = pd.read_csv(
    PARAMS
)

# ============================================================
# ONLY USABLE MULTISTAGE STAGES
# ============================================================

meta_cols = [
    "figure_id",
    "specimen_id",
    "stage_index",
    "stage",
    "tube_id",
    "soil_type",
    "family_normalized",
    "q_peak_kPa",
    "eps_peak_pct",
]

data = curves.merge(
    params[
        meta_cols
    ],
    on=[
        "figure_id",
        "specimen_id",
        "stage_index",
        "stage",
    ],
    how="inner",
    validate="many_to_one",
)

data = data[
    data[
        "family_normalized"
    ]
    == "multistage"
].copy()

# ============================================================
# ROBUSTNESS SCHEMES FOR q0
#
# q0 is estimated from the early fraction of the observed
# pre-peak branch:
#
#   2%, 5%, 10%, 15% of eps_peak
#
# This tests whether the candidate finding depends on one
# arbitrary stage-start stress convention.
# ============================================================

Q0_WINDOWS = [
    0.02,
    0.05,
    0.10,
    0.15,
]

TARGET_X = [
    0.25,
    0.50,
    0.75,
]

GRID = np.linspace(
    0.10,
    0.90,
    161,
)

descriptor_rows = []

group_cols = [
    "figure_id",
    "specimen_id",
    "stage_index",
    "stage",
]

for keys, frame in data.groupby(
    group_cols,
    sort=False,
):

    (
        figure_id,
        specimen_id,
        stage_index,
        stage,
    ) = keys

    # Strongest clean comparison:
    # stage 1 versus stage 2 only.
    if int(stage_index) not in [
        1,
        2,
    ]:
        continue

    first = frame.iloc[0]

    q_peak = float(
        first[
            "q_peak_kPa"
        ]
    )

    eps_peak = float(
        first[
            "eps_peak_pct"
        ]
    )

    if (
        q_peak <= 0
        or eps_peak <= 0
    ):
        continue

    pre = (
        frame[
            frame[
                "axial_strain_local_pct"
            ]
            <= eps_peak
            + 1e-9
        ]
        .dropna(
            subset=[
                "axial_strain_local_pct",
                "q_smooth_kPa",
            ]
        )
        .sort_values(
            "axial_strain_local_pct"
        )
        .copy()
    )

    if len(pre) < 20:
        continue

    eps = (
        pre[
            "axial_strain_local_pct"
        ]
        .to_numpy(float)
    )

    q = (
        pre[
            "q_smooth_kPa"
        ]
        .to_numpy(float)
    )

    for q0_fraction in Q0_WINDOWS:

        early = (
            eps
            <= q0_fraction
            * eps_peak
        )

        indices = np.where(
            early
        )[0]

        # Require at least three pixels.
        if len(indices) < 3:
            indices = np.arange(
                min(
                    3,
                    len(pre),
                )
            )

        q0 = float(
            np.median(
                q[
                    indices
                ]
            )
        )

        delta_peak = (
            q_peak
            - q0
        )

        if (
            delta_peak
            <= 0.15
            * q_peak
        ):
            continue

        x = (
            eps
            / eps_peak
        )

        y = (
            (
                q
                - q0
            )
            / delta_peak
        )

        valid = (
            np.isfinite(x)
            & np.isfinite(y)
            & (x >= -0.02)
            & (x <= 1.02)
        )

        x = x[
            valid
        ]

        y = y[
            valid
        ]

        if len(x) < 20:
            continue

        order = np.argsort(
            x
        )

        x = x[
            order
        ]

        y = y[
            order
        ]

        # Collapse duplicate x-values.
        temp = pd.DataFrame({
            "x":
                x,

            "y":
                y,
        })

        temp[
            "x_round"
        ] = (
            temp[
                "x"
            ].round(
                6
            )
        )

        temp = (
            temp.groupby(
                "x_round",
                as_index=False,
            )
            .agg(
                x=(
                    "x",
                    "mean",
                ),
                y=(
                    "y",
                    "median",
                ),
            )
            .sort_values(
                "x"
            )
        )

        x = (
            temp[
                "x"
            ].to_numpy(float)
        )

        y = (
            temp[
                "y"
            ].to_numpy(float)
        )

        if (
            x.min() > 0.10
            or x.max() < 0.90
        ):
            continue

        values = {}

        for target in TARGET_X:

            values[
                target
            ] = float(
                np.interp(
                    target,
                    x,
                    y,
                )
            )

        y_grid = np.interp(
            GRID,
            x,
            y,
        )

        mean_y = float(
            np.mean(
                y_grid
            )
        )

        descriptor_rows.append({
            "figure_id":
                figure_id,

            "specimen_id":
                specimen_id,

            "tube_id":
                first[
                    "tube_id"
                ],

            "soil_type":
                first[
                    "soil_type"
                ],

            "stage_index":
                int(
                    stage_index
                ),

            "q0_fraction":
                q0_fraction,

            "q0_kPa":
                q0,

            "q0_over_qpeak":
                q0
                / q_peak,

            "y25":
                values[
                    0.25
                ],

            "y50":
                values[
                    0.50
                ],

            "y75":
                values[
                    0.75
                ],

            "mean_y_10_90":
                mean_y,
        })


desc = pd.DataFrame(
    descriptor_rows
)

desc.to_csv(
    OUT_DESC,
    index=False,
)

# ============================================================
# CHECK COMPLETE STAGE1/STAGE2 PAIRS
# ============================================================

pair_counts = (
    desc.groupby(
        [
            "q0_fraction",
            "specimen_id",
        ]
    )[
        "stage_index"
    ]
    .nunique()
)

valid_pairs = (
    pair_counts[
        pair_counts == 2
    ]
    .reset_index()[
        [
            "q0_fraction",
            "specimen_id",
        ]
    ]
)

desc = desc.merge(
    valid_pairs,
    on=[
        "q0_fraction",
        "specimen_id",
    ],
    how="inner",
)

# ============================================================
# PAIRED DIFFERENCES
# ============================================================

METRICS = [
    "y25",
    "y50",
    "y75",
    "mean_y_10_90",
]

paired_rows = []

for (
    q0_fraction,
    specimen_id,
), frame in desc.groupby(
    [
        "q0_fraction",
        "specimen_id",
    ]
):

    stage1 = frame[
        frame[
            "stage_index"
        ]
        == 1
    ]

    stage2 = frame[
        frame[
            "stage_index"
        ]
        == 2
    ]

    if (
        stage1.empty
        or stage2.empty
    ):
        continue

    s1 = stage1.iloc[0]
    s2 = stage2.iloc[0]

    row = {
        "q0_fraction":
            q0_fraction,

        "specimen_id":
            specimen_id,

        "tube_id":
            s1[
                "tube_id"
            ],

        "soil_type":
            s1[
                "soil_type"
            ],
    }

    for metric in METRICS:

        row[
            f"delta_{metric}"
        ] = (
            float(
                s2[
                    metric
                ]
            )
            - float(
                s1[
                    metric
                ]
            )
        )

    paired_rows.append(
        row
    )


paired = pd.DataFrame(
    paired_rows
)

# ============================================================
# TUBE-CLUSTERED BOOTSTRAP
# ============================================================

def bootstrap_delta(
    frame,
    delta_col,
):

    tube = (
        frame.groupby(
            "tube_id",
            as_index=False,
        )
        .agg(
            delta=(
                delta_col,
                "mean",
            )
        )
    )

    values = (
        tube[
            "delta"
        ]
        .to_numpy(float)
    )

    if len(values) < 3:
        return None

    boot = np.empty(
        N_BOOT,
        dtype=float,
    )

    for i in range(
        N_BOOT
    ):

        sample = RNG.choice(
            values,
            size=len(values),
            replace=True,
        )

        boot[i] = float(
            np.mean(
                sample
            )
        )

    specimen_values = (
        frame[
            delta_col
        ]
        .to_numpy(float)
    )

    return {
        "n_specimens":
            frame[
                "specimen_id"
            ].nunique(),

        "n_tubes":
            len(
                values
            ),

        "mean_delta":
            float(
                np.mean(
                    values
                )
            ),

        "median_specimen_delta":
            float(
                np.median(
                    specimen_values
                )
            ),

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

        "prob_positive":
            float(
                np.mean(
                    boot > 0
                )
            ),

        "fraction_specimens_positive":
            float(
                np.mean(
                    specimen_values
                    > 0
                )
            ),
    }


# ============================================================
# OVERALL q0-SENSITIVITY TESTS
# ============================================================

test_rows = []

for q0_fraction, frame in paired.groupby(
    "q0_fraction"
):

    for metric in METRICS:

        result = bootstrap_delta(
            frame,
            f"delta_{metric}",
        )

        if result is None:
            continue

        test_rows.append({
            "q0_fraction":
                q0_fraction,

            "metric":
                metric,

            **result,
        })


tests = pd.DataFrame(
    test_rows
)

tests.to_csv(
    OUT_TESTS,
    index=False,
)

# ============================================================
# SOIL-STRATIFIED TEST
#
# Use the original 5% q0 window.
# Report only soil classes with >=3 independent tubes.
# ============================================================

main = paired[
    np.isclose(
        paired[
            "q0_fraction"
        ],
        0.05,
    )
].copy()

soil_rows = []

for soil_type, frame in main.groupby(
    "soil_type"
):

    if (
        frame[
            "tube_id"
        ].nunique()
        < 3
    ):
        continue

    for metric in METRICS:

        result = bootstrap_delta(
            frame,
            f"delta_{metric}",
        )

        if result is None:
            continue

        soil_rows.append({
            "soil_type":
                soil_type,

            "metric":
                metric,

            **result,
        })


soil_tests = pd.DataFrame(
    soil_rows
)

soil_tests.to_csv(
    OUT_SOIL,
    index=False,
)

# ============================================================
# REPORT
# ============================================================

print("=" * 96)
print(
    "UnsatConstitutiveLab — "
    "Phase 5H Stage-1/Stage-2 Robustness Battery"
)
print("=" * 96)

print()
print(
    "=== COVERAGE ==="
)

main_pairs = main[
    "specimen_id"
].nunique()

main_tubes = main[
    "tube_id"
].nunique()

print(
    "Stage1-stage2 specimen pairs:",
    main_pairs,
)

print(
    "Independent tubes           :",
    main_tubes,
)

print()
print(
    "=== q0 WINDOW SENSITIVITY ==="
)

print(
    tests.to_string(
        index=False
    )
)

print()
print(
    "=== SOIL-STRATIFIED STAGE1 -> STAGE2 ==="
)

if soil_tests.empty:

    print(
        "No soil class has sufficient independent tubes."
    )

else:

    print(
        soil_tests.to_string(
            index=False
        )
    )

print()
print(
    "DECISION RULE"
)

print(
    "Robust candidate finding requires:"
)

print(
    "1) stage1 -> stage2 deltas positive for y25, y50, "
    "y75 and mean_y;"
)

print(
    "2) the sign and practical magnitude persist across "
    "q0 windows 2%-15%;"
)

print(
    "3) the result is not carried entirely by one soil class."
)

print()
print(
    "If these pass, exploratory analysis stops."
)

print(
    "Next = literature novelty audit + final constitutive "
    "formulation + publication-quality figures."
)

print()
print(
    "Outputs:"
)

for path in [
    OUT_DESC,
    OUT_TESTS,
    OUT_SOIL,
]:
    print(
        " ",
        path,
    )

print()
print(
    "PHASE 5H STAGE1/STAGE2 ROBUSTNESS: PASS"
)
