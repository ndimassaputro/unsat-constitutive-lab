from pathlib import Path
import re

import fitz
import pandas as pd

PDF = Path("data/raw/Binder1.pdf")
TEXT_OUT = Path("data/processed/binder1_extracted_text.txt")
TABLE_OUT = Path("results/tables/pdf_keyword_inventory.csv")

TEXT_OUT.parent.mkdir(parents=True, exist_ok=True)
TABLE_OUT.parent.mkdir(parents=True, exist_ok=True)

KEYWORDS = [
    "unsaturated triaxial",
    "single stage",
    "single-stage",
    "multistage",
    "multi-stage",
    "matric suction",
    "suction",
    "axial strain",
    "deviator stress",
    "deviatoric stress",
    "stress-strain",
    "stress strain",
    "confining pressure",
    "confining stress",
    "net normal stress",
    "net confining",
    "effective stress",
    "pore water pressure",
    "water content",
    "degree of saturation",
    "pressure plate",
    "soil-water characteristic",
    "soil water characteristic",
    "failure envelope",
    "shear strength",
    "apparent cohesion",
    "friction angle",
]

doc = fitz.open(PDF)

pages = []
all_text_parts = []

for i, page in enumerate(doc):
    text = page.get_text("text")
    pages.append({
        "pdf_page": i + 1,
        "printed_page_guess": None,
        "text": text,
    })
    all_text_parts.append(
        f"\n{'=' * 78}\nPDF PAGE {i + 1}\n{'=' * 78}\n{text}"
    )

TEXT_OUT.write_text(
    "".join(all_text_parts),
    encoding="utf-8",
)

rows = []

for keyword in KEYWORDS:
    matched_pages = []
    total_occurrences = 0

    for page in pages:
        text_lower = page["text"].lower()
        n = text_lower.count(keyword.lower())

        if n:
            matched_pages.append(page["pdf_page"])
            total_occurrences += n

    rows.append({
        "keyword": keyword,
        "occurrences": total_occurrences,
        "pdf_pages": ", ".join(map(str, matched_pages)),
    })

inventory = pd.DataFrame(rows)
inventory.to_csv(TABLE_OUT, index=False)

# ------------------------------------------------------------------
# Find likely tables / figures / test identifiers
# ------------------------------------------------------------------

table_refs = []
figure_refs = []
test_refs = []

for page in pages:
    text = page["text"]

    for match in re.findall(
        r"\bTable\s+[A-Z]?-?\d+(?:[-–]\d+)?",
        text,
        flags=re.IGNORECASE,
    ):
        table_refs.append((page["pdf_page"], match.strip()))

    for match in re.findall(
        r"\bFigure\s+[A-Z]?-?\d+(?:[-–]\d+)?",
        text,
        flags=re.IGNORECASE,
    ):
        figure_refs.append((page["pdf_page"], match.strip()))

    for match in re.findall(
        r"\bST-\d+\b",
        text,
        flags=re.IGNORECASE,
    ):
        test_refs.append((page["pdf_page"], match.upper()))

# ------------------------------------------------------------------
# Compact page snippets for key concepts
# ------------------------------------------------------------------

FOCUS_TERMS = [
    "unsaturated triaxial",
    "axial strain",
    "deviator stress",
    "matric suction",
    "failure envelope",
    "apparent cohesion",
]

focus_pages = set()

for page in pages:
    lower = page["text"].lower()
    if any(term in lower for term in FOCUS_TERMS):
        focus_pages.add(page["pdf_page"])

# ------------------------------------------------------------------
# Report
# ------------------------------------------------------------------

nonempty = sum(bool(p["text"].strip()) for p in pages)

print("==============================================================")
print("UnsatConstitutiveLab — Binder1.pdf Structural Audit")
print("==============================================================")
print()
print("PDF pages                 :", len(doc))
print("Pages with extractable text:", nonempty)
print("Extracted text            :", TEXT_OUT)
print("Keyword inventory         :", TABLE_OUT)

print()
print("=== KEYWORD INVENTORY ===")
print(
    inventory[
        inventory["occurrences"] > 0
    ].to_string(index=False)
)

print()
print("=== UNIQUE ST SAMPLE IDs FOUND ===")
unique_tests = sorted(
    {item for _, item in test_refs},
    key=lambda s: int(s.split("-")[1]),
)
print("Count:", len(unique_tests))
print(", ".join(unique_tests) if unique_tests else "[none]")

print()
print("=== LIKELY TABLE REFERENCES ===")
seen = set()
for page_no, ref in table_refs:
    key = ref.lower()
    if key not in seen:
        seen.add(key)
        print(f"PDF page {page_no:>2}: {ref}")

print()
print("=== LIKELY FIGURE REFERENCES ===")
seen = set()
for page_no, ref in figure_refs:
    key = ref.lower()
    if key not in seen:
        seen.add(key)
        print(f"PDF page {page_no:>2}: {ref}")

print()
print("=== FOCUS PAGES ===")
print(", ".join(map(str, sorted(focus_pages))))

print()
print("=== SHORT TEXT PREVIEWS FROM FOCUS PAGES ===")

for page_no in sorted(focus_pages)[:15]:
    text = pages[page_no - 1]["text"]
    compact = re.sub(r"\s+", " ", text).strip()

    print()
    print(f"[PDF PAGE {page_no}]")
    print(compact[:650])

doc.close()

print()
print("PHASE 1B PDF STRUCTURAL AUDIT: PASS")
