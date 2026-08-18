from pathlib import Path
from collections import defaultdict
import math

import fitz
import pandas as pd

PDF = Path("data/raw/Binder1.pdf")

OUT = Path(
    "results/tables/fragmented_vector_style_inventory.csv"
)
OUT.parent.mkdir(parents=True, exist_ok=True)

# Representative stress-strain figure pages.
PAGES = [44, 45, 46, 47]

doc = fitz.open(PDF)

records = []

print("=" * 92)
print(
    "UnsatConstitutiveLab — Fragmented Vector Style Audit"
)
print("=" * 92)


def style_key(drawing):
    color = drawing.get("color")
    width = drawing.get("width")

    if color is None:
        color_key = "None"
    else:
        color_key = tuple(
            round(float(v), 4)
            for v in color
        )

    if width is None:
        width_key = None
    else:
        width_key = round(
            float(width),
            4,
        )

    return color_key, width_key


for page_no in PAGES:

    page = doc[page_no - 1]
    drawings = page.get_drawings()

    grouped = defaultdict(list)

    for path_index, drawing in enumerate(drawings):

        key = style_key(drawing)

        for item_index, item in enumerate(
            drawing.get("items", [])
        ):

            if not item:
                continue

            if item[0] != "l":
                continue

            # PyMuPDF line command:
            # ('l', Point(x0,y0), Point(x1,y1))
            p0 = item[1]
            p1 = item[2]

            x0 = float(p0.x)
            y0 = float(p0.y)
            x1 = float(p1.x)
            y1 = float(p1.y)

            length = math.hypot(
                x1 - x0,
                y1 - y0,
            )

            grouped[key].append({
                "path_index": path_index,
                "item_index": item_index,
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "length": length,
            })

    page_rows = []

    for (
        color,
        width,
    ), segments in grouped.items():

        xs = []
        ys = []

        for s in segments:
            xs.extend([
                s["x0"],
                s["x1"],
            ])
            ys.extend([
                s["y0"],
                s["y1"],
            ])

        total_length = sum(
            s["length"]
            for s in segments
        )

        x_min = min(xs)
        x_max = max(xs)
        y_min = min(ys)
        y_max = max(ys)

        bbox_width = (
            x_max - x_min
        )
        bbox_height = (
            y_max - y_min
        )

        n_paths = len({
            s["path_index"]
            for s in segments
        })

        median_length = float(
            pd.Series(
                [
                    s["length"]
                    for s in segments
                ]
            ).median()
        )

        row = {
            "pdf_page": page_no,
            "color": repr(color),
            "stroke_width": width,
            "n_segments": len(segments),
            "n_paths": n_paths,
            "total_length": total_length,
            "median_segment_length": median_length,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "bbox_width": bbox_width,
            "bbox_height": bbox_height,
        }

        records.append(row)
        page_rows.append(row)

    table = pd.DataFrame(
        page_rows
    )

    print()
    print("=" * 92)
    print(
        f"PDF PAGE {page_no}"
    )
    print("=" * 92)

    print(
        "Drawing paths :",
        len(drawings),
    )
    print(
        "Line segments :",
        sum(
            len(v)
            for v in grouped.values()
        ),
    )
    print(
        "Stroke styles :",
        len(grouped),
    )

    if table.empty:
        print(
            "\n[No vector line segments]"
        )
        continue

    # Rank styles likely to represent plotted data:
    # many segments + non-trivial x/y span.
    table["candidate_score"] = (
        table["n_segments"]
        * (
            table["bbox_width"]
            * table["bbox_height"]
        ) ** 0.25
    )

    candidates = table[
        (table["n_segments"] >= 5)
        & (table["bbox_width"] >= 20)
        & (table["bbox_height"] >= 10)
    ].sort_values(
        "candidate_score",
        ascending=False,
    )

    print()
    print(
        "=== TOP STYLE GROUPS ==="
    )

    if candidates.empty:
        print("[none]")
    else:
        print(
            candidates[
                [
                    "color",
                    "stroke_width",
                    "n_segments",
                    "n_paths",
                    "total_length",
                    "median_segment_length",
                    "bbox_width",
                    "bbox_height",
                    "x_min",
                    "x_max",
                    "y_min",
                    "y_max",
                ]
            ]
            .head(15)
            .to_string(
                index=False,
                float_format=lambda x:
                    f"{x:.2f}",
            )
        )


doc.close()

inventory = pd.DataFrame(
    records
)

inventory.to_csv(
    OUT,
    index=False,
)

print()
print("=" * 92)
print("GLOBAL SUMMARY")
print("=" * 92)

print(
    "Rows saved:",
    len(inventory),
)

if not inventory.empty:

    print(
        "Maximum segments in one style:",
        int(
            inventory[
                "n_segments"
            ].max()
        ),
    )

    print(
        "Style groups >=20 segments:",
        int(
            (
                inventory[
                    "n_segments"
                ] >= 20
            ).sum()
        ),
    )

print()
print(
    "Saved:",
    OUT,
)

print()
print(
    "PHASE 4C FRAGMENTED VECTOR STYLE AUDIT: PASS"
)
