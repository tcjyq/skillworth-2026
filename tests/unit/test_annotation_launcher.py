from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.annotation_launcher import launch_annotation_workspace


def test_launcher_uses_streamlit_without_importing_predictions_as_gold(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, *, env, check):
        captured.update(command=command, env=env, check=check)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("app.annotation_launcher.subprocess.run", fake_run)
    result = launch_annotation_workspace(
        benchmark_root=tmp_path / "benchmarks",
        skill_taxonomy_path=tmp_path / "skills.yml",
        role_taxonomy_path=tmp_path / "roles.json",
        silver_path=tmp_path / "silver.parquet",
        port=8510,
    )

    assert result == 0
    assert captured["command"][1:4] == ["-m", "streamlit", "run"]
    assert "8510" in captured["command"]
    assert captured["env"]["SKILLWORTH_ANNOTATION_ROOT"].endswith("benchmarks")
