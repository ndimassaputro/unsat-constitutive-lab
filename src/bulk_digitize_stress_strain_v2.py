from pathlib import Path
import math

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage
from scipy.cluster.vq import kmeans2
from scipy.signal import find_peaks
from matplotlib.colors import rgb_to_hsv

MANIFEST = Path(
    "results/tables/stress_strain_image_manifest.csv"
)

CURVE_DIR = Path(
    "data/processed/stress_strain_curves_v2"
)

MASTER_OUT = Path(
    "data/processed/stress_strain_master_v2.csv"
)

QC_OUT = Path(
    "results/tables/stress_strain_digitization_qc_v2.csv"
)

CURVE_DIR.mkdir(parents=True, exist_ok=True)
MASTER_OUT.parent.mkdir(parents=True, exist_ok=True)
QC_OUT.parent.mkdir(parents=True, exist_ok=True)

manifest = pd.read_csv(MANIFEST)

# ============================================================
# UTILITIES
# ============================================================

def parse_numbers(value):
    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    return [
        float(x)
        for x in text.split(";")
        if x.strip()
    ]


def parse_text(value):
    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    return [
        x.strip()
        for x in text.split(";")
        if x.strip()
    ]


def contiguous_groups(indices):
    indices = np.asarray(indices, dtype=int)

    if len(indices) == 0:
        return []

    groups = []

    start = indices[0]
    previous = indices[0]

    for value in indices[1:]:

        if value != previous + 1:
            groups.append(
                (
                    start,
                    previous,
                )
            )

            start = value

        previous = value

    groups.append(
        (
            start,
            previous,
        )
    )

    return groups


# ============================================================
# PLOT RECTANGLE
#
# The Appendix-F figures use a highly consistent template.
# Detect first; use image-fraction fallback if detection fails.
# ============================================================

def detect_plot_rect(rgb):

    gray = (
        0.299 * rgb[:, :, 0]
        + 0.587 * rgb[:, :, 1]
        + 0.114 * rgb[:, :, 2]
    )

    h, w = gray.shape

    dark = gray < 100

    vertical_counts = (
        dark.sum(axis=0)
    )

    horizontal_counts = (
        dark.sum(axis=1)
    )

    x_candidates = np.where(
        vertical_counts
        > 0.40 * h
    )[0]

    y_candidates = np.where(
        horizontal_counts
        > 0.40 * w
    )[0]

    x_groups = contiguous_groups(
        x_candidates
    )

    y_groups = contiguous_groups(
        y_candidates
    )

    x_centers = [
        int(
            round(
                (a + b) / 2
            )
        )
        for a, b in x_groups
        if (
            0.08 * w
            < (a + b) / 2
            < 0.99 * w
        )
    ]

    y_centers = [
        int(
            round(
                (a + b) / 2
            )
        )
        for a, b in y_groups
        if (
            0.01 * h
            < (a + b) / 2
            < 0.93 * h
        )
    ]

    detected = False

    if (
        len(x_centers) >= 2
        and len(y_centers) >= 2
    ):

        x_left = min(
            x_centers
        )

        x_right = max(
            x_centers
        )

        y_top = min(
            y_centers
        )

        y_bottom = max(
            y_centers
        )

        if (
            x_right - x_left
            >= 0.65 * w
            and y_bottom - y_top
            >= 0.65 * h
        ):
            detected = True

    if not detected:

        # Calibrated from the 660x495 Appendix-F template
        # and ST-36 675x495 plot.
        x_left = int(
            round(
                0.160 * w
            )
        )

        x_right = int(
            round(
                0.963 * w
            )
        )

        y_top = int(
            round(
                0.030 * h
            )
        )

        y_bottom = int(
            round(
                0.840 * h
            )
        )

        method = (
            "template_fraction"
        )

    else:

        method = (
            "detected_frame"
        )

    return (
        x_left,
        x_right,
        y_top,
        y_bottom,
        method,
    )


# ============================================================
# X-AXIS SCALE
#
# Major ticks in these plots represent 2% strain increments.
# Detect vertical tick stems immediately above the bottom axis.
# ============================================================

