"""Check repository scaffolding only; does not test product behavior."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
required = [
    "server", "dashboard", "agent/core", "agent/windows", "agent/tray",
    "agent/spikes", "agent/tests", "server/tests", "contracts/schemas",
    "contracts/fixtures", "dashboard/e2e",
    "deploy", "docs/adr", "docs/reference", "docs/evidence",
]
errors = [f"Missing directory: {name}" for name in required if not (root / name).is_dir()]
required_files = [
    "docs/DoAn_UD_QL_SD_PC_TreEm.pdf",
    "docs/REQUIREMENTS_TRACEABILITY.md",
    "docs/PRIVACY.md",
    "docs/THREATMODEL.md",
    "docs/AI_USAGE.md",
    "docs/BaoCaoKyThuatMang.md",
]
errors.extend(
    f"Missing required project document: {name}"
    for name in required_files
    if not (root / name).is_file()
)
ignored_roots = {".git", ".venv", "venv", "node_modules", "runtime", "tmp"}
for path in root.rglob("*.md"):
    relative = path.relative_to(root)
    if relative.parts and relative.parts[0] in ignored_roots:
        continue
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
print(
    f"PASS: {len(required)} required directories, {len(required_files)} required "
    "documents, 9 photos and local Markdown links. Scaffolding only."
)
