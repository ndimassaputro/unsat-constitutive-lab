from pathlib import Path
import re

p = Path("README.md")
text = p.read_text(encoding="utf-8")

pattern = re.compile(r"\$\$(.*?)\$\$", re.DOTALL)
matches = pattern.findall(text)

print(f"Found display-math blocks: {len(matches)}")

def convert(match):
    body = match.group(1)

    # Collapse multiline LaTeX into one clean inline expression.
    body = " ".join(
        line.strip()
        for line in body.splitlines()
        if line.strip()
    )

    body = re.sub(r"\s+", " ", body).strip()

    # README does not need boxed equations.
    body = body.replace(r"\boxed{", "")
    if body.count("}") > body.count("{"):
        body = body.rstrip("}").rstrip()

    return f"${body}$"

text = pattern.sub(convert, text)

# Hard validation.
if "$$" in text:
    raise SystemExit("FAIL: $$ still remains")

if "```math" in text:
    raise SystemExit("FAIL: math fence remains")

p.write_text(text, encoding="utf-8")

print("PASS: all display-math blocks converted")
print("Remaining $$ count:", text.count("$$"))
