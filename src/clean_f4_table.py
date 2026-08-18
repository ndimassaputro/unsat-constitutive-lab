from pathlib import Path
import csv

SRC = Path("results/tables/repaired/F4_compression_extension.csv")
OUT = Path("data/processed/F4_compression_extension_clean.csv")

OUT.parent.mkdir(parents=True, exist_ok=True)

# Keep ambiguous stress symbols neutral until we verify
# their exact definitions from the source document.
COLUMNS = [
    "soil_type",
    "test_type",
    "ua_minus_uw_kPa",
    "net_confining_kPa",
    "stress_col_1_kPa",
    "stress_col_2_kPa",
    "E_0p1_MPa",
    "E50_MPa",
    "reach_failure",
]

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.reader(f))

cleaned = []
current_soil = ""

for source_row_no, row in enumerate(rows, start=1):
    row = [cell.strip() for cell in row]

    if not row:
        continue

    while len(row) < 10:
        row.append("")

    joined = " ".join(row).lower()

    # Skip title/header/unit rows.
    if (
        "soil type" in joined
        or "test type" in joined
        or "(kpa)" in joined
        or "(mpa)" in joined
    ):
        continue

    # PDF merged cells: soil type is only printed at
    # the beginning of each group.
    if row[0]:
        current_soil = row[0]

    cell = row[1].strip()

    if not cell:
        continue

    # ----------------------------------------------------------
    # CASE A — collapsed AC row
    #
    # Example:
    # AC 27.6 68.9 91.1 191.5 9.7 6.7 Y
    #
    # tokens:
    # 0  AC
    # 1  suction
    # 2  net confining
    # 3  stress column 1
    # 4  stress column 2
    # 5  E0.1
    # 6  E50
    # 7  reach failure
    # ----------------------------------------------------------
    parts = cell.split()

    if parts and parts[0] == "AC":
        if len(parts) != 8:
            raise ValueError(
                f"Unexpected collapsed AC structure at source row "
                f"{source_row_no}: {parts}"
            )

        record = [
            current_soil,
            parts[0],
            parts[1],
            parts[2],
            parts[3],
            parts[4],
            parts[5],
            parts[6],
            parts[7],
        ]

        cleaned.append(record)
        continue

    # ----------------------------------------------------------
    # CASE B — normally extracted AC / LE row
    # ----------------------------------------------------------
    if cell in {"AC", "LE"}:
        record = [
            current_soil,
            cell,
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
        ]

        cleaned.append(record)
        continue

# --------------------------------------------------------------
# STRICT VALIDATION
# --------------------------------------------------------------

errors = []

for i, row in enumerate(cleaned, start=1):
    if len(row) != len(COLUMNS):
        errors.append(
            f"row {i}: expected {len(COLUMNS)} columns, "
            f"got {len(row)}"
        )
        continue

    if row[0] not in {"MH", "SC"}:
        errors.append(
            f"row {i}: unexpected soil_type={row[0]!r}"
        )

    if row[1] not in {"AC", "LE"}:
        errors.append(
            f"row {i}: invalid test_type={row[1]!r}"
        )

    for j in range(2, 8):
        try:
            float(row[j])
        except ValueError:
            errors.append(
                f"row {i}: non-numeric "
                f"{COLUMNS[j]}={row[j]!r}"
            )

    if row[8] not in {"Y", "N"}:
        errors.append(
            f"row {i}: invalid "
            f"reach_failure={row[8]!r}"
        )

n_ac = sum(r[1] == "AC" for r in cleaned)
n_le = sum(r[1] == "LE" for r in cleaned)

# A table containing compression/extension comparison
# cannot legitimately pass with either class missing.
if n_ac == 0:
    errors.append("No axial-compression (AC) tests captured.")

if n_le == 0:
    errors.append("No lateral-extension (LE) tests captured.")

if errors:
    print("VALIDATION ERRORS:")
    for err in errors:
        print(" -", err)

    raise SystemExit(
        "PHASE 1F F4 CLEANING: FAIL"
    )

# --------------------------------------------------------------
# SAVE
# --------------------------------------------------------------

with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(COLUMNS)
    writer.writerows(cleaned)

# --------------------------------------------------------------
# SUMMARY
# --------------------------------------------------------------

n_fail = sum(r[8] == "Y" for r in cleaned)
n_not_fail = sum(r[8] == "N" for r in cleaned)

soil_types = sorted({
    r[0] for r in cleaned
})

print("=" * 68)
print("UnsatConstitutiveLab — F4 Structural Cleaning")
print("=" * 68)
print()
print("Input :", SRC)
print("Output:", OUT)
print()
print("Rows cleaned      :", len(cleaned))
print("AC tests          :", n_ac)
print("LE tests          :", n_le)
print("Reach failure = Y :", n_fail)
print("Reach failure = N :", n_not_fail)
print("Soil types        :", ", ".join(soil_types))

print()
print("=== CLEAN PREVIEW ===")
print(" | ".join(COLUMNS))

for row in cleaned:
    print(" | ".join(row))

print()
print("PHASE 1F F4 CLEANING: PASS")
