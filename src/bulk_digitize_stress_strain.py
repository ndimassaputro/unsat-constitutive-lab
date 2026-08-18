from pathlib import Path
import math

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage
from scipy.cluster.vq import kmeans2
from matplotlib.colors import rgb_to_hsv

MANIFEST = Path(
    "results/tables/stress_strain_image_manifest.csv"
)

CURVE_DIR = Path(
    "data/processed/stress_strain_curves"
)

SUMMARY_OUT = Path(
    "results/tables/stress_strain_digitization_qc.csv"
)

MASTER_OUT = Path(
    "data/processed/stress_strain_master.csv"
)

CURVE_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
MASTER_OUT.parent.mkdir(parents=True, exist_ok=True)

manifest = pd.read_csv(MANIFEST)

# ============================================================
# UTILITIES
# ============================================================

def parse_semicolon_numbers(value):
    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    return [
        float(x)
        for x in text.split(";")
        if str(x).strip()
    ]


def parse_semicolon_text(value):
    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    return [
        x.strip()
        for x in text.split(";")
    ]


def contiguous_groups(indices):
    indices = np.asarray(indices, dtype=int)

    if len(indices) == 0:
        return []

    groups = []
    start = indices[0]
    prev = indices[0]

    for value in indices[1:]:
        if value != prev + 1:
            groups.append((start, prev))
            start = value

        prev = value

    groups.append((start, prev))

    return groups


# ============================================================
# PLOT RECTANGLE
# ============================================================

def detect_plot_rect(rgb):
    gray = (
        0.299 * rgb[:, :, 0]
        + 0.587 * rgb[:, :, 1]
        + 0.114 * rgb[:, :, 2]
    )

    h, w = gray.shape

    dark = gray < 110

    vertical_counts = dark.sum(axis=0)
    horizontal_counts = dark.sum(axis=1)

    x_candidates = np.where(
        vertical_counts > 0.45 * h
    )[0]

    y_candidates = np.where(
        horizontal_counts > 0.45 * w
    )[0]

    x_groups = contiguous_groups(x_candidates)
    y_groups = contiguous_groups(y_candidates)

    x_centers = [
        int(round((a + b) / 2))
        for a, b in x_groups
        if 0.05 * w < (a + b) / 2 < 0.99 * w
    ]

    y_centers = [
        int(round((a + b) / 2))
        for a, b in y_groups
        if 0.01 * h < (a + b) / 2 < 0.95 * h
    ]

    if len(x_centers) >= 2:
        x_left = min(x_centers)
        x_right = max(x_centers)
        x_method = "detected"
    else:
        x_left = int(round(0.160 * w))
        x_right = int(round(0.963 * w))
        x_method = "fallback_fraction"

    if len(y_centers) >= 2:
        y_top = min(y_centers)
        y_bottom = max(y_centers)
        y_method = "detected"
    else:
        y_top = int(round(0.030 * h))
        y_bottom = int(round(0.840 * h))
        y_method = "fallback_fraction"

    if (
        x_right - x_left < 0.55 * w
        or y_bottom - y_top < 0.55 * h
    ):
        x_left = int(round(0.160 * w))
        x_right = int(round(0.963 * w))
        y_top = int(round(0.030 * h))
        y_bottom = int(round(0.840 * h))

        x_method = "fallback_fraction"
        y_method = "fallback_fraction"

    return (
        x_left,
        x_right,
        y_top,
        y_bottom,
        x_method,
        y_method,
    )


# ============================================================
# Y-AXIS SCALE
#
# Figures use horizontal dashed gridlines at 50-kPa intervals.
# Count internal gridline levels:
#
# 4 internal -> y_max = 250 kPa
# 5 internal -> y_max = 300 kPa
# etc.
# ============================================================

def infer_ymax(rgb, rect):
    x_left, x_right, y_top, y_bottom = rect

    crop = rgb[
        y_top + 4:y_bottom - 4,
        x_left + 5:x_right - 5,
        :
    ]

    if crop.size == 0:
        return None, "failed"

    gray = (
        0.299 * crop[:, :, 0]
        + 0.587 * crop[:, :, 1]
        + 0.114 * crop[:, :, 2]
    )

    chroma = (
        crop.max(axis=2)
        - crop.min(axis=2)
    )

    # Gray/black dashed grid lines.
    candidate_pixel = (
        (gray < 235)
        & (chroma < 15)
    )

    row_score = (
        candidate_pixel.sum(axis=1)
        / candidate_pixel.shape[1]
    )

    rows = np.where(
        row_score > 0.20
    )[0]

    groups = contiguous_groups(rows)

    centers = []

    for a, b in groups:
        center = (
            y_top + 4
            + (a + b) / 2
        )

        if (
            center > y_top + 12
            and center < y_bottom - 12
        ):
            centers.append(center)

    # Deduplicate nearby line detections.
    merged = []

    for center in sorted(centers):
        if (
            not merged
            or center - merged[-1] > 6
        ):
            merged.append(center)

    n_internal = len(merged)

    if 2 <= n_internal <= 11:
        y_max = 50.0 * (
            n_internal + 1
        )

        return y_max, "gridline_count"

    return None, "failed"


