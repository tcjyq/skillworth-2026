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
), monthly_jobs AS (
    SELECT
        date_trunc('month', published_at)::DATE AS month,
        canonical_job_id
    FROM filtered_jobs
    WHERE published_at IS NOT NULL
), monthly_totals AS (
    SELECT month, count(DISTINCT canonical_job_id) AS sample_size
    FROM monthly_jobs
    GROUP BY month
), active_skills AS (
    SELECT DISTINCT filtered_skill_pairs.skill_id, skills.canonical_name, skills.category
    FROM filtered_skill_pairs
    INNER JOIN skills USING (skill_id)
), monthly_skill_counts AS (
    SELECT
        monthly_jobs.month,
        filtered_skill_pairs.skill_id,
        count(DISTINCT monthly_jobs.canonical_job_id) AS job_count
    FROM monthly_jobs
    INNER JOIN filtered_skill_pairs USING (canonical_job_id)
    GROUP BY monthly_jobs.month, filtered_skill_pairs.skill_id
)
SELECT
    active_skills.skill_id,
    active_skills.canonical_name,
    active_skills.category,
    monthly_totals.month,
    coalesce(monthly_skill_counts.job_count, 0)::BIGINT AS job_count,
    monthly_totals.sample_size::BIGINT AS sample_size,
    coalesce(monthly_skill_counts.job_count, 0)::DOUBLE / monthly_totals.sample_size AS skill_job_coverage
FROM active_skills
CROSS JOIN monthly_totals
LEFT JOIN monthly_skill_counts USING (month, skill_id)
ORDER BY active_skills.skill_id, monthly_totals.month;
