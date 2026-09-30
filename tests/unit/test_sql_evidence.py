"""Synthetic join-cardinality example for the public SQL evidence note."""

import duckdb


def test_source_mapping_join_requires_canonical_job_distinct() -> None:
    connection = duckdb.connect(":memory:")
    try:
        connection.execute("CREATE TABLE jobs (canonical_job_id VARCHAR, published_at DATE)")
        connection.execute("CREATE TABLE job_skills (canonical_job_id VARCHAR, skill_id VARCHAR)")
        connection.execute("CREATE TABLE job_source_map (canonical_job_id VARCHAR, silver_job_id VARCHAR)")
        connection.execute("INSERT INTO jobs VALUES ('j1', '2026-08-01'), ('j2', '2026-07-01')")
        connection.execute("INSERT INTO job_skills VALUES ('j1', 'python'), ('j2', 'python')")
        connection.execute("INSERT INTO job_source_map VALUES ('j1', 's1'), ('j1', 's2'), ('j2', 's3')")
        naive, canonical = connection.execute(
            """SELECT count(*), count(DISTINCT jobs.canonical_job_id)
               FROM jobs
               JOIN job_skills USING (canonical_job_id)
               JOIN job_source_map USING (canonical_job_id)
               WHERE skill_id = 'python' AND published_at >= DATE '2026-02-11'"""
        ).fetchone()
        denominator = connection.execute(
            "SELECT count(DISTINCT canonical_job_id) FROM jobs WHERE published_at >= DATE '2026-02-11'"
        ).fetchone()[0]
        assert (naive, canonical, denominator) == (3, 2, 2)
    finally:
        connection.close()
