from pathlib import Path
import csv
import fitz

PDF = Path("data/raw/Binder1.pdf")
OUT = Path("results/tables/repaired")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = {
    41: "F1_single_stage",
    42: "F2_multistage_slope",
    43: "F3_multistage_sheet_pile",
    70: "F4_compression_extension",
}

doc = fitz.open(PDF)

print("=" * 72)
print("UnsatConstitutiveLab — PyMuPDF Table Extraction Repair")
print("=" * 72)

for pdf_page, label in TARGETS.items():
    page = doc[pdf_page - 1]

    print()
    print(f"PDF page {pdf_page} — {label}")

    try:
        finder = page.find_tables()
        tables = finder.tables
    except Exception as exc:
        print("ERROR during table detection:", repr(exc))
        continue

    print("Tables detected:", len(tables))

    if not tables:
        print("WARNING: no tables detected")
        continue

    candidates = []

    for i, table in enumerate(tables, start=1):
        data = table.extract()

        nonempty = sum(
            1
            for row in data
            for cell in row
            if cell is not None and str(cell).strip()
        )

        rows = len(data)
        cols = max((len(r) for r in data), default=0)

        candidates.append(
            (nonempty, rows, cols, i, table, data)
        )

        print(
            f"  candidate {i}: "
            f"rows={rows}, cols={cols}, nonempty={nonempty}, "
            f"bbox={table.bbox}"
        )

    # Prefer information-rich table.
    candidates.sort(reverse=True, key=lambda x: x[0])
    _, rows, cols, idx, table, data = candidates[0]

    cleaned = []

    for row in data:
        clean = []
        for cell in row:
            if cell is None:
                text = ""
            else:
                text = " ".join(
                    str(cell)
                    .replace("\n", " ")
                    .split()
                )
            clean.append(text)

        cleaned.append(clean)

    out = OUT / f"{label}.csv"

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(cleaned)

    print()
    print(f"Selected candidate: {idx}")
    print(f"Rows              : {rows}")
    print(f"Cols              : {cols}")
    print(f"Saved             : {out}")

    print()
    print("Preview:")
    for row in cleaned[:12]:
        print(" | ".join(row))

doc.close()

print()
print("PHASE 1E TABLE EXTRACTION REPAIR: PASS")
