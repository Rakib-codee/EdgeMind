"""Reproducibility manifest for benchmark runs.

Captures the provenance of an experiment run as a small JSON document
written next to the run's output CSV. The manifest is metadata-only:
it lives outside the deterministic CSV artifacts, so fields like the
generation timestamp do not affect reproducibility of results.

Note: results produced before this tooling existed (e.g. the *_v2
files) carry their provenance in git history, not in manifests; the
manifest records the commit at the time of the run it describes.
"""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.scheduler.adaptive import DEFAULT_WEIGHTS

TRACKED_DEPENDENCIES = ("fastapi", "pydantic", "numpy", "pandas")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_state(cwd: Path | None = None) -> dict:
    """Current commit and dirty flag; None values when git is unavailable."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd, capture_output=True, text=True, check=True,
            ).stdout.strip()
        )
        return {"commit": commit, "dirty": dirty}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"commit": None, "dirty": None}


def dependency_versions() -> dict:
    versions = {}
    for package in TRACKED_DEPENDENCIES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def host_metadata() -> dict:
    """Host and Docker environment metadata; None when unavailable."""
    try:
        docker_version = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        docker_version = None
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "arch": platform.machine(),
        "docker_version": docker_version,
    }


def build_manifest(
    command: str,
    config: dict,
    inputs: list[Path] | None = None,
    outputs: list[Path] | None = None,
) -> dict:
    def describe(paths):
        return [
            {"path": str(p), "sha256": sha256_file(p)}
            for p in (paths or [])
            if Path(p).exists()
        ]

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "git": git_state(),
        "python_version": platform.python_version(),
        "host": host_metadata(),
        "dependencies": dependency_versions(),
        "scheduler_weights": {
            "load": DEFAULT_WEIGHTS.load,
            "failure": DEFAULT_WEIGHTS.failure,
        },
        "config": config,
        "inputs": describe(inputs),
        "outputs": describe(outputs),
    }


def write_manifest(manifest: dict, path: Path) -> Path:
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path
