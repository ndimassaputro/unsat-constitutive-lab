from pathlib import Path
import ast
import re

TARGET = Path(
    "src/make_figure03_constitutive_lambda.py"
)

text = TARGET.read_text()

# ============================================================
# 1. REMOVE ANY OLD EXTERNAL "TUBE-PAIRED" FIG.TEXT
#
# Use Python AST so this remains robust even if the previous
# layout patches changed whitespace.
# ============================================================

tree = ast.parse(
    text
)

lines = text.splitlines(
    keepends=True
)

remove_ranges = []

for node in ast.walk(
    tree
):

    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    func = node.func

    is_fig_text = (
        isinstance(
            func,
            ast.Attribute,
        )
        and isinstance(
            func.value,
            ast.Name,
        )
        and func.value.id == "fig"
        and func.attr == "text"
    )

    if not is_fig_text:
        continue

    segment = ast.get_source_segment(
        text,
        node,
    )

    if (
        segment
        and "Tube-paired"
        in segment
    ):

        remove_ranges.append(
            (
                node.lineno - 1,
                node.end_lineno,
            )
        )

# Remove from bottom upward.
for start, end in sorted(
    remove_ranges,
    reverse=True,
):

    del lines[
        start:end
    ]

text = "".join(
    lines
)

# Remove stale helper if left behind by previous patch.
text = text.replace(
    "panel_c_box = ax3.get_position()\n",
    "",
)

text = text.replace(
    "# FIG3_STATS_OUTSIDE_AXES\n",
    "",
)

# ============================================================
# 2. PANEL A LEGEND — SMALLER, STILL INSIDE
# ============================================================

legend_pattern = re.compile(
    r'''ax1\.legend\(
\s*frameon=False,
\s*loc="lower right",
\s*\)'''
)

small_legend = '''ax1.legend(
    frameon=False,
    loc="lower right",
    fontsize=7.2,
    handlelength=1.7,
    handletextpad=0.7,
    labelspacing=0.25,
    borderpad=0.20,
    borderaxespad=0.45,
)'''

text, legend_count = legend_pattern.subn(
    small_legend,
    text,
    count=1,
)

if legend_count != 1:

    raise SystemExit(
        "PATCH FAIL: panel-A legend block not found."
    )

# ============================================================
# 3. PANEL C — TWO-LINE STAT BOX BELOW "(c)"
# ============================================================

panel_c_label = '''ax3.text(
    0.025,
    0.965,
    "(c)",
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontweight="bold",
    fontsize=11,
)'''

panel_c_box = '''ax3.text(
    0.025,
    0.965,
    "(c)",
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontweight="bold",
    fontsize=11,
)

# ------------------------------------------------------------
# Compact two-line inferential summary.
# Positioned directly below "(c)" in the empty upper-left
# region of Panel C.
# ------------------------------------------------------------

ax3.text(
    0.055,
    0.865,
    (
        rf"Tube-paired $\\Delta\\lambda={delta_mean:+.2f}$; "
        rf"95% CI [{delta_lo:+.2f}, {delta_hi:+.2f}]"
        "\\n"
        rf"$P(\\Delta\\lambda>0)={prob_positive:.3f}$"
    ),
    transform=ax3.transAxes,
    ha="left",
    va="top",
    fontsize=7.4,
    linespacing=1.30,
    bbox=dict(
        boxstyle="round,pad=0.35",
        facecolor="white",
        edgecolor="#777777",
        linewidth=0.75,
        alpha=0.94,
    ),
)'''

if (
    "Compact two-line inferential summary."
    not in text
):

    if panel_c_label not in text:

        raise SystemExit(
            "PATCH FAIL: panel-C label block not found."
        )

    text = text.replace(
        panel_c_label,
        panel_c_box,
        1,
    )

# ============================================================
# 4. RESTORE NORMAL FIGURE AREA
#
# No statistics live above Panel C anymore, so we no longer
# need excessive top whitespace.
# ============================================================

layout_pattern = re.compile(
    r'''fig\.tight_layout\(
\s*rect=\[
\s*0\.0,
\s*[0-9.]+,
\s*1\.0,
\s*[0-9.]+,
\s*\],
\s*w_pad=2\.3,
\s*\)'''
)

new_layout = '''fig.tight_layout(
    rect=[
        0.0,
        0.10,
        1.0,
        0.98,
    ],
    w_pad=2.3,
)'''

text, layout_count = layout_pattern.subn(
    new_layout,
    text,
    count=1,
)

if layout_count != 1:

    raise SystemExit(
        "PATCH FAIL: Figure-03 tight_layout block not found."
    )

# ============================================================
# 5. FINAL SANITY CHECK
# ============================================================

if "panel_c_box" in text:

    raise SystemExit(
        "PATCH FAIL: stale panel_c_box variable remains."
    )

if "Compact two-line inferential summary." not in text:

    raise SystemExit(
        "PATCH FAIL: new Panel-C annotation missing."
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
    "Panel A smaller internal legend : PASS"
)

print(
    "Old top statistics removed      : PASS"
)

print(
    "Panel C two-line box added       : PASS"
)

print(
    "Normal top margin restored      : PASS"
)
