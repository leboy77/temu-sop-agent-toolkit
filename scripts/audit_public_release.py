#!/usr/bin/env python3
"""Audit the tracked tree for data that should not be published."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


FORBIDDEN_EXTENSIONS = {
    ".downloading",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".webp",
    ".xlsx",
    ".zip",
}

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "assigned_secret": re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)"
        r"\s*[:=]\s*[\"'][^\"']{8,}[\"']"
    ),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "windows_home_path": re.compile(r"(?i)\bC:\\Users\\[^\\\s]+"),
    "china_mobile": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
}


def run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "command failed")
    return result.stdout


def tracked_files() -> list[Path]:
    output = run(["git", "ls-files", "-z"])
    return [Path(item) for item in output.split("\0") if item]


def audit(
    files: list[Path],
    dirty: bool,
    license_present: bool,
) -> dict[str, object]:
    findings: list[dict[str, str]] = []
    warnings: list[str] = []

    required = ["README.md", "CONTRIBUTING.md", "SECURITY.md", "PUBLICATION_CHECKLIST.md"]
    for name in required:
        if not Path(name).exists():
            findings.append({"type": "MISSING_FILE", "path": name})
    if not license_present:
        findings.append({"type": "MISSING_LICENSE", "path": "LICENSE"})
    if dirty:
        warnings.append("Working tree has uncommitted changes; audit the final commit.")

    for path in files:
        suffix = path.suffix.lower()
        if not path.exists():
            findings.append({"type": "TRACKED_FILE_MISSING", "path": str(path)})
            continue
        if suffix in FORBIDDEN_EXTENSIONS:
            findings.append({"type": "FORBIDDEN_BINARY", "path": str(path)})
        if path.parts[:1] == ("records",) and path.name != "README.md":
            findings.append({"type": "PRIVATE_RUNTIME_PATH", "path": str(path)})
        if path.name.startswith(".env") and path.name != ".env.example":
            findings.append({"type": "SECRET_FILE", "path": str(path)})
        if path.stat().st_size > 1_048_576:
            findings.append({"type": "LARGE_FILE", "path": str(path)})

        if suffix in {
            ".md",
            ".json",
            ".csv",
            ".py",
            ".toml",
            ".yaml",
            ".yml",
            ".txt",
        }:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for rule, pattern in SECRET_PATTERNS.items():
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    findings.append(
                        {
                            "type": f"SENSITIVE_PATTERN:{rule}",
                            "path": f"{path}:{line}",
                        }
                    )

    return {
        "tracked_files": len(files),
        "findings": findings,
        "warnings": warnings,
        "status": "PASS" if not findings else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-missing-license", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    license_present = any(Path(name).exists() for name in ("LICENSE", "LICENSE.md", "COPYING"))
    dirty = bool(run(["git", "status", "--porcelain"]).strip())
    report = audit(
        tracked_files(),
        dirty=dirty and not args.allow_dirty,
        license_present=license_present or args.allow_missing_license,
    )

    for finding in report["findings"]:
        print(f"FAIL {finding['type']}: {finding['path']}")
    for warning in report["warnings"]:
        print(f"WARN {warning}")
    print(f"{report['status']}: audited {report['tracked_files']} tracked files")
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
