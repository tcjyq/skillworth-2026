from pathlib import Path

import yaml

from app.benchmark_status import benchmark_readiness_status


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_benchmark_status_reports_unlabeled_and_valid_split(tmp_path: Path) -> None:
    benchmark_root = tmp_path / "benchmarks"
    quality_path = tmp_path / "quality.yml"
    quality_path.write_text(
        """
quality_gates:
  skills: {minimum_gold_samples: 1}
  roles: {minimum_gold_samples: 1}
  dedup: {minimum_gold_pairs: 1}
""".strip(),
        encoding="utf-8",
    )
    from app.annotation_batches import _hash, _split

    role_id = "role-1"
    skill_id = "skill-1"
    left_id, right_id = "left-1", "right-1"
    pair_key = "|".join(sorted((left_id, right_id)))
    pair_id = _hash(pair_key)[:24]
    metadata = {"split_seed": 42}
    _write_yaml(
        benchmark_root / "roles/pending/batch.yml",
        {"metadata": metadata, "records": [{"record_id": role_id, "predicted_role": "other", "gold_role": None, "annotation_notes": "", "split": _split(role_id, 42)}]},
    )
    _write_yaml(
        benchmark_root / "skills/pending/batch.yml",
        {"metadata": metadata, "records": [{"record_id": skill_id, "predicted_skills": [], "gold_skills": None, "annotation_notes": "", "split": _split(skill_id, 42)}]},
    )
    _write_yaml(
        benchmark_root / "dedup/pending/batch.yml",
        {"metadata": metadata, "pairs": [{"pair_id": pair_id, "left_job_id": left_id, "right_job_id": right_id, "predicted_duplicate": False, "gold_duplicate": None, "annotation_notes": "", "split": _split(pair_key, 42)}]},
    )
    for name, rows_key in (("roles", "records"), ("skills", "records"), ("dedup", "pairs")):
        _write_yaml(benchmark_root / name / "gold.yml", {rows_key: []})

    result = benchmark_readiness_status(benchmark_root, quality_path)

    assert result.status == "NOT READY"
    assert result.pending_sample_count == 3
    assert result.unlabeled_sample_count == 3
    assert all(item.unique_sample_ids for item in result.collections)
    assert all(item.stable_sample_ids for item in result.collections)
    assert all(item.deterministic_split for item in result.collections)


def test_benchmark_status_is_ready_only_after_human_gold_exists(tmp_path: Path) -> None:
    benchmark_root = tmp_path / "benchmarks"
    quality_path = tmp_path / "quality.yml"
    quality_path.write_text(
        "quality_gates:\n  skills: {minimum_gold_samples: 1}\n  roles: {minimum_gold_samples: 1}\n  dedup: {minimum_gold_pairs: 1}\n",
        encoding="utf-8",
    )
    from app.annotation_batches import _hash, _split

    pair_key = "left|right"
    pending = {
        "roles": ("records", [{"record_id": "role", "predicted_role": "other", "gold_role": None, "annotation_notes": "", "split": _split("role", 42)}]),
        "skills": ("records", [{"record_id": "skill", "predicted_skills": [], "gold_skills": None, "annotation_notes": "", "split": _split("skill", 42)}]),
        "dedup": ("pairs", [{"pair_id": _hash(pair_key)[:24], "left_job_id": "left", "right_job_id": "right", "predicted_duplicate": False, "gold_duplicate": None, "annotation_notes": "", "split": _split(pair_key, 42)}]),
    }
    for name, (rows_key, rows) in pending.items():
        _write_yaml(benchmark_root / name / "pending/batch.yml", {"metadata": {"split_seed": 42}, rows_key: rows})
        id_key = "pair_id" if name == "dedup" else "record_id"
        _write_yaml(
            benchmark_root / name / "gold.yml",
            {rows_key: [{id_key: rows[0][id_key], "human_confirmed": True}]},
        )

    result = benchmark_readiness_status(benchmark_root, quality_path)

    assert result.status == "READY FOR EVALUATION"
    assert result.pending_sample_count == 3
