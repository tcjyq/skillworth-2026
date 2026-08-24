from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def launch_annotation_workspace(
    *,
    benchmark_root: Path,
    skill_taxonomy_path: Path,
    role_taxonomy_path: Path,
    silver_path: Path | None,
    port: int,
) -> int:
    app_path = Path(__file__).with_name("annotation_ui.py")
    environment = os.environ.copy()
    environment.update(
        {
            "SKILLWORTH_ANNOTATION_ROOT": str(benchmark_root.resolve()),
            "SKILLWORTH_SKILL_TAXONOMY": str(skill_taxonomy_path.resolve()),
            "SKILLWORTH_ROLE_TAXONOMY": str(role_taxonomy_path.resolve()),
        }
    )
    if silver_path is not None:
        environment["SKILLWORTH_ANNOTATION_SILVER"] = str(silver_path.resolve())
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.headless",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]
    return subprocess.run(command, env=environment, check=False).returncode