def infer_xmax_from_ticks(
    rgb,
    rect,
    n_stages,
):

    x_left, x_right, y_top, y_bottom = rect

    gray = (
        0.299 * rgb[:, :, 0]
        + 0.587 * rgb[:, :, 1]
        + 0.114 * rgb[:, :, 2]
    )

    dark = gray < 110

    width = (
        x_right
        - x_left
    )

    run_lengths = []

    xs = range(
        x_left + 3,
        x_right - 2,
    )

    for x in xs:

        best = 0

        # Search slightly around x because anti-aliased
        # tick lines may be 1–3 pixels wide.
        for xx in range(
            max(
                x_left,
                x - 1,
            ),
            min(
                x_right + 1,
                x + 2,
            ),
        ):

            run = 0

            for y in range(
                y_bottom - 2,
                max(
                    y_top,
                    y_bottom - 22,
                ),
                -1,
            ):

                if dark[y, xx]:
                    run += 1

                else:
                    if run > 0:
                        break

            best = max(
                best,
                run,
            )

        run_lengths.append(
            best
        )

    run_lengths = np.asarray(
        run_lengths,
        dtype=float,
    )

    # Find candidate vertical tick stems.
    peaks, props = find_peaks(
        run_lengths,
        height=4,
        distance=4,
    )

    if len(peaks) >= 4:

        heights = props[
            "peak_heights"
        ]

        # Major ticks should form the longer-stem population.
        if len(np.unique(heights)) >= 2:

            try:
                centers, labels = kmeans2(
                    heights.reshape(
                        -1,
                        1,
                    ),
                    2,
                    minit="++",
                    iter=50,
                    seed=20260818,
                )

                major_label = int(
                    np.argmax(
                        centers[:, 0]
                    )
                )

                major = peaks[
                    labels
                    == major_label
                ]

            except Exception:
                threshold = np.quantile(
                    heights,
                    0.65,
                )

                major = peaks[
                    heights >= threshold
                ]

        else:
            major = peaks

        major_x = np.asarray(
            [
                x_left
                + 3
                + int(p)
                for p in major
            ],
            dtype=float,
        )

        # Deduplicate very-near detections.
        major_x = np.sort(
            major_x
        )

        cleaned = []

        for x in major_x:

            if (
                not cleaned
                or x
                - cleaned[-1]
                >= 6
            ):
                cleaned.append(
                    x
                )

        major_x = np.asarray(
            cleaned,
            dtype=float,
        )

        # Remove detections too close to frame borders.
        major_x = major_x[
            (
                major_x
                > x_left
                + 0.03 * width
            )
            & (
                major_x
                < x_right
                - 0.03 * width
            )
        ]

        if len(major_x) >= 2:

            diffs = np.diff(
                major_x
            )

            median_spacing = float(
                np.median(
                    diffs
                )
            )

            if median_spacing > 10:

                n_intervals = int(
                    round(
                        width
                        / median_spacing
                    )
                )

                x_max = (
                    2.0
                    * n_intervals
                )

                if (
                    4.0
                    <= x_max
                    <= 24.0
                ):

                    spacing_cv = float(
                        np.std(
                            diffs
                        )
                        / np.mean(
                            diffs
                        )
                    ) if len(diffs) > 1 else 0.0

                    return (
                        x_max,
                        "tick_spacing",
                        spacing_cv,
                        len(
                            major_x
                        ),
                    )

    # Conservative fallback.
    if n_stages == 1:
        fallback = 12.0
    else:
        fallback = 8.0

    return (
        fallback,
        "template_fallback",
        np.nan,
        0,
    )


# ============================================================
# CONNECTED COMPONENTS
# ============================================================

def choose_curve_component(
    mask,
):

    structure = np.ones(
        (
            3,
            3,
        ),
        dtype=bool,
    )

    # Markers and connecting lines can have 1–2 px gaps.
    closed = ndimage.binary_closing(
        mask,
        structure=structure,
        iterations=2,
    )

    labels, n_labels = (
        ndimage.label(
            closed
        )
    )

    best = None
    best_score = -np.inf

    for label_id in range(
        1,
        n_labels + 1,
    ):

        ys, xs = np.where(
            labels
            == label_id
        )

        if len(xs) < 20:
            continue

        x_span = (
            xs.max()
            - xs.min()
            + 1
        )

        y_span = (
            ys.max()
            - ys.min()
            + 1
        )

        if (
            x_span < 20
            or y_span < 8
        ):
            continue

        score = (
            x_span
            * math.sqrt(
                y_span
            )
            * math.sqrt(
                len(xs)
            )
        )

        if score > best_score:

            best_score = score

            best = (
                labels
                == label_id
            )

    return best


