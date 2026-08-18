from pathlib import Path

import fitz
import pandas as pd

PDF = Path("data/raw/Binder1.pdf")
OUT = Path("results/tables/vector_path_inventory.csv")

OUT.parent.mkdir(parents=True, exist_ok=True)

# Representative pages across Appendix F.
PAGES = [44, 45, 46, 47, 67]

doc = fitz.open(PDF)

records = []

print("=" * 88)
print("UnsatConstitutiveLab — Stress-Strain Vector Path Inspection")
print("=" * 88)

for page_no in PAGES:

    page = doc[page_no - 1]
    drawings = page.get_drawings()

    page_records = []

    for idx, drawing in enumerate(drawings):

        items = drawing.get("items", [])

        n_line = sum(
            1 for item in items
            if item and item[0] == "l"
        )

        n_rect = sum(
            1 for item in items
            if item and item[0] == "re"
        )

        n_bezier = sum(
            1 for item in items
            if item and item[0] == "c"
        )

        rect = drawing.get("rect")

        if rect is None:
            continue

        width = float(rect.width)
        height = float(rect.height)

        color = drawing.get("color")
        fill = drawing.get("fill")
        stroke_width = drawing.get("width")

        row = {
            "pdf_page": page_no,
            "path_index": idx,
            "n_items": len(items),
            "n_line": n_line,
            "n_rect": n_rect,
            "n_bezier": n_bezier,
            "x0": float(rect.x0),
            "y0": float(rect.y0),
            "x1": float(rect.x1),
            "y1": float(rect.y1),
            "bbox_width": width,
            "bbox_height": height,
            "stroke_width": stroke_width,
            "color": repr(color),
            "fill": repr(fill),
        }

        records.append(row)
        page_records.append(row)

    candidates = pd.DataFrame(page_records)

    if not candidates.empty:

        # Candidate data curves tend to:
        # - contain multiple line segments
        # - span non-trivial width and height
        # Axes/gridlines usually have very small path complexity.
        candidates["candidate_score"] = (
            candidates["n_line"]
            * (
                candidates["bbox_width"]
                * candidates["bbox_height"]
            ) ** 0.25
        )

        candidates = candidates[
            (candidates["n_line"] >= 3)
            & (candidates["bbox_width"] >= 20)
            & (candidates["bbox_height"] >= 5)
        ].sort_values(
            "candidate_score",
            ascending=False,
        )

    print()
    print("=" * 88)
    print(f"PDF PAGE {page_no}")
    print("=" * 88)

    print("Total drawing paths:", len(drawings))
    print(
        "Paths with >=3 line segments:",
        sum(
            row["n_line"] >= 3
            for row in page_records
        ),
    )

    print()
    print("=== TOP VECTOR-PATH CANDIDATES ===")

    if candidates.empty:
        print("[none]")
    else:
        cols = [
            "path_index",
            "n_items",
            "n_line",
            "bbox_width",
            "bbox_height",
            "x0",
            "y0",
            "x1",
            "y1",
            "stroke_width",
            "color",
        ]

        print(
            candidates[
                cols
            ]
            .head(15)
            .to_string(
                index=False,
                float_format=lambda x: f"{x:.2f}",
            )
        )

doc.close()

inventory = pd.DataFrame(records)

inventory.to_csv(
    OUT,
    index=False,
)

print()
print("=" * 88)
print("GLOBAL SUMMARY")
print("=" * 88)

print("Pages inspected :", len(PAGES))
print("Drawing paths   :", len(inventory))

if not inventory.empty:

    print(
        "Line segments   :",
        int(inventory["n_line"].sum()),
    )

    complex_paths = inventory[
        inventory["n_line"] >= 10
    ]

    print(
        "Paths >=10 lines:",
        len(complex_paths),
    )

    print()
    print(
        "Largest line-path complexity:",
        int(inventory["n_line"].max()),
    )

print()
print("Saved:", OUT)

print()
print(
    "PHASE 4B VECTOR PATH INSPECTION: PASS"
)
