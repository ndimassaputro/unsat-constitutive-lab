from pathlib import Path
import re

TARGET = Path(
    "src/make_figure03_constitutive_lambda.py"
)

text = TARGET.read_text()

# ============================================================
# Replace current boxed Panel-C annotation with a compact
# three-line plain-text annotation.
# ============================================================

pattern = re.compile(
    r'''# ------------------------------------------------------------
# Compact two-line inferential summary\.
.*?
ax3\.text\(
.*?
\)
''',
    re.DOTALL,
)

replacement = r'''# ------------------------------------------------------------
# Compact three-line inferential summary.
# Plain text only: no box, no background.
# ------------------------------------------------------------

ax3.text(
    0.055,
    0.885,
    (
        rf"Tube-paired $\Delta\lambda={delta_mean:+.2f}$"
        "\n"
        rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]"
        "\n"
        rf"$P(\Delta\lambda>0)={prob_positive:.3f}$"
    ),
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontsize=6.4,
    linespacing=1.18,
)
'''

text, count = pattern.subn(
    replacement,
    text,
    count=1,
)

if count != 1:
    raise SystemExit(
        "PATCH FAIL: current Panel-C annotation block not found."
    )

TARGET.write_text(
    text
)

print(
    "Patched:",
    TARGET,
)

print(
    "Panel C annotation = 3 lines : PASS"
)

print(
    "Annotation box removed       : PASS"
)

print(
    "Font reduced to 6.4 pt       : PASS"
)