# ============================================================
# X-AXIS SCALE
#
# Major ticks are normally spaced every 2% axial strain.
# Score candidate axis maxima by expected major-tick locations.
# ============================================================

def infer_xmax(rgb, rect, n_stages):
    x_left, x_right, y_top, y_bottom = rect

    gray = (
        0.299 * rgb[:, :, 0]
        + 0.587 * rgb[:, :, 1]
        + 0.114 * rgb[:, :, 2]
    )

    dark = gray < 100

    runs = np.zeros(
        x_right - x_left + 1,
        dtype=float,
    )

    for local_x, x in enumerate(
        range(x_left, x_right + 1)
    ):
        run = 0

        for y in range(
            y_bottom - 1,
            max(
                y_top,
                y_bottom - 18,
            ),
            -1,
        ):
            if dark[y, x]:
                run += 1
            else:
                if run > 0:
                    break

        runs[local_x] = run

    candidates = [
        6,
        8,
        10,
        12,
        14,
        16,
        20,
    ]

    scores = []

    width = (
        x_right
        - x_left
    )

    for xmax in candidates:
        n_intervals = int(
            xmax / 2
        )

        expected = []

        for j in range(
            1,
            n_intervals,
        ):
            x = (
                x_left
                + width
                * (
                    2.0 * j
                    / xmax
                )
            )

            expected.append(x)

        if not expected:
            continue

        tick_scores = []

        for x in expected:
            local = int(
                round(
                    x - x_left
                )
            )

            lo = max(
                0,
                local - 3,
            )

            hi = min(
                len(runs),
                local + 4,
            )

            tick_scores.append(
                float(
                    runs[lo:hi].max()
                )
            )

        score = float(
            np.mean(
                tick_scores
            )
        )

        strong_fraction = float(
            np.mean(
                np.asarray(
                    tick_scores
                ) >= 6
            )
        )

        scores.append(
            (
                score
                + 4.0 * strong_fraction,
                xmax,
            )
        )

    scores.sort(
        reverse=True
    )

    if scores and scores[0][0] >= 7.0:
        return (
            float(
                scores[0][1]
            ),
            "major_tick_score",
        )

    # Empirical fallback visible in the Appendix-F templates.
    if n_stages == 1:
        return 12.0, "template_fallback"
    else:
        return 8.0, "template_fallback"


# ============================================================
# CONNECTED COMPONENT HELPERS
# ============================================================

def choose_curve_component(mask):
    structure = np.ones(
        (3, 3),
        dtype=bool,
    )

    closed = ndimage.binary_closing(
        mask,
        structure=structure,
        iterations=1,
    )

    labels, n = ndimage.label(
        closed
    )

    best = None
    best_score = -np.inf

    for label_id in range(
        1,
        n + 1
    ):
        ys, xs = np.where(
            labels == label_id
        )

        if len(xs) < 15:
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
            x_span < 15
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
                labels == label_id
            )

    return best


