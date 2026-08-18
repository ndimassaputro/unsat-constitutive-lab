from pathlib import Path
import re

path = Path("README.md")
text = path.read_text(encoding="utf-8")


def replace_section(text, start, end, new_body):
    if start not in text:
        raise SystemExit(f"FAIL: start marker not found: {start}")
    if end not in text:
        raise SystemExit(f"FAIL: end marker not found: {end}")

    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)

    return before + new_body.rstrip() + "\n\n" + end + after


# ============================================================
# 1. MODEL-FREE PRIMARY RESULT
# ============================================================

text = replace_section(
    text,
    "## Model-free mobilization descriptors",
    "---\n\n## Interpretation",
    r"""## Model-free mobilization descriptors

The primary scientific result does not rely on the fitted $\lambda$
parameter.

Direct normalized mobilization is evaluated at
$x=0.25$, $x=0.50$, and $x=0.75$, producing the descriptors
$y_{25}$, $y_{50}$, and $y_{75}$.

A mean mobilization descriptor, $\bar{y}_{10-90}$, is also evaluated over
$0.10 \le x \le 0.90$.

Using the primary definition of $q_0$:

| Descriptor | Stage-1 → Stage-2 shift | 95% tube-cluster bootstrap CI |
|---|---:|---:|
| $y_{25}$ | **+0.162** | **[+0.115, +0.209]** |
| $y_{50}$ | **+0.171** | **[+0.132, +0.210]** |
| $y_{75}$ | **+0.085** | **[+0.065, +0.105]** |
| $\bar{y}_{10-90}$ | **+0.131** | **[+0.100, +0.161]** |

At $x=0.50$, **92% of paired specimens** show a positive Stage-1 to
Stage-2 shift."""
)


# ============================================================
# 2. SOIL-CLASS RESULT
# ============================================================

text = replace_section(
    text,
    "## Soil-class stratification",
    "---\n\n# Figure 02 — Robustness and soil stratification",
    r"""## Soil-class stratification

The paired shift is independently present in the two major soil subsets.

| Soil class | $\Delta\bar{y}_{10-90}$ | 95% tube-cluster bootstrap CI |
|---|---:|---:|
| **MH** | **+0.160** | **[+0.117, +0.196]** |
| **ML** | **+0.105** | **[+0.071, +0.141]** |

The result is therefore not carried entirely by one major soil class.

SC is not assigned the same inference because the number of independent
SC tubes is insufficient for comparable stratified analysis."""
)


# ============================================================
# 3. LAMBDA INTERPRETATION
# ============================================================

text = replace_section(
    text,
    r"# Constitutive interpretation through $\lambda$",
    "---\n\n# Figure 03 — Constitutive representation",
    r"""# Constitutive interpretation through $\lambda$

The compact parameter $\lambda$ closely tracks the directly observed
normalized mobilization shape.

Across all **84 reconstructed stages**, the Spearman correlation between
$\lambda$ and the model-free mean mobilization descriptor
$\bar{y}_{10-90}$ is **$\rho \approx 0.996$**.

For multistage observations alone, the relationship remains essentially
unchanged: **$\rho \approx 0.996$**.

For tube-paired Stage-1 to Stage-2 comparisons:

- $\Delta\lambda \approx +2.62$
- 95% tube-cluster bootstrap CI: **[+1.66, +3.73]**
- $P(\Delta\lambda>0) \approx 1.000$

The primary scientific inference nevertheless remains anchored to the
**direct model-free mobilization descriptors**, rather than to
$\lambda$ alone."""
)


# ============================================================
# 4. NON-ZERO STAGE-START STRESS
# ============================================================

text = replace_section(
    text,
    "## 3. Non-zero stage-start stress",
    "---\n\n## 4. Uniform strain-axis scaling",
    r"""## 3. Non-zero stage-start stress

Later loading stages do not necessarily begin at zero deviator stress.

The analysis was therefore reformulated using
$\Delta q=q-q_0$ and $\Delta q_p=q_p-q_0$.

The observed mobilization shift remains after this rebaselining.

Therefore, the result is not explained simply by a non-zero stage-start
stress."""
)


# ============================================================
# 5. UNIFORM STRAIN-AXIS SCALING
# ============================================================

