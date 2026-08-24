WITH filtered_jobs AS (
    {filtered_jobs}
), filtered_source_jobs AS (
    SELECT DISTINCT mapping.source_id, mapping.silver_job_id, mapping.canonical_job_id
    FROM job_source_map AS mapping
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE {source_filter}
), source_totals AS (
    SELECT source_id, count(*) AS sample_size
    FROM filtered_source_jobs
    GROUP BY source_id
), role_mix AS (
    SELECT 'role' AS dimension, filtered_source_jobs.source_id, filtered_jobs.role_id AS value,
           count(*) AS job_count
    FROM filtered_source_jobs
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE filtered_jobs.role_id IS NOT NULL
    GROUP BY filtered_source_jobs.source_id, filtered_jobs.role_id
), city_mix AS (
    SELECT 'city' AS dimension, filtered_source_jobs.source_id, filtered_jobs.city_code AS value,
           count(*) AS job_count
    FROM filtered_source_jobs
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE filtered_jobs.city_code IS NOT NULL
    GROUP BY filtered_source_jobs.source_id, filtered_jobs.city_code
), experience_mix AS (
    SELECT 'experience' AS dimension, filtered_source_jobs.source_id, filtered_jobs.experience_band AS value,
           count(*) AS job_count
    FROM filtered_source_jobs
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE filtered_jobs.experience_band IS NOT NULL
    GROUP BY filtered_source_jobs.source_id, filtered_jobs.experience_band
), skill_mix AS (
    SELECT 'skill' AS dimension, filtered_source_jobs.source_id, job_skills.skill_id AS value,
           count(DISTINCT filtered_source_jobs.silver_job_id) AS job_count
    FROM filtered_source_jobs
    INNER JOIN job_skills USING (silver_job_id)
    GROUP BY filtered_source_jobs.source_id, job_skills.skill_id
), combined AS (
    SELECT * FROM role_mix
    UNION ALL SELECT * FROM city_mix
    UNION ALL SELECT * FROM experience_mix
    UNION ALL SELECT * FROM skill_mix
)
SELECT
    combined.dimension,
    combined.source_id,
    combined.value,
    combined.job_count::BIGINT AS job_count,
    combined.job_count::DOUBLE / nullif(source_totals.sample_size, 0) AS job_coverage,
    source_totals.sample_size::BIGINT AS sample_size
FROM combined
INNER JOIN source_totals USING (source_id)
ORDER BY dimension, source_id, value;
