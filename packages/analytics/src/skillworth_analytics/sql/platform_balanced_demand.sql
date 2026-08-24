WITH filtered_jobs AS (
    {filtered_jobs}
), filtered_source_jobs AS (
    SELECT DISTINCT mapping.source_id, mapping.silver_job_id, mapping.canonical_job_id
    FROM job_source_map AS mapping
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE {source_filter}
), source_totals AS (
    SELECT source_id, count(*) AS source_sample_size
    FROM filtered_source_jobs
    GROUP BY source_id
), source_skill_counts AS (
    SELECT
        filtered_source_jobs.source_id,
        job_skills.skill_id,
        count(DISTINCT filtered_source_jobs.silver_job_id) AS job_count
    FROM filtered_source_jobs
    INNER JOIN job_skills USING (silver_job_id)
    GROUP BY filtered_source_jobs.source_id, job_skills.skill_id
), pooled_counts AS (
    SELECT job_skills.skill_id, count(DISTINCT filtered_source_jobs.canonical_job_id) AS pooled_job_count
    FROM filtered_source_jobs
    INNER JOIN job_skills USING (silver_job_id)
    GROUP BY job_skills.skill_id
), totals AS (
    SELECT count(*) AS sample_size
    FROM filtered_jobs
), by_platform AS (
    SELECT
        skills.skill_id,
        skills.canonical_name,
        skills.category,
        source_totals.source_id,
        coalesce(source_skill_counts.job_count, 0)::BIGINT AS job_count,
        coalesce(source_skill_counts.job_count, 0)::DOUBLE / nullif(source_totals.source_sample_size, 0) AS job_coverage,
        source_totals.source_sample_size::BIGINT AS source_sample_size,
        coalesce(pooled_counts.pooled_job_count, 0)::DOUBLE / nullif(totals.sample_size, 0) AS pooled_coverage,
        count(*) OVER (PARTITION BY skills.skill_id)::BIGINT AS source_count,
        totals.sample_size::BIGINT AS sample_size
    FROM skills
    CROSS JOIN source_totals
    CROSS JOIN totals
    LEFT JOIN source_skill_counts USING (source_id, skill_id)
    LEFT JOIN pooled_counts USING (skill_id)
)
SELECT
    *,
    avg(job_coverage) OVER (PARTITION BY skill_id) AS platform_balanced_coverage
FROM by_platform
ORDER BY skill_id, source_id;
