from pathlib import Path

path = Path("README.md")
text = path.read_text()

license_badge = (
    "[![License: MIT]"
    "(https://img.shields.io/badge/License-MIT-yellow.svg)]"
    "(LICENSE)"
)

release_badge = (
    "[![Release]"
    "(https://img.shields.io/badge/release-v1.0.0-2F855A)]"
    "(https://github.com/ndimassaputro/"
    "unsat-constitutive-lab/releases/tag/v1.0.0)"
)

if release_badge in text:
    print("PASS: release badge already present")

elif license_badge in text:
    text = text.replace(
        license_badge,
        release_badge + "\n" + license_badge,
        1,
    )
    path.write_text(text)
    print("PASS: release badge inserted")

else:
    raise SystemExit(
        "FAIL: canonical MIT license badge not found in README"
    )
