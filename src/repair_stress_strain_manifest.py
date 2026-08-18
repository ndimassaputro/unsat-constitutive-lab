from pathlib import Path
import re

import fitz
import pandas as pd

PDF = Path("data/raw/Binder1.pdf")
STRENGTH = Path(
    "data/processed/strength_analysis_ready.csv"
)

OUT = Path(
    "results/tables/stress_strain_plot_manifest_corrected.csv"
)

OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

strength = pd.read_csv(STRENGTH)

doc = fitz.open(PDF)

records = []

for page_no in range(44, 67):

    page = doc[page_no - 1]
    page_area = (
        page.rect.width
        * page.rect.height
    )

    # --------------------------------------------------------
    # Large embedded images = candidate stress-strain panels.
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

        pw = int(
            info.get("width", 0)
        )

        ph = int(
            info.get("height", 0)
        )

        if (
            fraction >= 0.10
            and pw >= 600
            and ph >= 450
        ):
            plots.append({
                "xref":
                    int(
                        info.get(
                            "xref",
                            0,
                        )
                    ),

                "pixel_width":
                    pw,

                "pixel_height":
                    ph,

                "bbox":
                    bbox,

                "page_fraction":
                    fraction,
            })

    plots = sorted(
        plots,
        key=lambda x:
            x["bbox"].x0,
    )

    # --------------------------------------------------------
    # Caption extraction.
    #
    # Flatten whitespace so captions split over PDF text lines
    # can still be parsed.
    # --------------------------------------------------------

    text = page.get_text("text")

    compact = re.sub(
        r"\s+",
        " ",
        text,
    )

    # Capture:
    # Figure F-9 ST-124 ...
    # Figure F-18 ST-65A ...
    #
    # Allow spaces / missing dash after ST.
    caption_matches = re.findall(
        r"Figure\s+F-(\d+)"
        r"\s+"
        r"(ST[-\s]?\d+[A-Za-z]?)",
        compact,
        flags=re.IGNORECASE,
    )

    captions = []

    for fig_num, raw_specimen in caption_matches:

        spec_match = re.fullmatch(
            r"ST[-\s]?(\d+)([A-Za-z]?)",
            raw_specimen,
            flags=re.IGNORECASE,
        )

        if spec_match is None:
            continue

        specimen_id = (
            "ST-"
            + spec_match.group(1)
            + spec_match.group(2).upper()
        )

        captions.append({
            "figure_number":
                int(fig_num),

            "figure_id":
                f"F-{int(fig_num)}",

            "specimen_id":
                specimen_id,
        })

    # Remove duplicate text occurrences of same figure.
    unique = {}

    for c in captions:
        unique[
            c["figure_number"]
        ] = c

    captions = sorted(
        unique.values(),
        key=lambda x:
            x["figure_number"],
    )

    # --------------------------------------------------------
    # Pair left-to-right plot panels with increasing figure ID.
    # --------------------------------------------------------

    if len(plots) != len(captions):

        print()
        print(
            f"WARNING page {page_no}: "
            f"{len(plots)} plots but "
            f"{len(captions)} captions"
        )

        print(
            "Captions:",
            captions,
        )

    n_pair = min(
        len(plots),
        len(captions),
    )

    for i in range(n_pair):

        plot = plots[i]
        caption = captions[i]

        specimen_id = (
            caption["specimen_id"]
        )

        matched = strength[
            strength["specimen_id"]
            == specimen_id
        ].copy()

        if matched.empty:
            source_rows = 0
            stages = ""
            suctions = ""
            peaks = ""
        else:
            source_rows = len(
                matched
            )

            stages = ";".join(
                matched["stage"]
                .astype(str)
                .tolist()
            )

            suctions = ";".join(
                f"{v:.1f}"
                for v in matched[
                    "matric_suction_kPa"
                ]
            )

            peaks = ";".join(
                f"{v:.1f}"
                for v in matched[
                    "q_peak_kPa"
                ]
            )

        records.append({
            "pdf_page":
                page_no,

            "side":
                (
                    "left"
                    if i == 0
                    else "right"
                    if i == 1
                    else f"plot_{i + 1}"
                ),

            "figure_number":
                caption[
                    "figure_number"
                ],

            "figure_id":
                caption[
                    "figure_id"
                ],

            "specimen_id":
                specimen_id,

            "xref":
                plot["xref"],

            "pixel_width":
                plot[
                    "pixel_width"
                ],

            "pixel_height":
                plot[
                    "pixel_height"
                ],

            "page_fraction":
                plot[
                    "page_fraction"
                ],

            "source_rows":
                source_rows,

            "source_stages":
                stages,

            "source_suctions_kPa":
                suctions,

            "source_q_peaks_kPa":
                peaks,
        })

