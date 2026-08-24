WITH filtered_jobs AS (
    {filtered_jobs}
), filtered_mappings AS (
    SELECT DISTINCT mapping.canonical_job_id, mapping.source_id
    FROM job_source_map AS mapping
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE {source_filter}
), skill_pairs AS (
    SELECT DISTINCT filtered_mappings.canonical_job_id, job_skills.skill_id
    FROM filtered_mappings
    INNER JOIN job_source_map AS mapping
        ON mapping.canonical_job_id = filtered_mappings.canonical_job_id
        AND mapping.source_id = filtered_mappings.source_id
    INNER JOIN job_skills
        ON job_skills.silver_job_id = mapping.silver_job_id
), skill_counts AS (
    SELECT skill_id, count(*) AS job_count
    FROM skill_pairs
    GROUP BY skill_id
), skill_sources AS (
    SELECT skill_pairs.skill_id, count(DISTINCT filtered_mappings.source_id) AS source_count
    FROM skill_pairs
    INNER JOIN filtered_mappings USING (canonical_job_id)
    GROUP BY skill_pairs.skill_id
), totals AS (
    SELECT count(*) AS sample_size
    FROM filtered_jobs
)
SELECT
    skills.skill_id,
    skills.canonical_name,
    skills.category,
    coalesce(skill_counts.job_count, 0)::BIGINT AS job_count,
    coalesce(skill_counts.job_count, 0)::DOUBLE / nullif(totals.sample_size, 0) AS job_coverage,
    coalesce(skill_sources.source_count, 0)::BIGINT AS source_count,
    totals.sample_size::BIGINT AS sample_size
FROM skills
CROSS JOIN totals
LEFT JOIN skill_counts USING (skill_id)
LEFT JOIN skill_sources USING (skill_id)
ORDER BY job_count DESC, skills.skill_id;
