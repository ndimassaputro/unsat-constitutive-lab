from pathlib import Path
import re

import fitz
import pandas as pd

PDF = Path("data/raw/Binder1.pdf")
STRENGTH = Path(
    "data/processed/strength_analysis_ready.csv"
)

OUT = Path(
    "results/tables/stress_strain_plot_manifest.csv"
)

OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

strength = pd.read_csv(STRENGTH)

doc = fitz.open(PDF)

records = []

# Appendix-F specimen figures with embedded plot images.
for page_no in range(44, 67):

    page = doc[page_no - 1]
    page_area = (
        page.rect.width
        * page.rect.height
    )

    # --------------------------------------------------------
    # Find likely figure-caption text blocks.
    # --------------------------------------------------------

    blocks = page.get_text("blocks")

    captions = []

    for block in blocks:

        x0, y0, x1, y1, text, *_ = block

        clean = " ".join(
            text.split()
        )

        if re.search(
            r"Figure\s+F-\d+",
            clean,
            flags=re.IGNORECASE,
        ):
            captions.append({
                "x0": float(x0),
                "y0": float(y0),
                "x1": float(x1),
                "y1": float(y1),
                "text": clean,
            })

    # --------------------------------------------------------
    # Find large embedded images.
    #
    # Based on the audit, stress-strain panels occupy about
    # 15.5% of the page and are ~660 x 495 px.
    # --------------------------------------------------------

    infos = page.get_image_info(
        hashes=True,
        xrefs=True,
    )

    plots = []

    for info in infos:

        bbox = fitz.Rect(
            info["bbox"]
        )

        fraction = (
            bbox.width
            * bbox.height
            / page_area
        )

        pixel_width = int(
            info.get(
                "width",
                0,
            )
        )

        pixel_height = int(
            info.get(
                "height",
                0,
            )
        )

        is_plot_candidate = (
            fraction >= 0.10
            and pixel_width >= 600
            and pixel_height >= 450
        )

        if not is_plot_candidate:
            continue

        plots.append({
            "xref":
                int(info.get("xref", 0)),

            "pixel_width":
                pixel_width,

            "pixel_height":
                pixel_height,

            "bbox":
                bbox,

            "page_fraction":
                fraction,
        })

    plots = sorted(
        plots,
        key=lambda p:
            p["bbox"].x0,
    )

    # --------------------------------------------------------
    # Pair each image with the nearest caption.
    # Prefer captions below the image and horizontally nearby.
    # --------------------------------------------------------

    for plot_index, plot in enumerate(
        plots,
        start=1,
    ):

        bbox = plot["bbox"]

        plot_cx = (
            bbox.x0
            + bbox.x1
        ) / 2.0

        candidates = []

        for caption in captions:

            cap_cx = (
                caption["x0"]
                + caption["x1"]
            ) / 2.0

            horizontal_distance = abs(
                cap_cx
                - plot_cx
            )

            if caption["y0"] >= (
                bbox.y1 - 8
            ):
                vertical_distance = (
                    caption["y0"]
                    - bbox.y1
                )
            else:
                vertical_distance = (
                    1000
                    + abs(
                        caption["y0"]
                        - bbox.y1
                    )
                )

            score = (
                vertical_distance
                + 0.20
                * horizontal_distance
            )

            candidates.append(
                (
                    score,
                    caption,
                )
            )

        if candidates:

            candidates.sort(
                key=lambda x: x[0]
            )

            caption_text = (
                candidates[0][1]["text"]
            )

        else:
            caption_text = ""

        # ----------------------------------------------------
        # Parse figure number.
        # ----------------------------------------------------

        figure_match = re.search(
            r"Figure\s+(F-\d+)",
            caption_text,
            flags=re.IGNORECASE,
        )

        figure_id = (
            figure_match.group(1)
            if figure_match
            else ""
        )

        # ----------------------------------------------------
        # Parse specimen ID.
        #
        # Accept:
        # ST-36
        # ST36
        # ST-34A
        # ST34A
        # ----------------------------------------------------

        specimen_match = re.search(
            r"\bST[-\s]?(\d+)([A-Za-z]?)\b",
            caption_text,
            flags=re.IGNORECASE,
        )

        if specimen_match:

            specimen_id = (
                "ST-"
                + specimen_match.group(1)
                + specimen_match.group(2).upper()
            )

        else:
            specimen_id = ""

        # ----------------------------------------------------
        # Look up tabulated strength data.
        # ----------------------------------------------------

        matched = strength[
            strength["specimen_id"]
            == specimen_id
        ].copy()

        if matched.empty:

            source_rows = 0
            source_stages = ""
            source_suctions = ""
            source_peaks = ""

        else:

            source_rows = len(
                matched
            )

            source_stages = ";".join(
                matched["stage"]
                .astype(str)
                .tolist()
            )

            source_suctions = ";".join(
                f"{x:.1f}"
                for x in matched[
                    "matric_suction_kPa"
                ]
            )

            source_peaks = ";".join(
                f"{x:.1f}"
                for x in matched[
                    "q_peak_kPa"
                ]
            )

        side = (
            "left"
            if plot_index == 1
            else "right"
            if plot_index == 2
            else f"plot_{plot_index}"
        )

        records.append({
            "pdf_page":
                page_no,

            "side":
                side,

            "xref":
                plot["xref"],

            "pixel_width":
                plot["pixel_width"],

            "pixel_height":
                plot["pixel_height"],

            "page_fraction":
                plot["page_fraction"],

            "figure_id":
                figure_id,

            "specimen_id":
                specimen_id,

            "source_rows":
                source_rows,

            "source_stages":
                source_stages,

            "source_suctions_kPa":
                source_suctions,

            "source_q_peaks_kPa":
                source_peaks,

            "caption":
                caption_text,
        })

doc.close()

manifest = pd.DataFrame(
    records
)

manifest.to_csv(
    OUT,
    index=False,
)

# ------------------------------------------------------------
# QC
# ------------------------------------------------------------

print("=" * 82)
print(
    "UnsatConstitutiveLab — Stress-Strain Plot Manifest"
)
print("=" * 82)

print()
print(
    "Plot images found :",
    len(manifest),
)

print(
    "Unique specimens  :",
    manifest[
        "specimen_id"
    ].replace(
        "",
        pd.NA,
    ).nunique(),
)

resolved = manifest[
    manifest["source_rows"] > 0
]

print(
    "Source-resolved   :",
    len(resolved),
)

unresolved = manifest[
    manifest["source_rows"] == 0
]

print(
    "Source-unresolved :",
    len(unresolved),
)

print()
print("=== MANIFEST PREVIEW ===")

cols = [
    "pdf_page",
    "side",
    "figure_id",
    "specimen_id",
    "pixel_width",
    "pixel_height",
    "source_rows",
    "source_stages",
    "source_suctions_kPa",
    "source_q_peaks_kPa",
]

print(
    manifest[
        cols
    ]
    .head(20)
    .to_string(
        index=False,
    )
)

print()
print("=== UNRESOLVED ===")

if unresolved.empty:

    print(
        "None"
    )

else:

    print(
        unresolved[
            [
                "pdf_page",
                "side",
                "figure_id",
                "specimen_id",
                "caption",
            ]
        ].to_string(
            index=False,
        )
    )

print()
print(
    "Manifest:",
    OUT,
)

print()
print(
    "PHASE 4F STRESS-STRAIN MANIFEST: PASS"
)