text = replace_section(
    text,
    "## 4. Uniform strain-axis scaling",
    "---\n\n## 5. Constitutive-model dependence",
    r"""## 4. Uniform strain-axis scaling

The normalized strain coordinate is
$x=\varepsilon_a/\varepsilon_{a,p}$.

If both numerator and denominator are uniformly scaled by the same factor,
then
$k\varepsilon_a/(k\varepsilon_{a,p})
=\varepsilon_a/\varepsilon_{a,p}$.

Numerical sensitivity testing over **0.5× to 2× strain scaling** changes
the fitted $\lambda$ only at approximately machine precision.

Thus, a uniform template strain-axis scale factor cannot explain the
normalized mobilization shift.

This does **not** imply that every possible form of digitization error has
been eliminated."""
)


# ============================================================
# 6. CONSTITUTIVE-MODEL DEPENDENCE
# ============================================================

text = replace_section(
    text,
    "## 5. Constitutive-model dependence",
    "---\n\n# Candidate scientific contribution",
    r"""## 5. Constitutive-model dependence

The Stage-1 to Stage-2 effect remains after removing the hyperbolic model
entirely.

The direct descriptors $y_{25}$, $y_{50}$, $y_{75}$, and
$\bar{y}_{10-90}$ show the same systematic paired shift.

This is the strongest internal evidence that the effect is present in the
reconstructed laboratory curves themselves, rather than being created by
the one-parameter constitutive representation."""
)


# ============================================================
# 7. STAGE-START SENSITIVITY: REMOVE TINY DISPLAY EQUATIONS
# ============================================================

pattern = re.compile(
    r"""For example,\s*
\$\$\s*
\\Delta y_\{50\}\s*
\$\$\s*
remains approximately:\s*
\$\$\s*
\+0\.166\s*
\\text\{\s*to\s*\}\s*
\+0\.184\.\s*
\$\$""",
    flags=re.VERBOSE | re.DOTALL,
)

text, n = pattern.subn(
    r"For example, $\Delta y_{50}$ remains approximately "
    r"**+0.166 to +0.184**.",
    text,
)

if n != 1:
    print(f"NOTE: stage-start compact replacement count = {n}")


# ============================================================
# 8. CONVERT EVERY REMAINING $$ BLOCK TO CLEAN INLINE LATEX
#
# This removes the source of the mobile GitHub rendering issue
# globally, not only in the sections seen in screenshots.
# ============================================================

display_pattern = re.compile(
    r"\$\$\s*(.*?)\s*\$\$",
    flags=re.DOTALL,
)

converted = 0


def display_to_inline(match):
    global converted
    body = match.group(1)

    parts = [
        line.strip()
        for line in body.splitlines()
        if line.strip()
    ]

    expr = " ".join(parts)
    expr = re.sub(r"\s+", " ", expr).strip()

    # README does not need boxed statistical typography.
    expr = expr.replace(r"\boxed{", "")

    # Remove one unmatched final brace introduced by stripping
    # simple \boxed{...} forms.
    if expr.count("{") < expr.count("}"):
        expr = expr[:-1].rstrip()

    converted += 1
    return f"${expr}$"


text = display_pattern.sub(
    display_to_inline,
    text,
)


# ============================================================
# 9. FINAL NORMALIZATION
# ============================================================

# No old delimiter styles.
text = text.replace(r"\[", "")
text = text.replace(r"\]", "")

# No fenced math blocks.
text = re.sub(
    r"(?ms)^```math\s*\n(.*?)\n```\s*$",
    lambda m: "$" + " ".join(
        x.strip()
        for x in m.group(1).splitlines()
        if x.strip()
    ) + "$",
    text,
)

# Fix excessive blank lines.
text = re.sub(r"\n{4,}", "\n\n\n", text)

path.write_text(
    text.rstrip() + "\n",
    encoding="utf-8",
)


# ============================================================
# 10. HARD VALIDATION
# ============================================================

final = path.read_text(encoding="utf-8")

errors = []

if "$$" in final:
    errors.append("raw $$ remains")

if "```math" in final:
    errors.append("```math remains")

if r"\[" in final or r"\]" in final:
    errors.append("legacy display delimiters remain")

if r"\boxed" in final:
    errors.append(r"\boxed remains")

if errors:
    print("FAIL:")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("PASS: README mobile-safe math cleanup complete")
print(f"Remaining display blocks converted to inline math: {converted}")
print("PASS: raw $$ count = 0")
print("PASS: fenced math count = 0")
print("PASS: boxed math count = 0")
