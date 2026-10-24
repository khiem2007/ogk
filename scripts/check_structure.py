"""Check repository scaffolding only; does not test product behavior."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
required = [
    "server", "dashboard", "agent/core", "agent/windows", "agent/tray",
    "agent/dns", "contracts/schemas", "contracts/fixtures", "tests/unit",
    "tests/integration", "tests/e2e", "tests/manual", "scripts/spikes",
    "deploy", "docs/adr", "docs/reference", "docs/evidence",
]
errors = [f"Missing directory: {name}" for name in required if not (root / name).is_dir()]
for path in root.rglob("*.md"):
    content = path.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", content):
        if "://" in target or target.startswith("#"):
            continue
        target = target.split("#")[0]
        if target and not (path.parent / target).exists():
            errors.append(f"Broken link: {path.relative_to(root)} -> {target}")
photos = list((root / "docs/reference").glob("*.jpg"))
if len(photos) != 9:
    errors.append(f"Expected 9 reference photos, found {len(photos)}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"PASS: {len(required)} required directories, 9 photos and local Markdown links. Scaffolding only.")
