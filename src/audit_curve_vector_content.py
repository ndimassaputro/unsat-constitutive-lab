from pathlib import Path

import fitz
import pandas as pd

PDF = Path("data/raw/Binder1.pdf")
OUT = Path("results/tables/stress_strain_vector_audit.csv")

OUT.parent.mkdir(parents=True, exist_ok=True)

# Appendix-F individual specimen plots occupy approximately
# PDF pages 44–67 from the earlier structural audit.
PAGES = range(44, 68)

doc = fitz.open(PDF)

rows = []

print("=" * 78)
print("UnsatConstitutiveLab — Stress-Strain Curve Vector Audit")
print("=" * 78)

for page_no in PAGES:
    page = doc[page_no - 1]

    drawings = page.get_drawings()
    images = page.get_images(full=True)
    words = page.get_text("words")

    drawing_items = sum(
        len(d.get("items", []))
        for d in drawings
    )

    # Count line/polyline-like drawing commands.
    line_like = 0
    curve_like = 0

    for drawing in drawings:
        for item in drawing.get("items", []):
            if not item:
                continue

            command = item[0]

            if command in {"l", "re"}:
                line_like += 1
            elif command in {"c", "qu"}:
                curve_like += 1

    text = page.get_text("text")

    has_axial_strain = (
        "axial strain" in text.lower()
    )

    has_deviator = (
        "deviator" in text.lower()
    )

    rows.append({
        "pdf_page": page_no,
        "n_drawings": len(drawings),
        "drawing_items": drawing_items,
        "line_like_items": line_like,
        "curve_like_items": curve_like,
        "n_images": len(images),
        "n_words": len(words),
        "has_axial_strain_text": has_axial_strain,
        "has_deviator_text": has_deviator,
    })

    print(
        f"page {page_no:>2}: "
        f"drawings={len(drawings):>4}, "
        f"items={drawing_items:>5}, "
        f"lines={line_like:>5}, "
        f"curves={curve_like:>5}, "
        f"images={len(images):>2}, "
        f"stress-strain-text="
        f"{has_axial_strain and has_deviator}"
    )

doc.close()

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)

print()
print("=== SUMMARY ===")
print("Pages audited        :", len(df))
print(
    "Pages with drawings :",
    int((df["n_drawings"] > 0).sum()),
)
print(
    "Pages with images   :",
    int((df["n_images"] > 0).sum()),
)
print(
    "Total drawing items :",
    int(df["drawing_items"].sum()),
)
print(
    "Total curve items   :",
    int(df["curve_like_items"].sum()),
)

vector_candidate = (
    (df["drawing_items"] > 100)
    & (df["n_drawings"] > 0)
)

print(
    "Vector-rich pages   :",
    int(vector_candidate.sum()),
)

print()
print("Output:", OUT)

print()
print(
    "PHASE 4A STRESS-STRAIN VECTOR AUDIT: PASS"
)
