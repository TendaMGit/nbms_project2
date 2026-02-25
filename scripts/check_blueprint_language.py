from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_PATHS = [ROOT / "README.md", ROOT / "docs"]
EXCLUDED_DIRS = {ROOT / "docs" / "external", ROOT / "docs" / "blueprint"}
EXCLUDED_FILES = {ROOT / "docs" / "ops" / "STATE_OF_REPO.md"}

RULES = [
    (re.compile(r"\bDGC\b", re.IGNORECASE), "Use ITSC/Data Steward terms instead of DGC."),
    (re.compile(r"Data Governance Council", re.IGNORECASE), "Use ITSC/Data Steward terms instead."),
    (re.compile(r"\bnear[- ]real[- ]time\b", re.IGNORECASE), "Avoid near-real-time claims for MVP."),
    (re.compile(r"\breal[- ]time\b", re.IGNORECASE), "Avoid real-time claims for MVP."),
    (re.compile(r"\bautomatic(?:ally)?\s+recomput\w*", re.IGNORECASE), "Avoid automatic recompute claims."),
    (re.compile(r"\bauto[- ]?recomput\w*", re.IGNORECASE), "Avoid auto recompute claims."),
    (re.compile(r"\bcompute engine\b", re.IGNORECASE), "Avoid compute-engine framing."),
]


def _is_excluded(path: Path) -> bool:
    if path in EXCLUDED_FILES:
        return True
    for directory in EXCLUDED_DIRS:
        try:
            path.relative_to(directory)
            return True
        except ValueError:
            continue
    return False


def _is_negated(line: str, start_index: int) -> bool:
    prefix = line[:start_index].lower()
    return " not " in f" {prefix[-20:]} "


def _iter_markdown_files():
    for path in SCAN_PATHS:
        if not path.exists():
            continue
        if path.is_file() and path.suffix.lower() == ".md":
            if not _is_excluded(path):
                yield path
            continue
        for file_path in path.rglob("*.md"):
            if not _is_excluded(file_path):
                yield file_path


def main() -> int:
    violations = []
    for file_path in sorted(set(_iter_markdown_files())):
        for line_no, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
            for pattern, message in RULES:
                match = pattern.search(line)
                if not match:
                    continue
                if _is_negated(line, match.start()):
                    continue
                violations.append(
                    (
                        str(file_path.relative_to(ROOT)),
                        line_no,
                        match.group(0),
                        message,
                    )
                )

    if not violations:
        print("Blueprint language check passed.")
        return 0

    print("Blueprint language check failed:")
    for file_path, line_no, token, message in violations:
        print(f"- {file_path}:{line_no}: '{token}' -> {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
