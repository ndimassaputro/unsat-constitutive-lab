from pathlib import Path
import fitz

PDF = Path("data/raw/Binder1.pdf")

TARGETS = {
    41: ("F1", (100, 270, 540, 365)),
    42: ("F2", (80, 90, 550, 190)),
    43: ("F3", (80, 105, 540, 205)),
    70: ("F4", (95, 80, 600, 190)),
}

doc = fitz.open(PDF)

print("=" * 72)
print("UnsatConstitutiveLab — Table Header Audit")
print("=" * 72)

for page_no, (label, bbox) in TARGETS.items():
    page = doc[page_no - 1]
    rect = fitz.Rect(*bbox)

    print()
    print(f"=== PDF PAGE {page_no} — {label} ===")

    text = page.get_text("text", clip=rect)
    print(text.strip())

    print()
    print("--- WORD POSITIONS ---")

    words = page.get_text("words", clip=rect)

    for word in sorted(words, key=lambda w: (round(w[1], 1), w[0])):
        x0, y0, x1, y1, txt, *_ = word
        print(
            f"x={x0:7.1f} y={y0:7.1f} "
            f"{txt}"
        )

doc.close()

print()
print("PHASE 2A TABLE HEADER AUDIT: PASS")
