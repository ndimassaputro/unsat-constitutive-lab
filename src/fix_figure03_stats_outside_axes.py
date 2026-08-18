from pathlib import Path

TARGET = Path(
    "src/make_figure03_constitutive_lambda.py"
)

text = TARGET.read_text()

MARKER = "# FIG3_STATS_OUTSIDE_AXES"

if MARKER in text:
    print(
        "Figure 03 stats layout already patched."
    )
    raise SystemExit(0)

# ============================================================
# REMOVE STATISTICS TEXT FROM INSIDE PANEL C
# ============================================================

old_stats = r'''ax3.text(
    0.96,
    0.04,
    (
        rf"Tube-paired $\Delta\lambda={delta_mean:+.2f}$"
        "\n"
        rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]"
        "\n"
        rf"$P(\Delta\lambda>0)={prob_positive:.3f}$"
    ),
    transform=ax3.transAxes,
    ha="right",
    va="bottom",
    fontsize=8.0,
)'''

# Fallback for original version.
old_stats_original = r'''ax3.text(
    0.97,
    0.05,
    (
        rf"Tube-paired $\Delta\lambda={delta_mean:+.2f}$"
        "\n"
        rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]"
        "\n"
        rf"$P(\Delta\lambda>0)={prob_positive:.3f}$"
    ),
    transform=ax3.transAxes,
    ha="right",
    va="bottom",
    fontsize=8.2,
)'''

if old_stats in text:

    text = text.replace(
        old_stats,
        "",
        1,
    )

elif old_stats_original in text:

    text = text.replace(
        old_stats_original,
        "",
        1,
    )

else:

    raise SystemExit(
        "PATCH FAIL: panel-C statistics block not found."
    )

# ============================================================
# CREATE REAL TOP MARGIN
#
# Previously the axes occupied almost the entire vertical
# figure, leaving nowhere safe for the panel-C statistics.
# ============================================================

old_layout = '''fig.tight_layout(
    rect=[
        0.0,
        0.06,
        1.0,
        1.0,
    ],
    w_pad=2.3,
)'''

new_layout = r'''fig.tight_layout(
    rect=[
        0.0,
        0.07,
        1.0,
        0.86,
    ],
    w_pad=2.3,
)

# FIG3_STATS_OUTSIDE_AXES
#
# Keep inferential statistics COMPLETELY outside the data
# region. Position dynamically over panel C after tight_layout
# has finalized the axes geometry.

panel_c_box = ax3.get_position()

fig.text(
    (
        panel_c_box.x0
        + panel_c_box.x1
    )
    / 2.0,
    panel_c_box.y1
    + 0.018,
    (
        rf"Tube-paired $\Delta\lambda={delta_mean:+.2f}$"
        "   |   "
        rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]"
        "   |   "
        rf"$P(\Delta\lambda>0)={prob_positive:.3f}$"
    ),
    ha="center",
    va="bottom",
    fontsize=8.2,
)'''

if old_layout not in text:

    raise SystemExit(
        "PATCH FAIL: tight_layout block not found."
    )

text = text.replace(
    old_layout,
    new_layout,
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
    "Panel-C statistics moved outside axes: PASS"
)

print(
    "Top margin reserved                    : PASS"
)
