from pathlib import Path

import fitz
import pandas as pd

PDF = Path("data/raw/Binder1.pdf")
OUT = Path("results/tables/embedded_plot_image_inventory.csv")
IMG_OUT = Path("results/figures/embedded_image_audit")

OUT.parent.mkdir(parents=True, exist_ok=True)
IMG_OUT.mkdir(parents=True, exist_ok=True)

PAGES = [44, 45, 46, 47]

doc = fitz.open(PDF)

records = []

print("=" * 88)
print("UnsatConstitutiveLab — Embedded Plot Image Audit")
print("=" * 88)

for page_no in PAGES:
    page = doc[page_no - 1]
    rect = page.rect

    infos = page.get_image_info(
        hashes=True,
        xrefs=True,
    )

    print()
    print("=" * 88)
    print(f"PDF PAGE {page_no}")
    print("=" * 88)

    print(
        f"Page size: {rect.width:.1f} x {rect.height:.1f} pt"
    )
    print("Embedded images:", len(infos))

    if not infos:
        continue

    for i, info in enumerate(infos, start=1):
        bbox = fitz.Rect(info["bbox"])

        bbox_w = float(bbox.width)
        bbox_h = float(bbox.height)

        page_fraction = (
            bbox_w * bbox_h
            / (rect.width * rect.height)
        )

        row = {
            "pdf_page": page_no,
            "image_index": i,
            "xref": info.get("xref", 0),
            "pixel_width": info.get("width"),
            "pixel_height": info.get("height"),
            "colorspace": info.get("cs-name"),
            "bpc": info.get("bpc"),
            "bbox_x0": bbox.x0,
            "bbox_y0": bbox.y0,
            "bbox_x1": bbox.x1,
            "bbox_y1": bbox.y1,
            "bbox_width_pt": bbox_w,
            "bbox_height_pt": bbox_h,
            "page_area_fraction": page_fraction,
        }

        records.append(row)

        print()
        print(
            f"Image {i}: "
            f"xref={row['xref']}, "
            f"pixels={row['pixel_width']}x{row['pixel_height']}"
        )
        print(
            f"  bbox=({bbox.x0:.1f}, {bbox.y0:.1f}) "
            f"to ({bbox.x1:.1f}, {bbox.y1:.1f})"
        )
        print(
            f"  placed size="
            f"{bbox_w:.1f} x {bbox_h:.1f} pt"
        )
        print(
            f"  page coverage="
            f"{100 * page_fraction:.1f}%"
        )

        xref = info.get("xref", 0)

        if xref:
            try:
                extracted = doc.extract_image(xref)

                ext = extracted["ext"]
                data = extracted["image"]

                path = (
                    IMG_OUT
                    / f"page_{page_no:02d}_img_{i:02d}_xref_{xref}.{ext}"
                )

                path.write_bytes(data)

                print(
                    f"  extracted={path}"
                )

            except Exception as exc:
                print(
                    "  extraction warning:",
                    repr(exc),
                )

doc.close()

df = pd.DataFrame(records)

df.to_csv(
    OUT,
    index=False,
)

print()
print("=" * 88)
print("GLOBAL SUMMARY")
print("=" * 88)

print("Images found:", len(df))

if not df.empty:
    print(
        "Median pixel dimensions:",
        f"{df['pixel_width'].median():.0f} x "
        f"{df['pixel_height'].median():.0f}",
    )

    print(
        "Largest page coverage:",
        f"{100 * df['page_area_fraction'].max():.1f}%",
    )

    large = df[
        df["page_area_fraction"] >= 0.05
    ]

    print(
        "Images covering >=5% page:",
        len(large),
    )

print()
print("Inventory:", OUT)
print("Extracted images:", IMG_OUT)

print()
print(
    "PHASE 4D EMBEDDED IMAGE AUDIT: PASS"
)
