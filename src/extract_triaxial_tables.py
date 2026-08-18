from pathlib import Path
import csv

import pdfplumber

PDF = Path("data/raw/Binder1.pdf")
OUT = Path("results/tables/raw")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = {
    41: "F1_single_stage",
    42: "F2_multistage_slope",
    43: "F3_multistage_sheet_pile",
    70: "F4_compression_extension",
}

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 4,
    "join_tolerance": 4,
    "intersection_tolerance": 5,
    "edge_min_length": 3,
}

print("=" * 68)
print("UnsatConstitutiveLab — Raw Triaxial Table Extraction")
print("=" * 68)

with pdfplumber.open(PDF) as pdf:
    for pdf_page, label in TARGETS.items():
        page = pdf.pages[pdf_page - 1]

        tables = page.extract_tables(TABLE_SETTINGS)

        if not tables:
            # Fallback if ruling-line detection misses the table.
            tables = page.extract_tables({
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "snap_tolerance": 4,
                "join_tolerance": 4,
            })

        print()
        print(f"PDF page {pdf_page} — {label}")
        print(f"Tables detected: {len(tables)}")

        if not tables:
            print("WARNING: no table extracted")
            continue

        # Choose the table containing the most non-empty cells.
        def score(table):
            return sum(
                1
                for row in table
                for cell in row
                if cell is not None and str(cell).strip()
            )

        table = max(tables, key=score)

        max_cols = max(len(row) for row in table)
        normalized = []

        for row in table:
            clean = [
                "" if cell is None else
                " ".join(str(cell).replace("\n", " ").split())
                for cell in row
            ]
            clean += [""] * (max_cols - len(clean))
            normalized.append(clean)

        out = OUT / f"{label}.csv"

        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(normalized)

        print("Rows :", len(normalized))
        print("Cols :", max_cols)
        print("Saved:", out)

        print()
        print("Preview:")
        for row in normalized[:8]:
            print(" | ".join(row))

print()
print("PHASE 1D RAW TABLE EXTRACTION: PASS")