def centerline_from_component(
    component,
    x_offset,
    y_offset,
):

    rows = []

    if component is None:
        return rows

    for x_local in range(
        component.shape[1]
    ):

        ys = np.where(
            component[
                :,
                x_local,
            ]
        )[0]

        if len(ys) == 0:
            continue

        # Median collapses line + marker thickness.
        y_local = float(
            np.median(
                ys
            )
        )

        rows.append(
            (
                x_offset
                + x_local,

                y_offset
                + y_local,
            )
        )

    return rows


# ============================================================
# SINGLE-STAGE BLACK CURVE
# ============================================================

def extract_single(
    rgb,
    rect,
):

    x_left, x_right, y_top, y_bottom = rect

    pad = 5

    crop = rgb[
        y_top + pad:
        y_bottom - pad,

        x_left + pad:
        x_right - pad,

        :
    ]

    gray = (
        0.299
        * crop[:, :, 0]
        + 0.587
        * crop[:, :, 1]
        + 0.114
        * crop[:, :, 2]
    )

    chroma = (
        crop.max(
            axis=2
        )
        - crop.min(
            axis=2
        )
    )

    mask = (
        (gray < 85)
        & (chroma < 40)
    )

    component = (
        choose_curve_component(
            mask
        )
    )

    return (
        centerline_from_component(
            component,
            x_left + pad,
            y_top + pad,
        )
    )


# ============================================================
# MULTISTAGE COLORED CURVES
# ============================================================

def extract_multistage(
    rgb,
    rect,
    n_stages,
):

    x_left, x_right, y_top, y_bottom = rect

    pad = 5

    crop = (
        rgb[
            y_top + pad:
            y_bottom - pad,

            x_left + pad:
            x_right - pad,

            :
        ].astype(
            float
        )
        / 255.0
    )

    hsv = rgb_to_hsv(
        crop
    )

    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    hue = hsv[:, :, 0]

    colored = (
        (sat > 0.25)
        & (val < 0.97)
    )

    ys, xs = np.where(
        colored
    )

    if len(xs) < 100:
        return []

    hue_values = hue[
        ys,
        xs,
    ]

    features = np.column_stack(
        [
            np.cos(
                2
                * np.pi
                * hue_values
            ),
            np.sin(
                2
                * np.pi
                * hue_values
            ),
        ]
    )

    if len(features) > 12000:

        idx = np.linspace(
            0,
            len(features) - 1,
            12000,
        ).astype(
            int
        )

        sample = features[
            idx
        ]

    else:

        sample = features

    try:

        centers, _ = kmeans2(
            sample,
            n_stages,
            minit="++",
            iter=100,
            seed=20260818,
        )

    except TypeError:

        np.random.seed(
            20260818
        )

        centers, _ = kmeans2(
            sample,
            n_stages,
            minit="points",
            iter=100,
        )

    distances = np.linalg.norm(
        features[
            :,
            None,
            :
        ]
        - centers[
            None,
            :,
            :
        ],
        axis=2,
    )

    assignments = np.argmin(
        distances,
        axis=1,
    )

    curves = []

    for cluster in range(
        n_stages
    ):

        mask = np.zeros(
            colored.shape,
            dtype=bool,
        )

        keep = (
            assignments
            == cluster
        )

        mask[
            ys[keep],
            xs[keep],
        ] = True

        component = (
            choose_curve_component(
                mask
            )
        )

        points = (
            centerline_from_component(
                component,
                x_left + pad,
                y_top + pad,
            )
        )

        if len(points) >= 15:

            curves.append(
                points
            )

    # Cumulative strain means stages naturally order left-to-right.
    curves.sort(
        key=lambda pts:
            np.median(
                [
                    p[0]
                    for p in pts
                ]
            )
    )

    return curves


# ============================================================
# SOURCE-ANCHORED Y CALIBRATION
#
# Source table gives q_peak for every stage.
# Use all stages in a specimen to estimate one shared
# stress-per-pixel factor.
#
# This calibrates SCALE, while the image provides CURVE SHAPE.
# ============================================================