doc.close()

manifest = pd.DataFrame(
    records
)

manifest = manifest.sort_values(
    "figure_number"
).reset_index(
    drop=True
)

manifest.to_csv(
    OUT,
    index=False,
)

# ============================================================
# STRICT QC
# ============================================================

expected_figures = set(
    range(2, 48)
)

found_figures = set(
    manifest[
        "figure_number"
    ].tolist()
)

missing_figures = sorted(
    expected_figures
    - found_figures
)

extra_figures = sorted(
    found_figures
    - expected_figures
)

duplicate_figures = (
    manifest[
        manifest[
            "figure_number"
        ].duplicated(
            keep=False
        )
    ][
        [
            "pdf_page",
            "figure_id",
            "specimen_id",
        ]
    ]
)

duplicate_specimens = (
    manifest[
        manifest[
            "specimen_id"
        ].duplicated(
            keep=False
        )
    ][
        [
            "pdf_page",
            "figure_id",
            "specimen_id",
        ]
    ]
)

unresolved = manifest[
    manifest[
        "source_rows"
    ] == 0
]

print("=" * 84)
print(
    "UnsatConstitutiveLab — Corrected Stress-Strain Manifest"
)
print("=" * 84)

print()
print(
    "Plot records       :",
    len(manifest),
)

print(
    "Unique figures     :",
    manifest[
        "figure_number"
    ].nunique(),
)

print(
    "Unique specimens   :",
    manifest[
        "specimen_id"
    ].nunique(),
)

print(
    "Source-resolved    :",
    int(
        (
            manifest[
                "source_rows"
            ] > 0
        ).sum()
    ),
)

print()
print(
    "Missing figures    :",
    missing_figures
    if missing_figures
    else "None",
)

print(
    "Extra figures      :",
    extra_figures
    if extra_figures
    else "None",
)

print()
print(
    "=== DUPLICATE FIGURES ==="
)

if duplicate_figures.empty:
    print("None")
else:
    print(
        duplicate_figures.to_string(
            index=False
        )
    )

print()
print(
    "=== DUPLICATE SPECIMENS ==="
)

if duplicate_specimens.empty:
    print("None")
else:
    print(
        duplicate_specimens.to_string(
            index=False
        )
    )

print()
print(
    "=== UNRESOLVED SOURCE IDS ==="
)

if unresolved.empty:
    print("None")
else:
    print(
        unresolved[
            [
                "pdf_page",
                "figure_id",
                "specimen_id",
            ]
        ].to_string(
            index=False
        )
    )

print()
print(
    "=== FIRST 15 ==="
)

print(
    manifest[
        [
            "pdf_page",
            "side",
            "figure_id",
            "specimen_id",
            "source_rows",
            "source_stages",
            "source_suctions_kPa",
            "source_q_peaks_kPa",
        ]
    ]
    .head(15)
    .to_string(
        index=False
    )
)

print()
print(
    "=== LAST 10 ==="
)

print(
    manifest[
        [
            "pdf_page",
            "side",
            "figure_id",
            "specimen_id",
            "source_rows",
            "source_stages",
        ]
    ]
    .tail(10)
    .to_string(
        index=False
    )
)

# Hard fail if the expected 46-figure structure is not recovered.
if (
    len(manifest) != 46
    or manifest[
        "figure_number"
    ].nunique() != 46
    or missing_figures
    or extra_figures
    or not duplicate_figures.empty
):
    raise SystemExit(
        "PHASE 4F-B MANIFEST REPAIR: FAIL"
    )

print()
print(
    "PHASE 4F-B MANIFEST REPAIR: PASS"
)
