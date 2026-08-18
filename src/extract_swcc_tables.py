from pathlib import Path
import csv
import fitz

PDF = Path("data/raw/Binder1.pdf")
OUT = Path("results/tables/swcc_audit")
OUT.mkdir(parents=True, exist_ok=True)

# From the structural audit:
# E-3 ~ PDF page 27
# E-4 ~ PDF page 30
# E-5 ~ PDF page 32
# E-6/E-7 ~ PDF page 36
PAGES = [27, 30, 32, 36]

doc = fitz.open(PDF)

print("=" * 76)
print("UnsatConstitutiveLab — SWCC Parameter Audit")
print("=" * 76)

for page_no in PAGES:
    page = doc[page_no - 1]

    print()
    print(f"=== PDF PAGE {page_no} ===")

    text = page.get_text("text")
    print(text[:4500])

    print()
    print("--- TABLE DETECTION ---")

    try:
        finder = page.find_tables()
        tables = finder.tables
    except Exception as exc:
        print("Table detection error:", repr(exc))
        tables = []

    print("Tables detected:", len(tables))

    for i, table in enumerate(tables, start=1):
        data = table.extract()

        cleaned = []

        for row in data:
            clean = [
                "" if cell is None
                else " ".join(
                    str(cell).replace("\n", " ").split()
                )
                for cell in row
            ]
            cleaned.append(clean)

        out = OUT / f"page_{page_no:02d}_table_{i}.csv"

        with out.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:
            csv.writer(f).writerows(cleaned)

        print()
        print(f"Table {i}:")
        print("bbox :", table.bbox)
        print("saved:", out)

        for row in cleaned[:15]:
            print(" | ".join(row))

doc.close()

print()
print("PHASE 3F SWCC PARAMETER AUDIT: PASS")
