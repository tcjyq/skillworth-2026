WITH filtered_jobs AS (
    {filtered_jobs}
), filtered_mappings AS (
    SELECT DISTINCT mapping.canonical_job_id, mapping.silver_job_id
    FROM job_source_map AS mapping
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE {source_filter}
), skill_pairs AS (
    SELECT DISTINCT filtered_mappings.canonical_job_id, job_skills.skill_id
    FROM filtered_mappings
    INNER JOIN job_skills USING (silver_job_id)
), skill_job_counts AS (
    SELECT skill_id, count(*) AS job_count
    FROM skill_pairs
    GROUP BY skill_id
), salary_stats AS (
    SELECT
        skill_pairs.skill_id,
        count(*) AS sample_size,
        median(filtered_jobs.salary_mid_monthly) AS median,
        quantile_cont(filtered_jobs.salary_mid_monthly, 0.25) AS p25,
        quantile_cont(filtered_jobs.salary_mid_monthly, 0.75) AS p75
    FROM skill_pairs
    INNER JOIN filtered_jobs USING (canonical_job_id)
    WHERE filtered_jobs.salary_mid_monthly IS NOT NULL
    GROUP BY skill_pairs.skill_id
)
SELECT
    skills.skill_id,
    skills.canonical_name,
    skills.category,
    salary_stats.median,
    salary_stats.p25,
    salary_stats.p75,
    coalesce(salary_stats.sample_size, 0)::BIGINT AS sample_size,
    coalesce(salary_stats.sample_size, 0)::DOUBLE / nullif(skill_job_counts.job_count, 0) AS salary_coverage
FROM skill_job_counts
INNER JOIN skills USING (skill_id)
LEFT JOIN salary_stats USING (skill_id)
ORDER BY sample_size DESC, skills.skill_id;
