from pathlib import Path
import re

README = Path("README.md")

text = README.read_text()

title_block = """# UnsatConstitutiveLab

## Laboratory-Calibrated Constitutive Modelling of Unsaturated Soil under Triaxial Stress Paths"""

badges = r"""
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Method](https://img.shields.io/badge/Method-Constitutive%20Modelling-6B7280)](#constitutive-representation-of-pre-peak-response)
[![Domain](https://img.shields.io/badge/Domain-Unsaturated%20Soil%20Mechanics-8B5E3C)](#scientific-motivation)
[![Validation](https://img.shields.io/badge/Validation-Leave--One--Tube--Out-4C78A8)](#unsaturated-strength-modelling)
[![Data](https://img.shields.io/badge/Data-Laboratory%20Triaxial-2F855A)](#experimental-source)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
""".strip()

if title_block not in text:
    raise SystemExit(
        "FAIL: expected README title/subtitle block not found."
    )

# ------------------------------------------------------------
# Remove any badge block previously inserted immediately after
# the subtitle, then install the canonical final badge set.
# ------------------------------------------------------------

badge_line = re.compile(
    r'^\[!\[[^\n]+\]\([^\n]+\)\]\([^\n]+\)\s*$',
    re.MULTILINE,
)

prefix, suffix = text.split(
    title_block,
    1,
)

suffix_lines = suffix.splitlines()

while suffix_lines and not suffix_lines[0].strip():
    suffix_lines.pop(0)

while suffix_lines and (
    suffix_lines[0].lstrip().startswith("[![")
    or suffix_lines[0].lstrip().startswith("![")
):
    suffix_lines.pop(0)

while suffix_lines and not suffix_lines[0].strip():
    suffix_lines.pop(0)

text = (
    prefix
    + title_block
    + "\n\n"
    + badges
    + "\n\n"
    + "\n".join(suffix_lines)
)

# ------------------------------------------------------------
# Add compact License / data provenance section once.
# ------------------------------------------------------------

license_section = r"""
---

# License and data provenance

Original code and documentation in this repository are released under the
**MIT License**. See [`LICENSE`](LICENSE).

The experimental source archive analysed in this project is third-party
research data and is **not relicensed by this repository**.

Primary dataset:

**Tang, C.-T.; Borden, R. H.; Gabr, M. A.**  
Mendeley Data, Version 1.  
DOI: **10.17632/p9tmzckdpt.1**  
Source dataset license: **CC0 1.0 Universal**.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for the attribution
and reuse boundary.
""".strip()

if "# License and data provenance" not in text:
    marker = "\n# Scientific integrity\n"

    if marker in text:
        text = text.replace(
            marker,
            "\n" + license_section + "\n\n" + marker,
            1,
        )
    else:
        text = text.rstrip() + "\n\n" + license_section + "\n"

README.write_text(
    text.rstrip() + "\n"
)

print("README final polish: PASS")
print("Badge count:", text.count("img.shields.io"))
print(
    "License section:",
    "# License and data provenance" in text,
)
