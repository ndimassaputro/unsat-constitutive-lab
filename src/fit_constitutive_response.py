from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

CURVES = Path(
    "data/processed/stress_strain_master_v2.csv"
)

QC = Path(
    "results/tables/stress_strain_digitization_qc_v2.csv"
)

STRENGTH = Path(
    "data/processed/strength_analysis_ready.csv"
)

METRICS_OUT = Path(
    "results/tables/constitutive_curve_parameters.csv"
)

PRED_OUT = Path(
    "data/processed/constitutive_curve_fit_predictions.csv"
)

METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
PRED_OUT.parent.mkdir(parents=True, exist_ok=True)

USABLE = {
    "PASS",
    "USABLE_REVIEW_X",
}

curves = pd.read_csv(CURVES)
qc = pd.read_csv(QC)
strength = pd.read_csv(STRENGTH)

usable_qc = qc[
    qc["status"].isin(USABLE)
].copy()

curves = curves.merge(
    usable_qc[
        [
            "figure_id",
            "specimen_id",
            "status",
            "x_method",
            "x_max_pct",
            "peak_error_mean_abs_pct",
            "y_scale_cv_across_stages",
        ]
    ],
    on=[
        "figure_id",
        "specimen_id",
    ],
    how="inner",
    validate="many_to_one",
)

meta_columns = [
    "specimen_id",
    "stage",
    "tube_id",
    "soil_type",
    "test_family",
    "area",
    "sigma_c_net_kPa",
    "matric_suction_kPa",
    "gamma_d_g_cm3",
    "degree_saturation",
]

meta = strength[
    meta_columns
].drop_duplicates(
    [
        "specimen_id",
        "stage",
    ]
)

curves = curves.merge(
    meta,
    on=[
        "specimen_id",
        "stage",
    ],
    how="left",
    suffixes=(
        "",
        "_meta",
    ),
    validate="many_to_one",
)

if curves["soil_type"].isna().any():
    bad = curves.loc[
        curves["soil_type"].isna(),
        [
            "figure_id",
            "specimen_id",
            "stage",
        ],
    ].drop_duplicates()

    print("UNRESOLVED METADATA:")
    print(
        bad.to_string(
            index=False
        )
    )

    raise SystemExit(
        "PHASE 5A CONSTITUTIVE FIT: FAIL"
    )


# ============================================================
# HELPERS
# ============================================================

def deduplicate_curve(frame):

    frame = frame[
        [
            "axial_strain_local_pct",
            "deviator_stress_kPa",
            "q_smooth_kPa",
        ]
    ].dropna().copy()

    frame = frame[
        frame[
            "axial_strain_local_pct"
        ] >= 0
    ].copy()

    # Multiple pixels may map to effectively identical strain.
    frame["strain_round"] = (
        frame[
            "axial_strain_local_pct"
        ].round(5)
    )

    frame = (
        frame.groupby(
            "strain_round",
            as_index=False,
        )
        .agg(
            axial_strain_local_pct=(
                "axial_strain_local_pct",
                "mean",
            ),
            deviator_stress_kPa=(
                "deviator_stress_kPa",
                "median",
            ),
            q_smooth_kPa=(
                "q_smooth_kPa",
                "median",
            ),
        )
        .sort_values(
            "axial_strain_local_pct"
        )
        .reset_index(
            drop=True
        )
    )

    return frame


def interpolate_first_crossing(
    strain,
    q,
    target,
):

    strain = np.asarray(
        strain,
        float,
    )

    q = np.asarray(
        q,
        float,
    )

    above = np.where(
        q >= target
    )[0]

    if len(above) == 0:
        return np.nan

    j = int(
        above[0]
    )

    if j == 0:
        return float(
            strain[0]
        )

    x0 = strain[j - 1]
    x1 = strain[j]

    y0 = q[j - 1]
    y1 = q[j]

    if np.isclose(
        y1,
        y0,
    ):
        return float(
            x1
        )

    fraction = (
        target
        - y0
    ) / (
        y1
        - y0
    )

    return float(
        x0
        + fraction
        * (
            x1
            - x0
        )
    )


