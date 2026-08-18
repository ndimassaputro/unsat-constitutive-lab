from pathlib import Path

import fitz
from PIL import Image, ImageOps, ImageDraw

PDF = Path("data/raw/Binder1.pdf")
OUT = Path("results/figures/pdf_audit")
OUT.mkdir(parents=True, exist_ok=True)

# Pages most useful for deciding constitutive-model scope.
# PDF page numbering is 1-based here.
KEY_PAGES = [
    39, 40, 41, 42, 43,
    67, 68, 69, 70,
]

doc = fitz.open(PDF)

rendered = []

for page_no in KEY_PAGES:
    page = doc[page_no - 1]

    pix = page.get_pixmap(
        matrix=fitz.Matrix(1.7, 1.7),
        alpha=False,
    )

    path = OUT / f"binder1_page_{page_no:02d}.png"
    pix.save(path)

    img = Image.open(path).convert("RGB")
    rendered.append((page_no, img))

doc.close()

# ------------------------------------------------------------
# Build contact sheet
# ------------------------------------------------------------

thumb_width = 520
margin = 25
label_h = 36

thumbs = []

for page_no, img in rendered:
    ratio = thumb_width / img.width
    h = int(img.height * ratio)

    thumb = img.resize(
        (thumb_width, h),
        Image.Resampling.LANCZOS,
    )

    canvas = Image.new(
        "RGB",
        (thumb_width, h + label_h),
        "white",
    )

    canvas.paste(thumb, (0, label_h))

    draw = ImageDraw.Draw(canvas)
    draw.text(
        (10, 10),
        f"PDF page {page_no}",
        fill="black",
    )

    canvas = ImageOps.expand(
        canvas,
        border=1,
        fill="gray",
    )

    thumbs.append(canvas)

cols = 3
rows = (len(thumbs) + cols - 1) // cols

cell_w = max(im.width for im in thumbs)
cell_h = max(im.height for im in thumbs)

sheet = Image.new(
    "RGB",
    (
        cols * cell_w + (cols + 1) * margin,
        rows * cell_h + (rows + 1) * margin,
    ),
    "white",
)

for i, img in enumerate(thumbs):
    r = i // cols
    c = i % cols

    x = margin + c * (cell_w + margin)
    y = margin + r * (cell_h + margin)

    sheet.paste(img, (x, y))

contact = OUT / "triaxial_key_pages_contact_sheet.png"
sheet.save(contact, quality=95)

print("====================================================")
print("UnsatConstitutiveLab — Key Triaxial Page Rendering")
print("====================================================")
print()

for page_no, _ in rendered:
    print(
        f"PDF page {page_no:>2}: "
        f"{OUT / f'binder1_page_{page_no:02d}.png'}"
    )

print()
print("Contact sheet:", contact)
print()
print("PHASE 1C KEY-PAGE RENDERING: PASS")