def centerline_from_mask(
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

def extract_single_curve(
    rgb,
    rect,
):
    x_left, x_right, y_top, y_bottom = rect

    pad = 5

    crop = rgb[
        y_top + pad:y_bottom - pad,
        x_left + pad:x_right - pad,
        :
    ]

    gray = (
        0.299 * crop[:, :, 0]
        + 0.587 * crop[:, :, 1]
        + 0.114 * crop[:, :, 2]
    )

    chroma = (
        crop.max(axis=2)
        - crop.min(axis=2)
    )

    mask = (
        (gray < 80)
        & (chroma < 35)
    )

    component = choose_curve_component(
        mask
    )

    return centerline_from_mask(
        component,
        x_left + pad,
        y_top + pad,
    )


# ============================================================
# MULTISTAGE COLORED CURVES
# ============================================================

def extract_multistage_curves(
    rgb,
    rect,
    n_stages,
):
    x_left, x_right, y_top, y_bottom = rect

    pad = 5

    crop = rgb[
        y_top + pad:y_bottom - pad,
        x_left + pad:x_right - pad,
        :
    ].astype(float) / 255.0

    hsv = rgb_to_hsv(
        crop
    )

    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    hue = hsv[:, :, 0]

    colored = (
        (saturation > 0.28)
        & (value < 0.96)
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

    # Circular hue coordinates.
    features = np.column_stack([
        np.cos(
            2.0
            * np.pi
            * hue_values
        ),
        np.sin(
            2.0
            * np.pi
            * hue_values
        ),
    ])

    # Deterministic subsample for clustering speed.
    if len(features) > 10000:
        indices = np.linspace(
            0,
            len(features) - 1,
            10000,
        ).astype(int)

        sample = features[
            indices
        ]
    else:
        sample = features

    try:
        centroids, _ = kmeans2(
            sample,
            n_stages,
            minit="++",
            iter=50,
            seed=20260818,
        )
    except TypeError:
        np.random.seed(
            20260818
        )

        centroids, _ = kmeans2(
            sample,
            n_stages,
            minit="points",
            iter=50,
        )

    # Assign every colored pixel.
    distances = np.linalg.norm(
        features[:, None, :]
        - centroids[None, :, :],
        axis=2,
    )

    cluster_id = np.argmin(
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
            cluster_id
            == cluster
        )

        mask[
            ys[keep],
            xs[keep],
        ] = True

        component = choose_curve_component(
            mask
        )

        points = centerline_from_mask(
            component,
            x_left + pad,
            y_top + pad,
        )

        if len(points) < 15:
            continue

        curves.append(
            points
        )

    # Stage order follows cumulative x-position.
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
# PIXEL -> PHYSICAL
# ============================================================

def physical_curve(
    points,
    rect,
    x_max,
    y_max,
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
            frame["pixel_x"]
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
            - frame["pixel_y"]
        )
        / (
            y_bottom
            - y_top
        )
        * y_max
    )

    frame = frame[
        (
            frame[
                "axial_strain_global_pct"
            ] >= -0.1
        )
        & (
            frame[
                "axial_strain_global_pct"
            ] <= x_max + 0.1
        )
        & (
            frame[
                "deviator_stress_kPa"
            ] >= -5
        )
        & (
            frame[
                "deviator_stress_kPa"
            ] <= y_max + 10
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
# BULK RUN
# ============================================================

all_curves = []
qc_rows = []

print("=" * 86)
print(
    "UnsatConstitutiveLab — "
    "Bulk Stress-Strain Digitization"
)
print("=" * 86)

for _, row in manifest.iterrows():

    specimen = str(
        row["specimen_id"]
    )

    figure = str(
        row["figure_id"]
    )

    image_path = Path(
        row["image_path"]
    )

    stages = parse_semicolon_text(
        row["source_stages"]
    )

    suctions = parse_semicolon_numbers(
        row["source_suctions_kPa"]
    )

    peaks = parse_semicolon_numbers(
        row["source_q_peaks_kPa"]
    )

    n_stages = int(
        row["source_rows"]
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
                "metadata_mismatch",
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
        x_rect_method,
        y_rect_method,
    ) = detect_plot_rect(
        rgb
    )

    rect = (
        x_left,
        x_right,
        y_top,
        y_bottom,
    )

    y_max, y_scale_method = infer_ymax(
        rgb,
        rect,
    )

    x_max, x_scale_method = infer_xmax(
        rgb,
        rect,
        n_stages,
    )

    if y_max is None:
        qc_rows.append({
            "figure_id":
                figure,
            "specimen_id":
                specimen,
            "status":
                "y_axis_detection_failed",
            "n_stages":
                n_stages,
        })

        continue

    if n_stages == 1:
        extracted = [
            extract_single_curve(
                rgb,
                rect,
            )
        ]
    else:
        extracted = (
            extract_multistage_curves(
                rgb,
                rect,
                n_stages,
            )
        )

    if len(extracted) != n_stages:
        qc_rows.append({
            "figure_id":
                figure,
            "specimen_id":
                specimen,
            "status":
                "curve_count_mismatch",
            "n_stages":
                n_stages,
            "curves_detected":
                len(extracted),
            "x_max_pct":
                x_max,
            "y_max_kPa":
                y_max,
        })

        continue

    specimen_frames = []
    peak_errors = []

    for i, points in enumerate(
        extracted
    ):
        curve = physical_curve(
            points,
            rect,
            x_max,
            y_max,
        )

        if len(curve) < 15:
            continue

        # Stage-local strain:
        # remove cumulative offset shown in multistage plots.
        local_start = float(
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
            - local_start
        )

        curve[
            "figure_id"
        ] = figure

        curve[
            "specimen_id"
        ] = specimen

        curve[
            "stage_index"
        ] = i + 1

        curve[
            "stage"
        ] = stages[i]

        curve[
            "matric_suction_kPa"
        ] = suctions[i]

        curve[
            "source_q_peak_kPa"
        ] = peaks[i]

        digitized_peak = float(
            curve[
                "q_smooth_kPa"
            ].max()
        )

        peak_error_pct = (
            100.0
            * (
                digitized_peak
                - peaks[i]
            )
            / peaks[i]
        )

        peak_errors.append(
            peak_error_pct
        )

        specimen_frames.append(
            curve
        )

    if len(specimen_frames) != n_stages:
        qc_rows.append({
            "figure_id":
                figure,
            "specimen_id":
                specimen,
            "status":
                "postprocessing_stage_mismatch",
            "n_stages":
                n_stages,
            "stages_processed":
                len(
                    specimen_frames
                ),
        })

        continue

    specimen_df = pd.concat(
        specimen_frames,
        ignore_index=True,
    )

    out = (
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
        out,
        index=False,
    )

    all_curves.append(
        specimen_df
    )

    abs_errors = np.abs(
        peak_errors
    )

    qc_rows.append({
        "figure_id":
            figure,

        "specimen_id":
            specimen,

        "status":
            (
                "PASS"
                if np.max(
                    abs_errors
                ) <= 7.5
                else "REVIEW"
            ),

        "n_stages":
            n_stages,

        "x_max_pct":
            x_max,

        "y_max_kPa":
            y_max,

        "x_rect_method":
            x_rect_method,

        "y_rect_method":
            y_rect_method,

        "x_scale_method":
            x_scale_method,

        "y_scale_method":
            y_scale_method,

        "peak_error_mean_abs_pct":
            float(
                np.mean(
                    abs_errors
                )
            ),

        "peak_error_max_abs_pct":
            float(
                np.max(
                    abs_errors
                )
            ),

        "stage_peak_errors_pct":
            ";".join(
                f"{x:+.2f}"
                for x in peak_errors
            ),

        "output_csv":
            str(out),
    })


qc = pd.DataFrame(
    qc_rows
)

qc.to_csv(
    SUMMARY_OUT,
    index=False,
)

if all_curves:
    master = pd.concat(
        all_curves,
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
    "Figures attempted :",
    len(manifest),
)

print(
    "Figures PASS      :",
    int(
        (
            qc["status"]
            == "PASS"
        ).sum()
    ),
)

print(
    "Figures REVIEW    :",
    int(
        (
            qc["status"]
            == "REVIEW"
        ).sum()
    ),
)

failure_statuses = qc[
    ~qc["status"].isin(
        [
            "PASS",
            "REVIEW",
        ]
    )
]

print(
    "Figures failed    :",
    len(
        failure_statuses
    ),
)

if "n_stages" in qc.columns:
    passed = qc[
        qc["status"].isin(
            [
                "PASS",
                "REVIEW",
            ]
        )
    ]

    print(
        "Stages extracted :",
        int(
            passed[
                "n_stages"
            ].sum()
        ),
    )

if (
    "peak_error_mean_abs_pct"
    in qc.columns
):
    valid = qc[
        qc[
            "peak_error_mean_abs_pct"
        ].notna()
    ]

    if not valid.empty:
        print(
            "Median mean peak error:",
            f"{valid['peak_error_mean_abs_pct'].median():.2f} %",
        )

        print(
            "90th pct mean error    :",
            f"{valid['peak_error_mean_abs_pct'].quantile(0.90):.2f} %",
        )

        print(
            "Worst max peak error   :",
            f"{valid['peak_error_max_abs_pct'].max():.2f} %",
        )

print()
print("=== NON-PASS CASES ===")

nonpass = qc[
    qc["status"] != "PASS"
]

if nonpass.empty:
    print("None")
else:
    columns = [
        c
        for c in [
            "figure_id",
            "specimen_id",
            "status",
            "n_stages",
            "x_max_pct",
            "y_max_kPa",
            "peak_error_mean_abs_pct",
            "peak_error_max_abs_pct",
            "stage_peak_errors_pct",
        ]
        if c in nonpass.columns
    ]

    print(
        nonpass[
            columns
        ].to_string(
            index=False
        )
    )

print()
print(
    "QC table:",
    SUMMARY_OUT,
)

print(
    "Master curves:",
    MASTER_OUT,
)

print()
print(
    "PHASE 4H BULK STRESS-STRAIN DIGITIZATION: COMPLETE"
)
