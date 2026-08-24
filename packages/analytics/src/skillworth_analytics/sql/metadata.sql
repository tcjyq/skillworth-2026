WITH filtered_jobs AS (
    {filtered_jobs}
), filtered_mappings AS (
    SELECT DISTINCT mapping.canonical_job_id, mapping.source_id
    FROM job_source_map AS mapping
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE {source_filter}
)
SELECT
    count(DISTINCT filtered_jobs.canonical_job_id) AS sample_size,
    count(DISTINCT filtered_mappings.source_id) AS source_count,
    min(filtered_jobs.published_at) AS published_from,
    max(filtered_jobs.published_at) AS published_to
FROM filtered_jobs
LEFT JOIN filtered_mappings USING (canonical_job_id);