def smoothed_peak_pixel_y(
    points,
):

    frame = pd.DataFrame(
        points,
        columns=[
            "x",
            "y",
        ],
    ).sort_values(
        "x"
    )

    frame[
        "y_smooth"
    ] = (
        frame["y"]
        .rolling(
            7,
            center=True,
            min_periods=1,
        )
        .median()
    )

    # Peak stress = minimum y coordinate.
    return float(
        frame[
            "y_smooth"
        ].min()
    )


def calibrate_y_scale(
    extracted_curves,
    source_peaks,
    y_bottom,
):

    factors = []

    for points, q_peak in zip(
        extracted_curves,
        source_peaks,
    ):

        peak_y = (
            smoothed_peak_pixel_y(
                points
            )
        )

        pixel_height = (
            y_bottom
            - peak_y
        )

        if pixel_height <= 5:
            continue

        factors.append(
            q_peak
            / pixel_height
        )

    if not factors:
        return (
            None,
            np.nan,
            [],
        )

    factors = np.asarray(
        factors,
        dtype=float,
    )

    scale = float(
        np.median(
            factors
        )
    )

    if len(factors) >= 2:

        cv = float(
            np.std(
                factors,
                ddof=1,
            )
            / np.mean(
                factors
            )
        )

    else:

        cv = np.nan

    return (
        scale,
        cv,
        factors.tolist(),
    )


# ============================================================
# PHYSICAL CURVE
# ============================================================

def physical_curve(
    points,
    rect,
    x_max,
    stress_per_pixel,
):

    x_left, x_right, y_top, y_bottom = rect

    frame = pd.DataFrame(
        points,
        columns=[
            "pixel_x",
            "pixel_y",
        ],
    )

    frame[
        "axial_strain_global_pct"
    ] = (
        (
            frame[
                "pixel_x"
            ]
            - x_left
        )
        / (
            x_right
            - x_left
        )
        * x_max
    )

    frame[
        "deviator_stress_kPa"
    ] = (
        (
            y_bottom
            - frame[
                "pixel_y"
            ]
        )
        * stress_per_pixel
    )

    frame = frame[
        (
            frame[
                "axial_strain_global_pct"
            ]
            >= -0.15
        )
        & (
            frame[
                "axial_strain_global_pct"
            ]
            <= x_max
            + 0.15
        )
        & (
            frame[
                "deviator_stress_kPa"
            ]
            >= -5
        )
    ].copy()

    frame = frame.sort_values(
        "axial_strain_global_pct"
    )

    frame[
        "q_smooth_kPa"
    ] = (
        frame[
            "deviator_stress_kPa"
        ]
        .rolling(
            7,
            center=True,
            min_periods=1,
        )
        .median()
    )

    return frame


# ============================================================
# BULK PROCESSING
# ============================================================

qc_rows = []
master_parts = []

print("=" * 88)
print(
    "UnsatConstitutiveLab — "
    "Stress-Strain Digitization V2"
)
print("=" * 88)

