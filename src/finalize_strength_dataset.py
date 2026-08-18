from pathlib import Path
import hashlib
import re

import pandas as pd

SRC = Path("data/processed/strength_master.csv")
OUT = Path("data/processed/strength_analysis_ready.csv")
SUMMARY = Path("results/tables/strength_analysis_summary.csv")

OUT.parent.mkdir(parents=True, exist_ok=True)
SUMMARY.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SRC)

# ------------------------------------------------------------
# 1. PROVENANCE / ID QC
# ------------------------------------------------------------

SOURCE_CONFIRMED_RANGE_EXCEPTIONS = {
    "ST-124",
    "ST-114B",
    "ST-116E",
}

df["qc_id_note"] = ""

mask_exception = df["specimen_id"].isin(
    SOURCE_CONFIRMED_RANGE_EXCEPTIONS
)

df.loc[
    mask_exception,
    "qc_id_note"
] = (
    "source-confirmed in Appendix F; "
    "outside initial tube-range summary"
)

# Preserve original source value. Do not silently rename.
df["qc_source_confirmed"] = True

# ------------------------------------------------------------
# 2. TUBE-LEVEL GROUP ID
#
# ST-37A and ST-37B originate from the same numbered tube.
# Group by tube number to reduce train/holdout leakage.
# ------------------------------------------------------------

def tube_id(specimen_id):
    match = re.fullmatch(r"(ST-\d+)[A-Za-z]*", specimen_id)

    if match:
        return match.group(1)

    return specimen_id

df["tube_id"] = df["specimen_id"].map(tube_id)

# ------------------------------------------------------------
# 3. DERIVED PEAK DEVIATOR STRESS
#
# q_peak = sigma_a,peak - sigma_c,net
#
# Keep original columns intact.
# ------------------------------------------------------------

df["q_peak_kPa"] = (
    df["sigma_a_peak_kPa"]
    - df["sigma_c_net_kPa"]
)

if (df["q_peak_kPa"] <= 0).any():
    bad = df.loc[
        df["q_peak_kPa"] <= 0,
        [
            "source_table",
            "specimen_id",
            "stage",
            "sigma_c_net_kPa",
            "sigma_a_peak_kPa",
            "q_peak_kPa",
        ],
    ]

    print("INVALID q_peak ROWS:")
    print(bad.to_string(index=False))

    raise SystemExit(
        "PHASE 2C ANALYSIS DATASET: FAIL"
    )

# ------------------------------------------------------------
# 4. CONSERVATIVE TUBE-LEVEL HOLDOUT PROPOSAL
#
# Deterministic, stratified approximately by soil type.
# This is a proposal, not yet the final scientific split.
#
# All rows from the same tube remain together.
# ------------------------------------------------------------

tube_meta = (
    df[
        [
            "tube_id",
            "soil_type",
        ]
    ]
    .drop_duplicates()
)

# Verify one soil type per tube.
soil_counts = (
    tube_meta.groupby("tube_id")["soil_type"]
    .nunique()
)

if (soil_counts > 1).any():
    problematic = soil_counts[
        soil_counts > 1
    ]

    print("TUBES WITH MULTIPLE SOIL TYPES:")
    print(problematic)

    raise SystemExit(
        "PHASE 2C ANALYSIS DATASET: FAIL"
    )

tube_meta = (
    tube_meta
    .drop_duplicates("tube_id")
    .copy()
)

tube_meta["hash"] = tube_meta["tube_id"].map(
    lambda x: int(
        hashlib.sha256(
            x.encode("utf-8")
        ).hexdigest()[:12],
        16,
    )
)

tube_meta["proposed_split"] = "calibration"

for soil_type, group in tube_meta.groupby("soil_type"):
    group = group.sort_values("hash")

    n = len(group)

    # About 25% holdout, minimum 1 tube if possible.
    n_holdout = max(
        1,
        round(0.25 * n),
    )

    # Keep at least 2 calibration tubes when possible.
    if n >= 3:
        n_holdout = min(
            n_holdout,
            n - 2,
        )
    else:
        n_holdout = 0

    holdout_ids = (
        group.tail(n_holdout)["tube_id"]
        .tolist()
        if n_holdout > 0
        else []
    )

    tube_meta.loc[
        tube_meta["tube_id"].isin(holdout_ids),
        "proposed_split"
    ] = "holdout"

split_map = dict(
    zip(
        tube_meta["tube_id"],
        tube_meta["proposed_split"],
    )
)

df["proposed_split"] = df["tube_id"].map(
    split_map
)

# ------------------------------------------------------------
# 5. SAVE
# ------------------------------------------------------------

df.to_csv(
    OUT,
    index=False,
)

summary = (
    df.groupby(
        [
            "soil_type",
            "test_family",
            "proposed_split",
        ]
    )
    .agg(
        rows=("specimen_id", "size"),
        specimens=("specimen_id", "nunique"),
        tubes=("tube_id", "nunique"),
        suction_min_kPa=("matric_suction_kPa", "min"),
        suction_max_kPa=("matric_suction_kPa", "max"),
        q_peak_min_kPa=("q_peak_kPa", "min"),
        q_peak_max_kPa=("q_peak_kPa", "max"),
    )
    .reset_index()
)

summary.to_csv(
    SUMMARY,
    index=False,
)

# ------------------------------------------------------------
# 6. REPORT
# ------------------------------------------------------------

print("=" * 74)
print("UnsatConstitutiveLab — Analysis-Ready Strength Dataset")
print("=" * 74)

print()
print("Input :", SRC)
print("Output:", OUT)
print()

print("Rows             :", len(df))
print(
    "Unique specimens :",
    df["specimen_id"].nunique(),
)
print(
    "Unique tubes     :",
    df["tube_id"].nunique(),
)

print()
print("=== SOURCE-CONFIRMED ID EXCEPTIONS ===")

exceptions = (
    df.loc[
        mask_exception,
        [
            "specimen_id",
            "tube_id",
            "source_table",
            "qc_id_note",
        ],
    ]
    .drop_duplicates()
)

print(
    exceptions.to_string(index=False)
    if not exceptions.empty
    else "None"
)

print()
print("=== q_peak RANGE ===")

print(
    df["q_peak_kPa"]
    .agg(["min", "median", "max"])
    .to_string()
)

print()
print("=== TUBE COUNTS BY SOIL TYPE ===")

print(
    tube_meta.groupby(
        [
            "soil_type",
            "proposed_split",
        ]
    )
    .size()
    .to_string()
)

print()
print("=== ROW COUNTS BY SPLIT ===")

print(
    df.groupby(
        [
            "soil_type",
            "proposed_split",
        ]
    )
    .size()
    .to_string()
)

print()
print("=== HOLDOUT TUBES ===")

holdout = (
    tube_meta[
        tube_meta["proposed_split"]
        == "holdout"
    ]
    .sort_values(
        [
            "soil_type",
            "tube_id",
        ]
    )
)

print(
    holdout[
        [
            "soil_type",
            "tube_id",
        ]
    ].to_string(index=False)
)

print()
print("=== SUMMARY ===")
print(summary.to_string(index=False))

print()
print(
    "PHASE 2C ANALYSIS-READY DATASET: PASS"
)
