from pathlib import Path
import re

TARGET = Path(
    "src/make_figure03_constitutive_lambda.py"
)

text = TARGET.read_text()

# ============================================================
# 1. GIVE PANEL C MORE EMPTY HEADROOM
#
# Highest Stage-2 lambda is around the upper data region.
# Reserve ~35% of the observed lambda span above the maximum
# so the statistical box has its own dedicated space.
# ============================================================

old_ylim = '''ax3.set_ylim(
    max(
        0.0,
        lambda_min
        - 0.08
        * lambda_span,
    ),
    lambda_max
    + 0.14
    * lambda_span,
)'''

new_ylim = '''ax3.set_ylim(
    0.0,
    lambda_max
    + 0.35
    * lambda_span,
)'''

if old_ylim not in text:
    raise SystemExit(
        "PATCH FAIL: panel-C ylim block not found."
    )

text = text.replace(
    old_ylim,
    new_ylim,
    1,
)

# ============================================================
# 2. MOVE THE TWO-LINE BOX INTO RESERVED UPPER SPACE
#
# Keep it below "(c)", but above the highest observations.
# Slightly smaller font makes it compact.
# ============================================================

box_pattern = re.compile(
    r'''ax3\.text\(
\s*0\.055,
\s*0\.865,
\s*\(
.*?
\s*\),
\s*transform=ax3\.transAxes,
\s*ha="left",
\s*va="top",
\s*fontsize=7\.4,
\s*linespacing=1\.30,
\s*bbox=dict\(
.*?
\s*\),
\s*\)''',
    re.DOTALL,
)

new_box = r'''ax3.text(
    0.055,
    0.885,
    (
        rf"$\Delta\lambda={delta_mean:+.2f}$; "
        rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]"
        "\n"
        rf"Tube-paired: $P(\Delta\lambda>0)={prob_positive:.3f}$"
    ),
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontsize=6.9,
    linespacing=1.22,
    bbox=dict(
        boxstyle="round,pad=0.32",
        facecolor="white",
        edgecolor="#777777",
        linewidth=0.70,
        alpha=0.96,
    ),
)'''

text, count = box_pattern.subn(
    new_box,
    text,
    count=1,
)

if count != 1:
    raise SystemExit(
        "PATCH FAIL: panel-C statistics box not found."
    )

TARGET.write_text(
    text
)

print(
    "Patched:",
    TARGET,
)

print()
print(
    "Extra Panel-C headroom : PASS"
)

print(
    "Statistics box raised  : PASS"
)

print(
    "Statistics box compact : PASS"
)