for _, row in manifest.iterrows():

    figure = str(
        row[
            "figure_id"
        ]
    )

    specimen = str(
        row[
            "specimen_id"
        ]
    )

    image_path = Path(
        row[
            "image_path"
        ]
    )

    stages = parse_text(
        row[
            "source_stages"
        ]
    )

    suctions = parse_numbers(
        row[
            "source_suctions_kPa"
        ]
    )

    peaks = parse_numbers(
        row[
            "source_q_peaks_kPa"
        ]
    )

    n_stages = int(
        row[
            "source_rows"
        ]
    )

    if not (
        len(stages)
        == len(suctions)
        == len(peaks)
        == n_stages
    ):

        qc_rows.append({
            "figure_id":
                figure,

            "specimen_id":
                specimen,

            "status":
                "METADATA_FAIL",
        })

        continue

    rgb = np.asarray(
        Image.open(
            image_path
        ).convert(
            "RGB"
        )
    )

    (
        x_left,
        x_right,
        y_top,
        y_bottom,
        rect_method,
    ) = detect_plot_rect(
        rgb
    )

    rect = (
        x_left,
        x_right,
        y_top,
        y_bottom,
    )

    (
        x_max,
        x_method,
        x_tick_spacing_cv,
        n_major_ticks,
    ) = infer_xmax_from_ticks(
        rgb,
        rect,
        n_stages,
    )

    if n_stages == 1:

        curves = [
            extract_single(
                rgb,
                rect,
            )
        ]

    else:

        curves = (
            extract_multistage(
                rgb,
                rect,
                n_stages,
            )
        )

    if (
        len(curves)
        != n_stages
    ):

        qc_rows.append({
            "figure_id":
                figure,

            "specimen_id":
                specimen,

            "status":
                "CURVE_COUNT_FAIL",

            "n_stages":
                n_stages,

            "curves_detected":
                len(curves),

            "x_max_pct":
                x_max,

            "x_method":
                x_method,
        })

        continue

    (
        stress_per_pixel,
        y_scale_cv,
        individual_factors,
    ) = calibrate_y_scale(
        curves,
        peaks,
        y_bottom,
    )

    if stress_per_pixel is None:

        qc_rows.append({
            "figure_id":
                figure,

            "specimen_id":
                specimen,

            "status":
                "Y_CALIBRATION_FAIL",

            "n_stages":
                n_stages,
        })

        continue

    specimen_parts = []
    stage_peak_errors = []

    for i, (
        points,
        stage_name,
        suction,
        source_peak,
    ) in enumerate(
        zip(
            curves,
            stages,
            suctions,
            peaks,
        ),
        start=1,
    ):

        curve = physical_curve(
            points,
            rect,
            x_max,
            stress_per_pixel,
        )

        if len(curve) < 15:
            continue

        global_start = float(
            curve[
                "axial_strain_global_pct"
            ].min()
        )

        curve[
            "axial_strain_local_pct"
        ] = (
            curve[
                "axial_strain_global_pct"
            ]
            - global_start
        )

        digitized_peak = float(
            curve[
                "q_smooth_kPa"
            ].max()
        )

        peak_error_pct = (
            100.0
            * (
                digitized_peak
                - source_peak
            )
            / source_peak
        )

        stage_peak_errors.append(
            peak_error_pct
        )

        curve[
            "figure_id"
        ] = figure

        curve[
            "specimen_id"
        ] = specimen

        curve[
            "stage_index"
        ] = i

        curve[
            "stage"
        ] = stage_name

        curve[
            "matric_suction_kPa"
        ] = suction

        curve[
            "source_q_peak_kPa"
        ] = source_peak

        curve[
            "stress_per_pixel_kPa"
        ] = stress_per_pixel

        curve[
            "x_max_pct"
        ] = x_max

        specimen_parts.append(
            curve
        )

    if (
        len(
            specimen_parts
        )
        != n_stages
    ):

        qc_rows.append({
            "figure_id":
                figure,

            "specimen_id":
                specimen,

            "status":
                "POSTPROCESS_FAIL",

            "n_stages":
                n_stages,

            "stages_processed":
                len(
                    specimen_parts
                ),
        })

        continue

    specimen_df = pd.concat(
        specimen_parts,
        ignore_index=True,
    )

    output = (
        CURVE_DIR
        / (
            figure.replace(
                "-",
                "_",
            )
            + "_"
            + specimen.replace(
                "-",
                "_",
            )
            + ".csv"
        )
    )

    specimen_df.to_csv(
        output,
        index=False,
    )

    master_parts.append(
        specimen_df
    )

    abs_peak_errors = np.abs(
        stage_peak_errors
    )

    # --------------------------------------------------------
    # QC rules
    #
    # Peak agreement is cross-stage for multistage specimens.
    # Single-stage Y is source-anchored by definition, so X-axis
    # confidence matters more for later stiffness interpretation.
    # --------------------------------------------------------

    if n_stages >= 2:

        y_consistent = (
            not np.isnan(
                y_scale_cv
            )
            and y_scale_cv
            <= 0.08
        )

    else:

        y_consistent = True

    x_confident = (
        x_method
        == "tick_spacing"
        and (
            np.isnan(
                x_tick_spacing_cv
            )
            or x_tick_spacing_cv
            <= 0.15
        )
    )

    if (
        np.max(
            abs_peak_errors
        )
        <= 5.0
        and y_consistent
        and x_confident
    ):

        status = "PASS"

    elif (
        np.max(
            abs_peak_errors
        )
        <= 8.0
        and y_consistent
    ):

        status = "USABLE_REVIEW_X"

    elif (
        np.max(
            abs_peak_errors
        )
        <= 12.0
    ):

        status = "REVIEW"

    else:

        status = "FAIL_QC"

    qc_rows.append({
        "figure_id":
            figure,

        "specimen_id":
            specimen,

        "status":
            status,

        "n_stages":
            n_stages,

        "x_max_pct":
            x_max,

        "x_method":
            x_method,

        "n_major_ticks":
            n_major_ticks,

        "x_tick_spacing_cv":
            x_tick_spacing_cv,

        "rect_method":
            rect_method,

        "stress_per_pixel_kPa":
            stress_per_pixel,

        "y_scale_cv_across_stages":
            y_scale_cv,

        "peak_error_mean_abs_pct":
            float(
                np.mean(
                    abs_peak_errors
                )
            ),

        "peak_error_max_abs_pct":
            float(
                np.max(
                    abs_peak_errors
                )
            ),

        "stage_peak_errors_pct":
            ";".join(
                f"{x:+.2f}"
                for x in stage_peak_errors
            ),

        "individual_stress_per_pixel":
            ";".join(
                f"{x:.6f}"
                for x in individual_factors
            ),

        "output_csv":
            str(
                output
            ),
    })


