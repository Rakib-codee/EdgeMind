"""Tests for the reproducibility manifest."""

import json

from benchmarks.manifest import (
    build_manifest,
    git_state,
    sha256_file,
    write_manifest,
)


def test_sha256_file_is_deterministic(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("a,b\n1,2\n")
    assert sha256_file(f) == sha256_file(f)
    f.write_text("a,b\n1,3\n")
    first = sha256_file(tmp_path / "data.csv")
    f.write_text("a,b\n1,4\n")
    assert sha256_file(f) != first


def test_manifest_schema(tmp_path):
    out = tmp_path / "out.csv"
    out.write_text("x\n1\n")
    manifest = build_manifest(
        command="python -m benchmarks.run_evaluation --seeds 10",
        config={"seeds": 10},
        outputs=[out],
    )
    for key in (
        "schema_version",
        "generated_at",
        "command",
        "git",
        "python_version",
        "dependencies",
        "scheduler_weights",
        "config",
        "inputs",
        "outputs",
    ):
        assert key in manifest
    assert manifest["outputs"][0]["sha256"] == sha256_file(out)
    assert manifest["config"]["seeds"] == 10


def test_manifest_handles_missing_optional_metadata(tmp_path, monkeypatch):
    # Git unavailable -> commit recorded as None, not an exception.
    import benchmarks.manifest as manifest_module

    monkeypatch.setattr(
        manifest_module, "git_state", lambda cwd=None: {"commit": None, "dirty": None}
    )
    manifest = build_manifest(command="test", config={})
    assert manifest["git"]["commit"] is None
    assert manifest["inputs"] == []
    assert manifest["outputs"] == []


def test_write_and_read_roundtrip(tmp_path):
    manifest = build_manifest(command="test", config={"a": 1})
    path = write_manifest(manifest, tmp_path / "run.manifest.json")
    loaded = json.loads(path.read_text())
    assert loaded["command"] == "test"
    assert loaded["config"] == {"a": 1}


def test_git_state_reports_real_commit():
    state = git_state()
    assert state["commit"] is not None
    assert len(state["commit"]) == 40
