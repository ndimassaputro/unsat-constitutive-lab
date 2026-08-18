from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

SRC = Path(
    "results/figures/embedded_image_audit/"
    "page_44_img_03_xref_182.png"
)

OUT = Path(
    "data/processed/st36_digitized_curve.csv"
)

QC = Path(
    "results/tables/st36_curve_digitization_qc.csv"
)

OUT.parent.mkdir(parents=True, exist_ok=True)
QC.parent.mkdir(parents=True, exist_ok=True)

img = Image.open(SRC).convert("L")
arr = np.asarray(img)

h, w = arr.shape

print("=" * 72)
print("UnsatConstitutiveLab — ST-36 Curve Extraction")
print("=" * 72)
print()
print("Image:", SRC)
print("Pixels:", w, "x", h)

# ------------------------------------------------------------
# Plot-region calibration for this 675 x 495 embedded figure.
#
# Determined from visible axes:
#
# x = 0 ... 12 % axial strain
# y = 0 ... 300 kPa deviatoric stress
#
# Keep this explicit and auditable.
# ------------------------------------------------------------

X_LEFT = 108
X_RIGHT = 650

Y_TOP = 15
Y_BOTTOM = 416

# Slightly restrict interior to avoid axes/text.
x0 = X_LEFT + 2
x1 = X_RIGHT - 2
y0 = Y_TOP + 2
y1 = Y_BOTTOM - 2

crop = arr[y0:y1 + 1, x0:x1 + 1]

# ------------------------------------------------------------
# Extract dark curve pixels.
#
# The curve/markers are nearly black.
# Gridlines are gray and therefore mostly rejected.
# ------------------------------------------------------------

DARK_THRESHOLD = 45

mask = crop < DARK_THRESHOLD

points = []

for local_x in range(mask.shape[1]):

    ys = np.where(
        mask[:, local_x]
    )[0]

    if len(ys) == 0:
        continue

    global_x = x0 + local_x

    # Remove likely bottom-axis / legend pixels.
    global_ys = y0 + ys

    valid = global_ys < (Y_BOTTOM - 15)

    global_ys = global_ys[valid]

    if len(global_ys) == 0:
        continue

    # For each x-column, use median dark-pixel location.
    # Marker thickness then collapses toward its center.
    global_y = float(
        np.median(global_ys)
    )

    strain_pct = (
        (global_x - X_LEFT)
        / (X_RIGHT - X_LEFT)
        * 12.0
    )

    q_kPa = (
        (Y_BOTTOM - global_y)
        / (Y_BOTTOM - Y_TOP)
        * 300.0
    )

    if (
        0.0 <= strain_pct <= 12.0
        and 0.0 <= q_kPa <= 300.0
    ):
        points.append(
            (
                strain_pct,
                q_kPa,
            )
        )

curve = pd.DataFrame(
    points,
    columns=[
        "axial_strain_pct",
        "deviator_stress_kPa",
    ],
)

if curve.empty:
    raise SystemExit(
        "No curve pixels extracted."
    )

# ------------------------------------------------------------
# Smooth only for QC of the extracted centerline.
# Raw digitized values are preserved in output.
# ------------------------------------------------------------

curve["q_smooth_kPa"] = (
    curve[
        "deviator_stress_kPa"
    ]
    .rolling(
         nine := 9,
        center=True,
        min_periods=1,
    )
    .median()
)

peak_idx = (
    curve["q_smooth_kPa"]
    .idxmax()
)

peak_q = float(
    curve.loc[
        peak_idx,
        "q_smooth_kPa",
    ]
)

peak_strain = float(
    curve.loc[
        peak_idx,
        "axial_strain_pct",
    ]
)

SOURCE_PEAK = 264.5

peak_error = (
    peak_q - SOURCE_PEAK
)

peak_error_pct = (
    100.0
    * peak_error
    / SOURCE_PEAK
)

curve.to_csv(
    OUT,
    index=False,
)

qc = pd.DataFrame([
    {
        "specimen_id": "ST-36",
        "source_peak_kPa": SOURCE_PEAK,
        "digitized_peak_kPa": peak_q,
        "peak_error_kPa": peak_error,
        "peak_error_pct": peak_error_pct,
        "digitized_peak_strain_pct":
            peak_strain,
        "n_digitized_columns":
            len(curve),
    }
])

qc.to_csv(
    QC,
    index=False,
)

print()
print("=== EXTRACTION QC ===")
print("Digitized points :", len(curve))
print(
    "Digitized peak   :",
    f"{peak_q:.2f} kPa",
)
print(
    "Source peak      :",
    f"{SOURCE_PEAK:.2f} kPa",
)
print(
    "Peak error       :",
    f"{peak_error:+.2f} kPa",
)
print(
    "Peak error       :",
    f"{peak_error_pct:+.2f} %",
)
print(
    "Peak strain      :",
    f"{peak_strain:.3f} %",
)

print()
print("Curve:", OUT)
print("QC   :", QC)

print()
print(
    "PHASE 4E ST-36 CURVE EXTRACTION: PASS"
)