# ============================================================
# SAVE
# ============================================================

qc = pd.DataFrame(
    qc_rows
)

qc.to_csv(
    QC_OUT,
    index=False,
)

if master_parts:

    master = pd.concat(
        master_parts,
        ignore_index=True,
    )

    master.to_csv(
        MASTER_OUT,
        index=False,
    )

else:

    master = pd.DataFrame()


# ============================================================
# REPORT
# ============================================================

print()
print("=== GLOBAL QC ===")

print(
    "Figures attempted      :",
    len(
        manifest
    ),
)

for status in [
    "PASS",
    "USABLE_REVIEW_X",
    "REVIEW",
    "FAIL_QC",
    "CURVE_COUNT_FAIL",
    "Y_CALIBRATION_FAIL",
    "POSTPROCESS_FAIL",
    "METADATA_FAIL",
]:

    count = int(
        (
            qc[
                "status"
            ]
            == status
        ).sum()
    )

    if count:
        print(
            f"{status:<22}:",
            count,
        )

usable_status = [
    "PASS",
    "USABLE_REVIEW_X",
]

usable = qc[
    qc[
        "status"
    ].isin(
        usable_status
    )
]

print()
print(
    "Usable figures         :",
    len(
        usable
    ),
)

if (
    not usable.empty
    and "n_stages"
    in usable.columns
):

    print(
        "Usable stages          :",
        int(
            usable[
                "n_stages"
            ].sum()
        ),
    )

valid = qc[
    qc[
        "peak_error_mean_abs_pct"
    ].notna()
] if (
    "peak_error_mean_abs_pct"
    in qc.columns
) else pd.DataFrame()

if not valid.empty:

    print(
        "Median mean peak error :",
        f"{valid['peak_error_mean_abs_pct'].median():.2f} %",
    )

    print(
        "90th pct mean error    :",
        f"{valid['peak_error_mean_abs_pct'].quantile(0.90):.2f} %",
    )

multi = valid[
    valid[
        "n_stages"
    ] >= 2
] if (
    "n_stages"
    in valid.columns
) else pd.DataFrame()

if (
    not multi.empty
    and "y_scale_cv_across_stages"
    in multi.columns
):

    print(
        "Median multistage Y-CV :",
        f"{100 * multi['y_scale_cv_across_stages'].median():.2f} %",
    )

print()
print(
    "X tick-calibrated figs :",
    int(
        (
            qc.get(
                "x_method",
                pd.Series(
                    dtype=str
                )
            )
            == "tick_spacing"
        ).sum()
    ),
)

print()
print("=== NON-USABLE CASES ===")

nonusable = qc[
    ~qc[
        "status"
    ].isin(
        usable_status
    )
]

if nonusable.empty:

    print("None")

else:

    cols = [
        c
        for c in [
            "figure_id",
            "specimen_id",
            "status",
            "n_stages",
            "x_max_pct",
            "x_method",
            "x_tick_spacing_cv",
            "y_scale_cv_across_stages",
            "peak_error_mean_abs_pct",
            "peak_error_max_abs_pct",
            "stage_peak_errors_pct",
        ]
        if c
        in nonusable.columns
    ]

    print(
        nonusable[
            cols
        ].to_string(
            index=False
        )
    )

print()
print(
    "QC table     :",
    QC_OUT,
)

print(
    "Master curves:",
    MASTER_OUT,
)

print()
print(
    "PHASE 4H-V2 SOURCE-ANCHORED DIGITIZATION: COMPLETE"
)
