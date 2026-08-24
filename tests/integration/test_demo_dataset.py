from __future__ import annotations

import json
from pathlib import Path

import duckdb

from app.demo_dataset import build_demo_dataset


def test_demo_dataset_rebuilds_from_versioned_fixture(tmp_path: Path) -> None:
    output_root = tmp_path / "demo"

    result = build_demo_dataset(output_root=output_root)

    assert result.manifest_path.is_file()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["data_mode"] == "demo"
    assert manifest["snapshot"] == "demo-2026-08-08"
    assert manifest["access_date"] == "2026-08-08"
    assert Path(manifest["warehouse_path"]).is_file()
    assert Path(manifest["graph_edges_path"]).is_file()
    assert Path(manifest["quality_report_path"]).is_file()

    connection = duckdb.connect(manifest["warehouse_path"], read_only=True)
    try:
        assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 8
        assert connection.execute(
            "SELECT count(*) FROM china_skillworth_visual_ready"
        ).fetchone()[0] > 0
    finally:
        connection.close()
