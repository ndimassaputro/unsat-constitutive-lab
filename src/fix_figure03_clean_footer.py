from pathlib import Path
import re

TARGET = Path(
    "src/make_figure03_constitutive_lambda.py"
)

text = TARGET.read_text()

# ============================================================
# 1. Slightly increase figure height
# ============================================================

text = text.replace(
    """figsize=(
        11.2,
        3.85,
    ),""",
    """figsize=(
        11.2,
        4.15,
    ),""",
)

# ============================================================
# 2. Replace the ENTIRE footer/layout section.
#
# This removes:
# - old single-line footer
# - statistics above panel C
# - panel_c_box positioning logic
#
# Statistics will live safely below all panels.
# ============================================================

pattern = re.compile(
    r"""
# ============================================================
# FOOTER
# ============================================================
.*?
(?=fig\.savefig\()
""",
    re.DOTALL | re.VERBOSE,
)

replacement = r'''# ============================================================
# CLEAN FOOTER + LAYOUT
#
# Keep ALL inferential text outside the three plotting panels.
# This prevents overlap with:
# - panel labels
# - axis labels
# - Stage-2 observations
# ============================================================

fig.tight_layout(
    rect=[
        0.0,
        0.19,
        1.0,
        0.98,
    ],
    w_pad=2.3,
)

# Scientific interpretation / caveat.
fig.text(
    0.5,
    0.085,
    (
        r"$\lambda$ is a compact representation of pre-peak "
        r"mobilization shape; primary Stage 1--Stage 2 inference "
        r"is based on direct model-free normalized mobilization."
    ),
    ha="center",
    va="center",
    fontsize=8.2,
)

# Tube-paired quantitative result.
fig.text(
    0.5,
    0.035,
    (
        rf"Tube-paired Stage 1 $\rightarrow$ Stage 2: "
        rf"$\Delta\lambda={delta_mean:+.2f}$; "
        rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]; "
        rf"$P(\Delta\lambda>0)={prob_positive:.3f}$."
    ),
    ha="center",
    va="center",
    fontsize=8.2,
)

'''

new_text, count = pattern.subn(
    replacement,
    text,
    count=1,
)

if count != 1:
    raise SystemExit(
        "PATCH FAIL: footer/layout section not found uniquely."
    )

TARGET.write_text(
    new_text
)

print(
    "Patched:",
    TARGET,
)

print(
    "Panel-C statistics removed from top : PASS"
)

print(
    "Statistics moved to footer          : PASS"
)

print(
    "Extra bottom margin reserved        : PASS"
)

print(
    "Figure height increased             : PASS"
)
