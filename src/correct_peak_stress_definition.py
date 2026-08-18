from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(
    "data/processed/strength_analysis_ready.csv"
)

OUT = Path(
    "data/processed/strength_analysis_ready.csv"
)

AUDIT = Path(
    "results/tables/peak_stress_definition_correction.csv"
)

NOTE = Path(
    "docs/peak_stress_definition_correction.md"
)

AUDIT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

NOTE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df = pd.read_csv(SRC)

required = [
    "specimen_id",
    "sigma_c_net_kPa",
    "sigma_a_peak_kPa",
    "q_peak_kPa",
]

missing = [
    col for col in required
    if col not in df.columns
]

if missing:
    raise SystemExit(
        f"Missing columns: {missing}"
    )

old_q = df["q_peak_kPa"].copy()

# ============================================================
# CORRECT INTERPRETATION
#
# Appendix-F stress-strain figures plot:
#
#     Deviatoric stress (kPa)
#
# The plotted peak for ST-36 at suction = 152 kPa is
# approximately 265 kPa, matching the Table F-1 value
# 264.5 kPa.
#
# Therefore the extracted table peak-stress column is already
# the measured peak deviatoric stress q_f.
#
# It must NOT have net confining stress subtracted again.
# ============================================================

df["deviator_stress_peak_kPa"] = (
    df["sigma_a_peak_kPa"]
)

df["q_peak_kPa"] = (
    df["deviator_stress_peak_kPa"]
)

df["peak_stress_definition"] = (
    "measured peak deviatoric stress from Appendix F"
)

# ------------------------------------------------------------
# Source-level verification using ST-36
# ------------------------------------------------------------

st36 = df[
    df["specimen_id"] == "ST-36"
]

if len(st36) != 1:
    raise SystemExit(
        f"Expected exactly one ST-36 row, found {len(st36)}"
    )

row = st36.iloc[0]

source_peak = float(
    row["sigma_a_peak_kPa"]
)

sigma_c = float(
    row["sigma_c_net_kPa"]
)

old_value = float(
    old_q.loc[st36.index[0]]
)

corrected = float(
    row["q_peak_kPa"]
)

if not np.isclose(
    source_peak,
    264.5,
    atol=0.2,
):
    raise SystemExit(
        "ST-36 source peak is not the expected 264.5 kPa."
    )

if not np.isclose(
    old_value,
    source_peak - sigma_c,
    atol=0.2,
):
    raise SystemExit(
        "Old q definition does not match the identified "
        "double-subtraction error."
    )

if not np.isclose(
    corrected,
    source_peak,
    atol=1e-9,
):
    raise SystemExit(
        "Corrected q does not equal source peak stress."
    )

if (df["q_peak_kPa"] <= 0).any():
    raise SystemExit(
        "Non-positive corrected peak deviator stress found."
    )

# ------------------------------------------------------------
# Audit table
# ------------------------------------------------------------

audit = pd.DataFrame({
    "specimen_id":
        df["specimen_id"],

    "stage":
        df["stage"],

    "sigma_c_net_kPa":
        df["sigma_c_net_kPa"],

    "source_peak_stress_kPa":
        df["sigma_a_peak_kPa"],

    "previous_incorrect_q_kPa":
        old_q,

    "corrected_q_peak_kPa":
        df["q_peak_kPa"],

    "correction_kPa":
        df["q_peak_kPa"] - old_q,
})

audit.to_csv(
    AUDIT,
    index=False,
)

df.to_csv(
    OUT,
    index=False,
)

NOTE.write_text(
    """# Peak-stress definition correction

## Issue

The first strength-analysis pass interpreted the Appendix-F peak-stress
column as total axial stress and calculated

`q_peak = sigma_a_peak - sigma_c_net`.

This double-subtracted the confining stress.

## Source-level verification

The Appendix-F stress-strain plot for ST-36 is explicitly labelled
`Deviatoric stress (kPa)` and reaches a peak of approximately 265 kPa.

Table F-1 reports 264.5 kPa for the corresponding ST-36 test
(matric suction = 152 kPa).

The table peak-stress value therefore corresponds directly to the
measured peak deviatoric stress used in the stress-strain figure.

## Correct definition

`q_peak_kPa = source peak-stress value`

No additional subtraction of net confining stress is applied.

## Consequence

All Phase-3 model fits and validation results obtained with the previous
derived q definition are superseded and must be recomputed.

The superseded files are retained for provenance rather than deleted.
""",
    encoding="utf-8",
)

print("=" * 76)
print(
    "UnsatConstitutiveLab — Peak Stress Definition Correction"
)
print("=" * 76)

print()
print("=== ST-36 SOURCE CHECK ===")
print(
    "Net confining stress       :",
    f"{sigma_c:.1f} kPa",
)
print(
    "Table/source peak stress   :",
    f"{source_peak:.1f} kPa",
)
print(
    "Previous incorrect q       :",
    f"{old_value:.1f} kPa",
)
print(
    "Corrected deviator q_peak  :",
    f"{corrected:.1f} kPa",
)

print()
print("=== DATASET ===")
print("Rows:", len(df))
print(
    "Corrected q range:",
    f"{df['q_peak_kPa'].min():.1f}",
    "to",
    f"{df['q_peak_kPa'].max():.1f}",
    "kPa",
)

print()
print("Audit:", AUDIT)
print("Note :", NOTE)

print()
print(
    "PEAK STRESS DEFINITION CORRECTION: PASS"
)
