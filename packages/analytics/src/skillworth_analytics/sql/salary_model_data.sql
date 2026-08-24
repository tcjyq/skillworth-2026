WITH filtered_jobs AS (
    {filtered_jobs}
), filtered_mappings AS (
    SELECT DISTINCT mapping.canonical_job_id, mapping.silver_job_id
    FROM job_source_map AS mapping
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE {source_filter}
), filtered_skill_pairs AS (
    SELECT DISTINCT filtered_mappings.canonical_job_id, job_skills.skill_id
    FROM filtered_mappings
    INNER JOIN job_skills USING (silver_job_id)
), job_skill_lists AS (
    SELECT canonical_job_id, list(skill_id ORDER BY skill_id) AS skill_ids
    FROM filtered_skill_pairs
    GROUP BY canonical_job_id
)
SELECT
    filtered_jobs.canonical_job_id,
    filtered_jobs.salary_mid_monthly,
    filtered_jobs.role_id,
    filtered_jobs.city_code,
    filtered_jobs.experience_band,
    filtered_jobs.education_band,
    CASE
        WHEN filtered_jobs.published_at IS NULL THEN NULL
        ELSE strftime(filtered_jobs.published_at, '%Y-%m')
    END AS published_month,
    job_skill_lists.skill_ids
FROM filtered_jobs
LEFT JOIN job_skill_lists USING (canonical_job_id)
WHERE filtered_jobs.salary_mid_monthly BETWEEN ? AND ?
ORDER BY filtered_jobs.canonical_job_id;
