"""Create or verify the reproducible CurricuPath Open Day release manifest."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
RELEASE_DIRECTORY = PROJECT_ROOT / "experiments" / "release"
MANIFEST_PATH = RELEASE_DIRECTORY / "open_day_rc1_manifest.json"
RELEASE_VERSION = "open-day-rc1-2026-09-22"

from app.config import get_settings
from app.data.database import create_database_engine, database_status
from app.data.recommendation_log import catalogue_version
from app.release import build_release_inputs, changed_release_sections, sha256_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the committed manifest without modifying it.",
    )
    args = parser.parse_args()

    settings = get_settings()
    database = _database_evidence(settings.database_url)
    inputs = build_release_inputs(
        PROJECT_ROOT,
        settings,
        database_fingerprint=database.get("catalogue_fingerprint"),
    )
    checks = _run_release_checks()
    git = _git_evidence()

    if args.verify:
        _verify_existing(inputs, checks, git, database)
        return

    personnel = _read_json(
        PROJECT_ROOT / "experiments" / "evaluation" / "v2_5" / "personnel.json"
    )
    checks_passed = all(check["passed"] for check in checks)
    manifest = {
        "release_version": RELEASE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "candidate_verified" if checks_passed else "candidate_failed",
        "freeze_instruction": (
            "Commit this candidate manifest with the release inputs, then run "
            "`py scripts/freeze_release.py --verify` from a clean working tree."
        ),
        "git_at_candidate_generation": git,
        "database": database,
        "verification": {
            "passed": checks_passed,
            "checks": checks,
        },
        "evaluation_approval": {
            "status": personnel.get("status", "missing"),
            "official_claims_allowed": personnel.get("status") == "complete",
            "note": (
                "Engineering release verification does not replace independent "
                "academic labelling and grounding review."
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": _package_versions(),
            "compose_sha256": sha256_file(PROJECT_ROOT / "compose.yaml"),
        },
        "release_inputs": inputs,
    }
    RELEASE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Release candidate: {manifest['status']}")
    print(f"Manifest: {MANIFEST_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Release fingerprint: {inputs['release_fingerprint']}")
    print(f"Working tree clean before generation: {git['working_tree_clean']}")
    if not checks_passed:
        raise SystemExit(1)


def _run_release_checks() -> list[dict[str, Any]]:
    environment = os.environ.copy()
    environment["HANDBOOK_RAG_DEMO_ENABLED"] = "false"
    commands: list[tuple[str, list[str]]] = [
        ("data_validation", [sys.executable, "scripts/validate_database.py"]),
        ("automated_tests", [sys.executable, "-m", "pytest", "-q"]),
        (
            "postgresql_smoke",
            [sys.executable, "-m", "pytest", "tests/test_postgres_runtime.py", "-q"],
        ),
    ]
    pnpm = shutil.which("pnpm")
    if pnpm:
        commands.append(("frontend_build", [pnpm, "run", "build:ui"]))
    else:
        return [
            *_execute_checks(commands, environment),
            {
                "name": "frontend_build",
                "passed": False,
                "exit_code": None,
                "duration_seconds": 0,
                "summary": "pnpm is not installed or not on PATH.",
            },
        ]
    return _execute_checks(commands, environment)


def _execute_checks(
    commands: list[tuple[str, list[str]]], environment: dict[str, str]
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for name, command in commands:
        started = perf_counter()
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        output = "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
        )
        checks.append(
            {
                "name": name,
                "passed": completed.returncode == 0,
                "exit_code": completed.returncode,
                "duration_seconds": round(perf_counter() - started, 3),
                "summary": "\n".join(output.splitlines()[-12:]),
            }
        )
        print(f"{name}: {'PASS' if completed.returncode == 0 else 'FAIL'}")
    return checks


def _database_evidence(database_url: str) -> dict[str, Any]:
    try:
        engine = create_database_engine(database_url)
        status = database_status(engine)
        status["catalogue_fingerprint"] = catalogue_version(engine)
        return status
    except Exception as error:
        return {
            "connected": False,
            "catalogue_fingerprint": None,
            "error": f"{type(error).__name__}: {error}",
        }


def _git_evidence() -> dict[str, Any]:
    status = _git("status", "--porcelain")
    return {
        "head": _git("rev-parse", "HEAD"),
        "branch": _git("branch", "--show-current"),
        "working_tree_clean": not bool(status),
    }


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()


def _package_versions() -> dict[str, str]:
    packages = (
        "fastapi",
        "google-genai",
        "huggingface-hub",
        "pgvector",
        "psycopg",
        "pydantic",
        "pytest",
        "sqlalchemy",
    )
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not_installed"
    return versions


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _verify_existing(
    inputs: dict[str, Any],
    checks: list[dict[str, Any]],
    git: dict[str, Any],
    database: dict[str, Any],
) -> None:
    if not MANIFEST_PATH.is_file():
        raise SystemExit("Release manifest is missing; run without --verify first.")
    manifest = _read_json(MANIFEST_PATH)
    frozen = manifest.get("release_inputs", {})
    changed = changed_release_sections(frozen, inputs)
    failures: list[str] = []
    if changed:
        failures.append(f"release inputs changed: {', '.join(changed)}")
    if not all(check["passed"] for check in checks):
        failures.append("one or more release checks failed")
    if not database.get("connected"):
        failures.append("PostgreSQL catalogue is unavailable")
    if not git["working_tree_clean"]:
        failures.append("working tree is not clean")
    if failures:
        for failure in failures:
            print(f"BLOCKED: {failure}")
        raise SystemExit(1)
    print("RELEASE FROZEN AND VERIFIED")
    print(f"Release fingerprint: {inputs['release_fingerprint']}")


if __name__ == "__main__":
    main()
