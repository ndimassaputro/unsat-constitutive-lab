from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path("assets/social-preview.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

# GitHub-recommended social preview aspect ratio: 2:1
fig = plt.figure(figsize=(12.8, 6.4), dpi=100)
fig.patch.set_facecolor("#0B1320")

# ------------------------------------------------------------
# Background
# ------------------------------------------------------------
ax_bg = fig.add_axes([0, 0, 1, 1])
ax_bg.set_xlim(0, 1)
ax_bg.set_ylim(0, 1)
ax_bg.axis("off")

# Subtle panels
ax_bg.add_patch(
    FancyBboxPatch(
        (0.055, 0.09),
        0.89,
        0.82,
        boxstyle="round,pad=0.012,rounding_size=0.025",
        linewidth=1.2,
        edgecolor="#30445E",
        facecolor="#101C2C",
    )
)

# Accent rule
ax_bg.plot(
    [0.085, 0.46],
    [0.79, 0.79],
    lw=4,
    color="#4FA3D1",
    solid_capstyle="round",
)

# ------------------------------------------------------------
# Left text block
# ------------------------------------------------------------
ax_bg.text(
    0.085,
    0.84,
    "UNSATCONSTITUTIVELAB",
    fontsize=13,
    fontweight="bold",
    color="#8FB9D4",
    ha="left",
    va="center",
)

ax_bg.text(
    0.085,
    0.71,
    "Laboratory-Calibrated\nConstitutive Modelling",
    fontsize=29,
    fontweight="bold",
    color="#F4F7FA",
    ha="left",
    va="center",
    linespacing=1.12,
)

ax_bg.text(
    0.085,
    0.545,
    "Unsaturated residual soil • triaxial stress paths",
    fontsize=13.5,
    color="#B9C7D5",
    ha="left",
    va="center",
)

# Finding card
ax_bg.add_patch(
    FancyBboxPatch(
        (0.085, 0.245),
        0.39,
        0.215,
        boxstyle="round,pad=0.015,rounding_size=0.018",
        linewidth=1.0,
        edgecolor="#38536D",
        facecolor="#14263A",
    )
)

ax_bg.text(
    0.105,
    0.415,
    "PRIMARY FINDING",
    fontsize=10.5,
    fontweight="bold",
    color="#79B8DD",
    ha="left",
    va="center",
)

ax_bg.text(
    0.105,
    0.35,
    "Stage 2 exhibits earlier normalized\npre-peak stress mobilization than Stage 1",
    fontsize=13.5,
    fontweight="bold",
    color="#F2F5F7",
    ha="left",
    va="center",
    linespacing=1.25,
)

ax_bg.text(
    0.105,
    0.275,
    "25 paired specimens  •  18 independent tubes",
    fontsize=10.5,
    color="#A9BAC9",
    ha="left",
    va="center",
)

ax_bg.text(
    0.085,
    0.145,
    "Nurwahid Dimas Saputro  •  Computational Geomechanics",
    fontsize=10.8,
    color="#889BAD",
    ha="left",
    va="center",
)

# ------------------------------------------------------------
# Right scientific graphic
# ------------------------------------------------------------
ax = fig.add_axes([0.57, 0.19, 0.32, 0.57])
ax.set_facecolor("#101C2C")

x = np.linspace(0, 1, 300)

def mobilization(x, lam):
    return x * (1 + lam) / (1 + lam * x)

lam_stage1 = 0.74
lam_stage2 = 2.20

y1 = mobilization(x, lam_stage1)
y2 = mobilization(x, lam_stage2)

ax.plot(x, y1, lw=3.0, color="#65A9D7", label="Stage 1")
ax.plot(x, y2, lw=3.0, color="#E99A5B", label="Stage 2")

ax.fill_between(
    x,
    y1,
    y2,
    where=(y2 >= y1),
    alpha=0.11,
    color="#E99A5B",
)

ax.scatter(
    [0.5, 0.5],
    [
        mobilization(np.array([0.5]), lam_stage1)[0],
        mobilization(np.array([0.5]), lam_stage2)[0],
    ],
    s=45,
    color=["#65A9D7", "#E99A5B"],
    zorder=5,
)

ax.set_xlim(0, 1)
ax.set_ylim(0, 1.04)
ax.set_xlabel(
    r"Normalized axial strain  $\varepsilon/\varepsilon_p$",
    fontsize=10.5,
    color="#D3DCE5",
)
ax.set_ylabel(
    r"Normalized stress mobilization  $y$",
    fontsize=10.5,
    color="#D3DCE5",
)

ax.tick_params(colors="#9EB0BF", labelsize=9)

for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_color("#53697C")
    spine.set_linewidth(1.0)

ax.grid(alpha=0.12, color="#DCE6EE")

leg = ax.legend(
    loc="lower right",
    frameon=True,
    fontsize=9.5,
)
leg.get_frame().set_facecolor("#14263A")
leg.get_frame().set_edgecolor("#53697C")
for txt in leg.get_texts():
    txt.set_color("#E7EDF2")

ax.text(
    0.03,
    0.96,
    "Normalized pre-peak response",
    transform=ax.transAxes,
    ha="left",
    va="top",
    fontsize=11,
    fontweight="bold",
    color="#E8EEF3",
)

# Metrics bottom-right
ax_bg.text(
    0.57,
    0.115,
    "84 reconstructed stages   •   median pre-peak NRMSE 3.2%",
    fontsize=10.3,
    color="#9FB1C0",
    ha="left",
    va="center",
)

fig.savefig(
    OUT,
    dpi=100,
    facecolor=fig.get_facecolor(),
)
plt.close(fig)

print(f"PASS: wrote {OUT}")
print("Expected dimensions: 1280 x 640 px")
