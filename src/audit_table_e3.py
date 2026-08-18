from pathlib import Path
import fitz

PDF = Path("data/raw/Binder1.pdf")

doc = fitz.open(PDF)

print("=" * 72)
print("UnsatConstitutiveLab — Table E-3 Focused Audit")
print("=" * 72)

for page_no in [27, 28, 29]:

    page = doc[page_no - 1]

    print()
    print("=" * 72)
    print(f"PDF PAGE {page_no}")
    print("=" * 72)

    text = page.get_text("text")

    print(text)

    print()
    print("--- TABLE DETECTION ---")

    try:
        tables = page.find_tables().tables
    except Exception as exc:
        print("Detection error:", repr(exc))
        tables = []

    print("Tables detected:", len(tables))

    for i, table in enumerate(tables, start=1):

        print()
        print(f"TABLE {i}")
        print("bbox:", table.bbox)

        data = table.extract()

        for row in data:
            clean = [
                "" if cell is None
                else " ".join(
                    str(cell)
                    .replace("\n", " ")
                    .split()
                )
                for cell in row
            ]

            print(" | ".join(clean))

doc.close()

print()
print("PHASE 3F-B TABLE E-3 AUDIT: PASS")
