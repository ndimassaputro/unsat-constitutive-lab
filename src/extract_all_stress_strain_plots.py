from pathlib import Path
import re

import fitz
import pandas as pd
from PIL import Image, ImageDraw, ImageOps

PDF = Path("data/raw/Binder1.pdf")
MANIFEST = Path(
    "results/tables/stress_strain_plot_manifest_corrected.csv"
)

OUT_DIR = Path(
    "results/figures/stress_strain_raw"
)

CONTACT = Path(
    "results/figures/"
    "stress_strain_representative_contact_sheet.png"
)

META_OUT = Path(
    "results/tables/"
    "stress_strain_image_manifest.csv"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CONTACT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

manifest = pd.read_csv(MANIFEST)

doc = fitz.open(PDF)

records = []

print("=" * 84)
print(
    "UnsatConstitutiveLab — "
    "Bulk Stress-Strain Image Extraction"
)
print("=" * 84)

for _, row in manifest.iterrows():

    fig = str(
        row["figure_id"]
    )

    specimen = str(
        row["specimen_id"]
    )

    xref = int(
        row["xref"]
    )

    extracted = doc.extract_image(
        xref
    )

    ext = extracted["ext"]
    data = extracted["image"]

    fig_safe = fig.replace(
        "-",
        "_",
    )

    specimen_safe = specimen.replace(
        "-",
        "_",
    )

    out = (
        OUT_DIR
        / f"{fig_safe}_{specimen_safe}.{ext}"
    )

    out.write_bytes(data)

    records.append({
        **row.to_dict(),
        "image_path":
            str(out),
        "image_ext":
            ext,
    })

doc.close()

images = pd.DataFrame(
    records
)

images.to_csv(
    META_OUT,
    index=False,
)

# ============================================================
# STRICT EXTRACTION QC
# ============================================================

missing = []

for path in images["image_path"]:
    if not Path(path).exists():
        missing.append(path)

if missing:
    print("MISSING FILES:")
    for path in missing:
        print(" -", path)

    raise SystemExit(
        "BULK IMAGE EXTRACTION: FAIL"
    )

if len(images) != 46:
    raise SystemExit(
        f"Expected 46 images, found {len(images)}"
    )

# ============================================================
# AUTOMATIC REPRESENTATIVE SELECTION
#
# Pick one:
# - single-stage
# - two-stage
# - three-stage
# - four-stage
#
# source_rows is the number of tabulated shearing stages
# for that specimen.
# ============================================================

representatives = []

for label, target_rows in [
    ("single-stage", 1),
    ("two-stage", 2),
    ("three-stage", 3),
    ("four-stage", 4),
]:

    candidates = images[
        images["source_rows"]
        == target_rows
    ].copy()

    if candidates.empty:
        print(
            f"WARNING: no {label} "
            f"candidate found."
        )
        continue

    # Prefer an early figure for each class,
    # except 4-stage where any resolved example is fine.
    chosen = (
        candidates
        .sort_values(
            "figure_number"
        )
        .iloc[0]
    )

    representatives.append(
        (
            label,
            chosen,
        )
    )

# ============================================================
# CONTACT SHEET
# ============================================================

thumb_w = 660
margin = 25
label_h = 62

tiles = []

for label, row in representatives:

    path = Path(
        row["image_path"]
    )

    img = Image.open(
        path
    ).convert(
        "RGB"
    )

    ratio = (
        thumb_w
        / img.width
    )

    thumb_h = int(
        img.height
        * ratio
    )

    thumb = img.resize(
        (
            thumb_w,
            thumb_h,
        ),
        Image.Resampling.LANCZOS,
    )

    tile = Image.new(
        "RGB",
        (
            thumb_w,
            thumb_h
            + label_h,
        ),
        "white",
    )

    tile.paste(
        thumb,
        (
            0,
            label_h,
        ),
    )

    draw = ImageDraw.Draw(
        tile
    )

    title = (
        f"{label} | "
        f"{row['figure_id']} | "
        f"{row['specimen_id']} | "
        f"stages: {row['source_stages']}"
    )

    detail = (
        f"suction: "
        f"{row['source_suctions_kPa']} kPa | "
        f"q_peak: "
        f"{row['source_q_peaks_kPa']} kPa"
    )

    draw.text(
        (
            10,
            8,
        ),
        title,
        fill="black",
    )

    draw.text(
        (
            10,
            31,
        ),
        detail,
        fill="black",
    )

    tile = ImageOps.expand(
        tile,
        border=1,
        fill="gray",
    )

    tiles.append(
        tile
    )

cols = 2

rows = (
    len(tiles)
    + cols
    - 1
) // cols

cell_w = max(
    tile.width
    for tile in tiles
)

cell_h = max(
    tile.height
    for tile in tiles
)

sheet = Image.new(
    "RGB",
    (
        cols * cell_w
        + (cols + 1) * margin,

        rows * cell_h
        + (rows + 1) * margin,
    ),
    "white",
)

for i, tile in enumerate(
    tiles
):

    r = i // cols
    c = i % cols

    x = (
        margin
        + c
        * (
            cell_w
            + margin
        )
    )

    y = (
        margin
        + r
        * (
            cell_h
            + margin
        )
    )

    sheet.paste(
        tile,
        (
            x,
            y,
        ),
    )

sheet.save(
    CONTACT
)

# ============================================================
# REPORT
# ============================================================

print()
print("Images extracted :", len(images))
print(
    "Unique specimens:",
    images[
        "specimen_id"
    ].nunique(),
)

print()
print(
    "=== REPRESENTATIVE CASES ==="
)

for label, row in representatives:

    print()
    print(label)
    print(
        "  figure   :",
        row["figure_id"],
    )
    print(
        "  specimen :",
        row["specimen_id"],
    )
    print(
        "  stages   :",
        row["source_stages"],
    )
    print(
        "  suctions :",
        row["source_suctions_kPa"],
    )
    print(
        "  q peaks  :",
        row["source_q_peaks_kPa"],
    )
    print(
        "  image    :",
        row["image_path"],
    )

print()
print(
    "Image manifest:",
    META_OUT,
)

print(
    "Contact sheet :",
    CONTACT,
)

print()
print(
    "PHASE 4G BULK IMAGE EXTRACTION: PASS"
)
