WITH filtered_jobs AS (
    {filtered_jobs}
), filtered_mappings AS (
    SELECT DISTINCT mapping.canonical_job_id, mapping.silver_job_id
    FROM job_source_map AS mapping
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE {source_filter}
), dimension_totals AS (
    SELECT {dimension_column} AS dimension_value, count(*) AS sample_size
    FROM filtered_jobs
    WHERE {dimension_column} IS NOT NULL
    GROUP BY {dimension_column}
), skill_counts AS (
    SELECT
        filtered_jobs.{dimension_column} AS dimension_value,
        job_skills.skill_id,
        count(DISTINCT job_skills.canonical_job_id) AS job_count
    FROM filtered_jobs
    INNER JOIN filtered_mappings USING (canonical_job_id)
    INNER JOIN job_skills USING (silver_job_id)
    WHERE filtered_jobs.{dimension_column} IS NOT NULL
    GROUP BY filtered_jobs.{dimension_column}, job_skills.skill_id
)
SELECT
    '{dimension}' AS dimension,
    skill_counts.dimension_value,
    skills.skill_id,
    skills.canonical_name,
    skills.category,
    skill_counts.job_count::BIGINT AS job_count,
    skill_counts.job_count::DOUBLE / nullif(dimension_totals.sample_size, 0) AS job_coverage,
    dimension_totals.sample_size::BIGINT AS sample_size
FROM skill_counts
INNER JOIN dimension_totals USING (dimension_value)
INNER JOIN skills USING (skill_id)
ORDER BY dimension_value, job_count DESC, skills.skill_id;
