from pathlib import Path
import csv
import re
import pandas as pd

BASE = Path("results/tables/repaired")
OUT = Path("data/processed/strength_master.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

SOURCES = [
    ("F1_single_stage.csv", "F1", "single_stage"),
    ("F2_multistage_slope.csv", "F2", "multistage"),
    ("F3_multistage_sheet_pile.csv", "F3", "multistage"),
]

MASTER_COLUMNS = [
    "source_table",
    "test_family",
    "area",
    "soil_type",
    "specimen_id",
    "depth_m",
    "stage",
    "sigma_c_net_kPa",
    "matric_suction_kPa",
    "sigma_a_peak_kPa",
    "gamma_d_g_cm3",
    "degree_saturation",
    "qc_specimen_id_outside_program_range",
]

records = []

for filename, source_table, family in SOURCES:
    path = BASE / filename

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    current_area = ""
    current_soil = ""
    current_specimen = ""
    current_depth = ""

    for row_no, row in enumerate(rows, start=1):
        row = [str(x).strip() for x in row]

        # Skip header/unit rows.
        joined = " ".join(row).lower()

        if (
            not row
            or "soil type" in joined
            or "depth" in joined
            or "kpa" in joined
            or "stage" in joined and "#" in joined
        ):
            continue

        expected_cols = 9 if source_table == "F1" else 10

        if len(row) < expected_cols:
            row += [""] * (expected_cols - len(row))

        if source_table == "F1":
            (
                area,
                soil,
                specimen,
                depth,
                sigma_c,
                suction,
                sigma_a_peak,
                gamma_d,
                saturation,
            ) = row[:9]

            stage = "single"

        else:
            (
                area,
                soil,
                specimen,
                depth,
                stage,
                sigma_c,
                suction,
                sigma_a_peak,
                gamma_d,
                saturation,
            ) = row[:10]

        # Forward-fill merged PDF cells.
        if area:
            current_area = area

        if soil:
            current_soil = soil

        if specimen:
            current_specimen = specimen

        if depth:
            current_depth = depth

        # A valid experimental row must have the three main
        # numerical stress-state variables.
        try:
            sigma_c_f = float(sigma_c)
            suction_f = float(suction)
            sigma_a_f = float(sigma_a_peak)
            gamma_d_f = float(gamma_d)
            saturation_f = float(saturation)
        except ValueError:
            continue

        if not current_specimen:
            raise ValueError(
                f"{source_table} row {row_no}: "
                "numeric row has no specimen ID"
            )

        # Preserve suspicious IDs; flag rather than silently fixing.
        match = re.fullmatch(r"ST-(\d+)([A-Za-z]?)", current_specimen)

        outside_range = False

        if match:
            number = int(match.group(1))
            if number > 94:
                outside_range = True

        records.append({
            "source_table": source_table,
            "test_family": family,
            "area": current_area,
            "soil_type": current_soil,
            "specimen_id": current_specimen,
            "depth_m": current_depth,
            "stage": stage,
            "sigma_c_net_kPa": sigma_c_f,
            "matric_suction_kPa": suction_f,
            "sigma_a_peak_kPa": sigma_a_f,
            "gamma_d_g_cm3": gamma_d_f,
            "degree_saturation": saturation_f,
            "qc_specimen_id_outside_program_range": outside_range,
        })

df = pd.DataFrame(records, columns=MASTER_COLUMNS)

if df.empty:
    raise SystemExit("No experimental records parsed.")

# ------------------------------------------------------------
# BASIC QC
# ------------------------------------------------------------

errors = []

for col in [
    "sigma_c_net_kPa",
    "matric_suction_kPa",
    "sigma_a_peak_kPa",
    "gamma_d_g_cm3",
    "degree_saturation",
]:
    if df[col].isna().any():
        errors.append(f"{col}: contains missing values")

if ((df["degree_saturation"] < 0) |
    (df["degree_saturation"] > 1)).any():
    errors.append("degree_saturation outside [0, 1]")

if (df["sigma_c_net_kPa"] < 0).any():
    errors.append("negative net confining stress found")

if (df["matric_suction_kPa"] < 0).any():
    errors.append("negative matric suction found")

if errors:
    print("QC ERRORS:")
    for err in errors:
        print(" -", err)
    raise SystemExit("PHASE 2B STRENGTH MASTER: FAIL")

df.to_csv(OUT, index=False)

print("=" * 72)
print("UnsatConstitutiveLab — Strength Master Dataset")
print("=" * 72)

print()
print("Output:", OUT)
print("Rows:", len(df))
print("Unique specimen IDs:", df["specimen_id"].nunique())

print()
print("=== BY SOURCE TABLE ===")
print(df.groupby("source_table").size().to_string())

print()
print("=== UNIQUE SPECIMENS BY SOURCE ===")
print(
    df.groupby("source_table")["specimen_id"]
      .nunique()
      .to_string()
)

print()
print("=== SOIL TYPES ===")
print(
    df.groupby(["source_table", "soil_type"])
      .size()
      .to_string()
)

print()
print("=== STAGES ===")
print(
    df.groupby(["source_table", "stage"])
      .size()
      .to_string()
)

print()
print("=== NUMERICAL RANGE CHECK ===")
print(
    df[
        [
            "sigma_c_net_kPa",
            "matric_suction_kPa",
            "sigma_a_peak_kPa",
            "gamma_d_g_cm3",
            "degree_saturation",
        ]
    ]
    .agg(["min", "max"])
    .to_string()
)

print()
print("=== QC FLAGS ===")

flagged = df[
    df["qc_specimen_id_outside_program_range"]
]

if flagged.empty:
    print("No specimen-ID range flags.")
else:
    print(
        flagged[
            [
                "source_table",
                "specimen_id",
                "depth_m",
            ]
        ]
        .drop_duplicates()
        .to_string(index=False)
    )

print()
print("=== FIRST 12 RECORDS ===")
print(df.head(12).to_string(index=False))

print()
print("PHASE 2B STRENGTH MASTER: PASS")
