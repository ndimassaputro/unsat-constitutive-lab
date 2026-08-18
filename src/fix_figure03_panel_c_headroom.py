from pathlib import Path

TARGET = Path(
    "src/make_figure03_constitutive_lambda.py"
)

text = TARGET.read_text()

old = '''ax3.set_xlim(
    -0.35,
    1.35,
)

ax3.set_xticks(
    [
        0,
        1,
    ]
)'''

new = '''ax3.set_xlim(
    -0.35,
    1.35,
)

# ============================================================
# PANEL-C VERTICAL HEADROOM
#
# Give the largest Stage-1/Stage-2 lambda values explicit
# breathing room so markers and connecting lines never touch
# or get visually clipped by the upper frame.
# ============================================================

lambda_all = np.concatenate(
    [
        tube_paired[
            "lambda_stage1"
        ].to_numpy(float),

        tube_paired[
            "lambda_stage2"
        ].to_numpy(float),
    ]
)

lambda_min = float(
    np.min(
        lambda_all
    )
)

lambda_max = float(
    np.max(
        lambda_all
    )
)

lambda_span = max(
    lambda_max
    - lambda_min,
    1.0,
)

ax3.set_ylim(
    max(
        0.0,
        lambda_min
        - 0.08
        * lambda_span,
    ),
    lambda_max
    + 0.14
    * lambda_span,
)

ax3.set_xticks(
    [
        0,
        1,
    ]
)'''

if old not in text:
    raise SystemExit(
        "PATCH FAIL: panel-C axis block not found."
    )

text = text.replace(
    old,
    new,
    1,
)

# Move the statistics box slightly further from Stage-2 data.
old_annotation = '''ax3.text(
    0.97,
    0.05,
    (
        rf"Tube-paired $\\\\Delta\\\\lambda={delta_mean:+.2f}$"
        "\\n"
        rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]"
        "\\n"
        rf"$P(\\\\Delta\\\\lambda>0)={prob_positive:.3f}$"
    ),
    transform=ax3.transAxes,
    ha="right",
    va="bottom",
    fontsize=8.2,
)'''

new_annotation = '''ax3.text(
    0.96,
    0.04,
    (
        rf"Tube-paired $\\\\Delta\\\\lambda={delta_mean:+.2f}$"
        "\\n"
        rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]"
        "\\n"
        rf"$P(\\\\Delta\\\\lambda>0)={prob_positive:.3f}$"
    ),
    transform=ax3.transAxes,
    ha="right",
    va="bottom",
    fontsize=8.0,
)'''

if old_annotation in text:
    text = text.replace(
        old_annotation,
        new_annotation,
        1,
    )

TARGET.write_text(
    text
)

print(
    "Patched:",
    TARGET,
)

print(
    "Panel C automatic Y headroom: PASS"
)