def fit_prepeak(
    strain_pct,
    q,
    q_peak,
    eps_peak_pct,
):
    """
    Normalized hyperbolic mobilization:

        q/q_peak =
        x(1 + lambda) / (1 + lambda*x)

        x = eps / eps_peak

    lambda >= 0 controls curvature.
    """

    strain_pct = np.asarray(
        strain_pct,
        float,
    )

    q = np.asarray(
        q,
        float,
    )

    x = (
        strain_pct
        / eps_peak_pct
    )

    y = (
        q
        / q_peak
    )

    valid = (
        (x >= 0)
        & (x <= 1.001)
        & np.isfinite(x)
        & np.isfinite(y)
    )

    x = x[
        valid
    ]

    y = y[
        valid
    ]

    if len(x) < 12:
        return None

    def prediction(
        lam,
    ):
        return (
            x
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

    def residual(
        parameter,
    ):
        lam = float(
            parameter[0]
        )

        return (
            prediction(
                lam
            )
            - y
        )

    fit = least_squares(
        residual,
        x0=np.array(
            [2.0]
        ),
        bounds=(
            np.array(
                [0.0]
            ),
            np.array(
                [100.0]
            ),
        ),
        loss="soft_l1",
        f_scale=0.05,
    )

    lam = float(
        fit.x[0]
    )

    pred_norm = (
        prediction(
            lam
        )
    )

    rmse_norm = float(
        np.sqrt(
            np.mean(
                (
                    pred_norm
                    - y
                ) ** 2
            )
        )
    )

    # Initial tangent modulus.
    #
    # eps_peak converted from percent to dimensionless strain.
    eps_peak_decimal = (
        eps_peak_pct
        / 100.0
    )

    E_i_kPa = (
        q_peak
        * (
            1.0
            + lam
        )
        / eps_peak_decimal
    )

    return {
        "lambda_mobilization":
            lam,

        "E_i_model_MPa":
            E_i_kPa
            / 1000.0,

        "prepeak_nrmse":
            rmse_norm,
    }


def fit_postpeak(
    strain_pct,
    q,
    q_peak,
    eps_peak_pct,
):
    """
    Normalized exponential post-peak model:

      q/q_peak =
      r + (1-r)*exp[-beta*(eps-eps_peak)]

    beta units: 1 / percent axial strain.
    """

    strain_pct = np.asarray(
        strain_pct,
        float,
    )

    q = np.asarray(
        q,
        float,
    )

    delta = (
        strain_pct
        - eps_peak_pct
    )

    y = (
        q
        / q_peak
    )

    valid = (
        (delta >= 0)
        & np.isfinite(
            delta
        )
        & np.isfinite(
            y
        )
    )

    delta = delta[
        valid
    ]

    y = y[
        valid
    ]

    if len(delta) < 12:
        return None

    strain_span = float(
        np.max(
            delta
        )
        - np.min(
            delta
        )
    )

    if strain_span < 0.35:
        return None

    # If the available response barely drops from peak,
    # classify as hardening/truncated instead of forcing
    # a softening mechanism.
    observed_drop = (
        1.0
        - float(
            np.median(
                y[
                    max(
                        0,
                        int(
                            0.85
                            * len(y)
                        ),
                    ):
                ]
            )
        )
    )

    if observed_drop < 0.025:
        return {
            "postpeak_available":
                False,

            "postpeak_reason":
                "hardening_or_truncated",

            "residual_ratio_model":
                np.nan,

            "beta_softening_per_pct":
                np.nan,

            "postpeak_nrmse":
                np.nan,
        }

    def prediction(
        r,
        beta,
    ):
        return (
            r
            + (
                1.0
                - r
            )
            * np.exp(
                -beta
                * delta
            )
        )

    def residual(
        parameter,
    ):
        r = float(
            parameter[0]
        )

        beta = float(
            parameter[1]
        )

        return (
            prediction(
                r,
                beta,
            )
            - y
        )

    tail = float(
        np.median(
            y[
                max(
                    0,
                    int(
                        0.85
                        * len(y)
                    ),
                ):
            ]
        )
    )

    r0 = float(
        np.clip(
            tail,
            0.0,
            1.0,
        )
    )

    fit = least_squares(
        residual,
        x0=np.array(
            [
                r0,
                0.5,
            ]
        ),
        bounds=(
            np.array(
                [
                    0.0,
                    0.0,
                ]
            ),
            np.array(
                [
                    1.20,
                    20.0,
                ]
            ),
        ),
        loss="soft_l1",
        f_scale=0.05,
    )

    r = float(
        fit.x[0]
    )

    beta = float(
        fit.x[1]
    )

    pred_norm = (
        prediction(
            r,
            beta,
        )
    )

    rmse_norm = float(
        np.sqrt(
            np.mean(
                (
                    pred_norm
                    - y
                ) ** 2
            )
        )
    )

    return {
        "postpeak_available":
            True,

        "postpeak_reason":
            "fitted",

        "residual_ratio_model":
            r,

        "beta_softening_per_pct":
            beta,

        "postpeak_nrmse":
            rmse_norm,
    }


def evaluate_piecewise(
    strain_pct,
    q_peak,
    eps_peak_pct,
    pre,
    post,
):

    strain_pct = np.asarray(
        strain_pct,
        float,
    )

    pred = np.full(
        len(
            strain_pct
        ),
        np.nan,
        dtype=float,
    )

    pre_mask = (
        strain_pct
        <= eps_peak_pct
    )

    x = (
        strain_pct[
            pre_mask
        ]
        / eps_peak_pct
    )

    lam = pre[
        "lambda_mobilization"
    ]

    pred[
        pre_mask
    ] = (
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

    post_mask = (
        ~pre_mask
    )

    if (
        post is not None
        and post.get(
            "postpeak_available",
            False,
        )
    ):

        r = post[
            "residual_ratio_model"
        ]

        beta = post[
            "beta_softening_per_pct"
        ]

        delta = (
            strain_pct[
                post_mask
            ]
            - eps_peak_pct
        )

        pred[
            post_mask
        ] = (
            q_peak
            * (
                r
                + (
                    1.0
                    - r
                )
                * np.exp(
                    -beta
                    * delta
                )
            )
        )

    else:

        pred[
            post_mask
        ] = (
            q_peak
        )

    return pred


# ============================================================
# CURVE-BY-CURVE ANALYSIS
# ============================================================

metric_rows = []
prediction_parts = []

group_columns = [
    "figure_id",
    "specimen_id",
    "stage_index",
    "stage",
]

print("=" * 88)
print(
    "UnsatConstitutiveLab — "
    "Phase 5A Constitutive Response Fitting"
)
print("=" * 88)

for keys, raw in curves.groupby(
    group_columns,
    sort=False,
):

    (
        figure_id,
        specimen_id,
        stage_index,
        stage,
    ) = keys

    curve = deduplicate_curve(
        raw
    )

    if len(curve) < 20:
        continue

    first = raw.iloc[0]

    q_peak = float(
        first[
            "source_q_peak_kPa"
        ]
    )

    strain = (
        curve[
            "axial_strain_local_pct"
        ].to_numpy(
            float
        )
    )

    q = (
        curve[
            "q_smooth_kPa"
        ].to_numpy(
            float
        )
    )

    # --------------------------------------------------------
    # Peak
    # --------------------------------------------------------

    peak_index = int(
        np.argmax(
            q
        )
    )

    digitized_peak = float(
        q[
            peak_index
        ]
    )

    eps_peak_pct = float(
        strain[
            peak_index
        ]
    )

    if (
        eps_peak_pct
        <= 0.05
    ):
        continue

    # --------------------------------------------------------
    # Empirical stiffness descriptors
    # --------------------------------------------------------

    pre_strain = strain[
        :peak_index + 1
    ]

    pre_q = q[
        :peak_index + 1
    ]

    eps50_pct = (
        interpolate_first_crossing(
            pre_strain,
            pre_q,
            0.5
            * q_peak,
        )
    )

    if (
        np.isfinite(
            eps50_pct
        )
        and eps50_pct > 0
    ):

        E50_MPa = (
            0.5
            * q_peak
            / (
                eps50_pct
                / 100.0
            )
            / 1000.0
        )

    else:

        E50_MPa = np.nan

    # E at 0.1% axial strain.
    target_eps = 0.1

    if (
        strain.min()
        <= target_eps
        <= strain.max()
    ):

        q_01 = float(
            np.interp(
                target_eps,
                strain,
                q,
            )
        )

        E_0p1_MPa = (
            q_01
            / 0.001
            / 1000.0
        )

    else:

        q_01 = np.nan
        E_0p1_MPa = np.nan

    # --------------------------------------------------------
    # Pre-peak constitutive backbone
    # --------------------------------------------------------

    pre_fit = fit_prepeak(
        pre_strain,
        pre_q,
        q_peak,
        eps_peak_pct,
    )

    if pre_fit is None:
        continue

    # --------------------------------------------------------
    # Post-peak
    # --------------------------------------------------------

    post_fit = fit_postpeak(
        strain[
            peak_index:
        ],
        q[
            peak_index:
        ],
        q_peak,
        eps_peak_pct,
    )

    if post_fit is None:

        post_fit = {
            "postpeak_available":
                False,

            "postpeak_reason":
                "insufficient_postpeak",

            "residual_ratio_model":
                np.nan,

            "beta_softening_per_pct":
                np.nan,

            "postpeak_nrmse":
                np.nan,
        }

    # Empirical terminal response.
    tail_start = max(
        0,
        int(
            0.90
            * len(q)
        ),
    )

    q_terminal = float(
        np.median(
            q[
                tail_start:
            ]
        )
    )

    terminal_ratio = (
        q_terminal
        / q_peak
    )

    # --------------------------------------------------------
    # Piecewise prediction
    # --------------------------------------------------------

    q_pred = evaluate_piecewise(
        strain,
        q_peak,
        eps_peak_pct,
        pre_fit,
        post_fit,
    )

    total_nrmse = float(
        np.sqrt(
            np.mean(
                (
                    (
                        q_pred
                        - q
                    )
                    / q_peak
                ) ** 2
            )
        )
    )

    # --------------------------------------------------------
    # Metadata / confidence
    # --------------------------------------------------------

    digitization_status = str(
        first[
            "status"
        ]
    )

    if digitization_status == "PASS":
        strain_confidence = (
            "high_tick_calibrated"
        )
    else:
        strain_confidence = (
            "template_axis"
        )

    metric_rows.append({
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

        "test_family":
            first[
                "test_family"
            ],

        "stage":
            stage,

        "stage_index":
            stage_index,

        "digitization_status":
            digitization_status,

        "strain_confidence":
            strain_confidence,

        "sigma_c_net_kPa":
            first[
                "sigma_c_net_kPa"
            ],

        "matric_suction_kPa":
            first[
                "matric_suction_kPa_meta"
            ]
            if (
                "matric_suction_kPa_meta"
                in first.index
            )
            else first[
                "matric_suction_kPa"
            ],

        "gamma_d_g_cm3":
            first[
                "gamma_d_g_cm3"
            ],

        "degree_saturation":
            first[
                "degree_saturation"
            ],

        "q_peak_source_kPa":
            q_peak,

        "q_peak_digitized_kPa":
            digitized_peak,

        "eps_peak_pct":
            eps_peak_pct,

        "eps50_pct":
            eps50_pct,

        "E_0p1_MPa":
            E_0p1_MPa,

        "E50_MPa":
            E50_MPa,

        "lambda_mobilization":
            pre_fit[
                "lambda_mobilization"
            ],

        "E_i_model_MPa":
            pre_fit[
                "E_i_model_MPa"
            ],

        "prepeak_nrmse":
            pre_fit[
                "prepeak_nrmse"
            ],

        "postpeak_available":
            post_fit[
                "postpeak_available"
            ],

        "postpeak_reason":
            post_fit[
                "postpeak_reason"
            ],

        "residual_ratio_model":
            post_fit[
                "residual_ratio_model"
            ],

        "beta_softening_per_pct":
            post_fit[
                "beta_softening_per_pct"
            ],

        "postpeak_nrmse":
            post_fit[
                "postpeak_nrmse"
            ],

        "terminal_strength_ratio":
            terminal_ratio,

        "piecewise_total_nrmse":
            total_nrmse,

        "n_curve_points":
            len(
                curve
            ),
    })

    prediction = pd.DataFrame({
        "figure_id":
            figure_id,

        "specimen_id":
            specimen_id,

        "stage":
            stage,

        "stage_index":
            stage_index,

        "axial_strain_local_pct":
            strain,

        "q_digitized_kPa":
            q,

        "q_piecewise_model_kPa":
            q_pred,

        "q_peak_source_kPa":
            q_peak,
    })

    prediction_parts.append(
        prediction
    )


# ============================================================
# SAVE
# ============================================================

metrics = pd.DataFrame(
    metric_rows
)

predictions = pd.concat(
    prediction_parts,
    ignore_index=True,
)

metrics.to_csv(
    METRICS_OUT,
    index=False,
)

predictions.to_csv(
    PRED_OUT,
    index=False,
)


# ============================================================
# REPORT
# ============================================================

print()
print("=== DATASET COVERAGE ===")

print(
    "Usable digitized stages :",
    curves[
        [
            "figure_id",
            "specimen_id",
            "stage_index",
        ]
    ]
    .drop_duplicates()
    .shape[0],
)

print(
    "Constitutive fits       :",
    len(
        metrics
    ),
)

print(
    "Unique specimens        :",
    metrics[
        "specimen_id"
    ].nunique(),
)

print(
    "Unique tubes            :",
    metrics[
        "tube_id"
    ].nunique(),
)

print()
print("=== STRAIN CONFIDENCE ===")

print(
    metrics[
        "strain_confidence"
    ]
    .value_counts()
    .to_string()
)

print()
print("=== PRE-PEAK FIT QUALITY ===")

print(
    metrics[
        "prepeak_nrmse"
    ]
    .describe(
        percentiles=[
            0.5,
            0.9,
            0.95,
        ]
    )
    .to_string()
)

print()
print("=== FULL PIECEWISE FIT QUALITY ===")

print(
    metrics[
        "piecewise_total_nrmse"
    ]
    .describe(
        percentiles=[
            0.5,
            0.9,
            0.95,
        ]
    )
    .to_string()
)

print()
print("=== POST-PEAK COVERAGE ===")

print(
    metrics[
        "postpeak_reason"
    ]
    .value_counts()
    .to_string()
)

print()
print("=== PARAMETER SUMMARY BY SOIL ===")

summary = (
    metrics.groupby(
        "soil_type"
    )
    .agg(
        n_stages=(
            "specimen_id",
            "size",
        ),
        n_tubes=(
            "tube_id",
            "nunique",
        ),
        median_E50_MPa=(
            "E50_MPa",
            "median",
        ),
        median_Ei_MPa=(
            "E_i_model_MPa",
            "median",
        ),
        median_eps_peak_pct=(
            "eps_peak_pct",
            "median",
        ),
        median_lambda=(
            "lambda_mobilization",
            "median",
        ),
        median_terminal_ratio=(
            "terminal_strength_ratio",
            "median",
        ),
        median_beta=(
            "beta_softening_per_pct",
            "median",
        ),
    )
)

print(
    summary.to_string()
)

print()
print("=== WORST 12 PIECEWISE FITS ===")

worst = (
    metrics.sort_values(
        "piecewise_total_nrmse",
        ascending=False,
    )
    [
        [
            "figure_id",
            "specimen_id",
            "stage",
            "soil_type",
            "strain_confidence",
            "piecewise_total_nrmse",
            "prepeak_nrmse",
            "postpeak_nrmse",
            "eps_peak_pct",
            "lambda_mobilization",
            "terminal_strength_ratio",
        ]
    ]
    .head(12)
)

print(
    worst.to_string(
        index=False
    )
)

print()
print("Outputs:")
print(" ", METRICS_OUT)
print(" ", PRED_OUT)

print()
print(
    "PHASE 5A CONSTITUTIVE RESPONSE FITTING: PASS"
)
