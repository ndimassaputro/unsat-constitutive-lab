from pathlib import Path
import re
import sys

README = Path("README.md")

if not README.exists():
    raise SystemExit("FAIL: README.md not found")

text = README.read_text(encoding="utf-8")
original = text

# ============================================================
# GitHub math cleanup
#
# GitHub Markdown:
#   inline math  -> $ ... $
#   display math -> $$ ... $$
#
# The README currently uses:
#   \( ... \)
#   \[ ... \]
#
# which is responsible for the broken rendering seen on GitHub.
# ============================================================

# ------------------------------------------------------------
# 1. Display mathematics
#
# Only convert delimiters that occupy their own line.
# This prevents accidental changes to ordinary escaped text.
# ------------------------------------------------------------

lines = text.splitlines()

converted_lines = []
inside_display_math = False
display_open_count = 0
display_close_count = 0

for line in lines:
    stripped = line.strip()

    if stripped == r"\[":
        if inside_display_math:
            raise SystemExit(
                "FAIL: nested display-math opening delimiter found"
            )
        converted_lines.append("$$")
        inside_display_math = True
        display_open_count += 1
        continue

    if stripped == r"\]":
        if not inside_display_math:
            raise SystemExit(
                "FAIL: display-math closing delimiter without opening"
            )
        converted_lines.append("$$")
        inside_display_math = False
        display_close_count += 1
        continue

    converted_lines.append(line)

if inside_display_math:
    raise SystemExit(
        "FAIL: unclosed display-math block detected"
    )

text = "\n".join(converted_lines) + "\n"

# ------------------------------------------------------------
# 2. Inline mathematics
#
# Convert \( expression \) -> $expression$
#
# Non-greedy matching keeps separate expressions independent.
# ------------------------------------------------------------

inline_pattern = re.compile(
    r"\\\((.+?)\\\)",
    flags=re.DOTALL,
)

inline_matches = inline_pattern.findall(text)
inline_count = len(inline_matches)

text = inline_pattern.sub(
    lambda m: f"${m.group(1)}$",
    text,
)

# ------------------------------------------------------------
# 3. Clean common unnecessary line fragmentation inside
#    simple display equations.
#
# We keep multiline equations where useful, but compact trivial
# expressions so the README resembles Project 3 more closely.
# ------------------------------------------------------------

simple_replacements = {
    """$$
q_p = q_{\\mathrm{source\\ peak}},
$$""":
    """$$
q_p = q_{\\mathrm{source\\ peak}}
$$""",

    """$$
(x,y)=(0,0)
$$""":
    """$$
(x,y) = (0,0)
$$""",

    """$$
(x,y)=(1,1)
$$""":
    """$$
(x,y) = (1,1)
$$""",

    """$$
x=0.25,\\qquad
x=0.50,\\qquad
x=0.75.
$$""":
    """$$
x = 0.25, \\qquad x = 0.50, \\qquad x = 0.75
$$""",

    """$$
y_{25},\\qquad
y_{50},\\qquad
y_{75}.
$$""":
    """$$
y_{25}, \\qquad y_{50}, \\qquad y_{75}
$$""",

    """$$
0.10 \\le x \\le 0.90.
$$""":
    """$$
0.10 \\le x \\le 0.90
$$""",

    """$$
\\Delta q=q-q_0
$$""":
    """$$
\\Delta q = q - q_0
$$""",

    """$$
\\Delta q_p=q_p-q_0.
$$""":
    """$$
\\Delta q_p = q_p - q_0
$$""",

    """$$
P(\\Delta\\lambda>0)
\\approx
1.000.
$$""":
    """$$
P(\\Delta \\lambda > 0) \\approx 1.000
$$""",

    """$$
\\rho
\\approx
0.996
$$""":
    """$$
\\rho \\approx 0.996
$$""",

    """$$
\\bar y_{10-90}.
$$""":
    """$$
\\bar{y}_{10-90}
$$""",
}

for old, new in simple_replacements.items():
    text = text.replace(old, new)

# ------------------------------------------------------------
# 4. Typographic consistency inside math
# ------------------------------------------------------------

text = text.replace(
    r"\Delta\bar y",
    r"\Delta \bar{y}",
)

text = text.replace(
    r"\Delta\lambda",
    r"\Delta \lambda",
)

text = text.replace(
    r"\varepsilon_{a,p}",
    r"\varepsilon_{a,p}",
)

# ------------------------------------------------------------
# 5. Validation
# ------------------------------------------------------------

legacy_display_open = len(
    re.findall(r"(?m)^\s*\\\[\s*$", text)
)

legacy_display_close = len(
    re.findall(r"(?m)^\s*\\\]\s*$", text)
)

legacy_inline_open = text.count(r"\(")
legacy_inline_close = text.count(r"\)")

dollar_display_count = len(
    re.findall(r"(?m)^\s*\$\$\s*$", text)
)

if legacy_display_open:
    raise SystemExit(
        f"FAIL: {legacy_display_open} legacy \\\\[ delimiters remain"
    )

if legacy_display_close:
    raise SystemExit(
        f"FAIL: {legacy_display_close} legacy \\\\] delimiters remain"
    )

if legacy_inline_open or legacy_inline_close:
    raise SystemExit(
        "FAIL: legacy inline math delimiters remain: "
        f"open={legacy_inline_open}, close={legacy_inline_close}"
    )

if dollar_display_count % 2 != 0:
    raise SystemExit(
        "FAIL: unbalanced $$ display-math delimiters"
    )

# ------------------------------------------------------------
# 6. Write
# ------------------------------------------------------------

README.write_text(
    text,
    encoding="utf-8",
)

print("PASS: GitHub math delimiters repaired")
print(
    f"display blocks converted: {display_open_count}"
)
print(
    f"display closes converted: {display_close_count}"
)
print(
    f"inline expressions converted: {inline_count}"
)
print(
    f"final $$ delimiter count: {dollar_display_count}"
)

if text == original:
    print("NOTE: README was already clean")
