SELECT 'jobs_canonical_job_id_unique' AS test_name,
       count(*) - count(DISTINCT canonical_job_id) AS violation_count
FROM jobs
UNION ALL
SELECT 'job_source_map_silver_job_id_unique',
       count(*) - count(DISTINCT silver_job_id)
FROM job_source_map
UNION ALL
SELECT 'skills_skill_id_unique',
       count(*) - count(DISTINCT skill_id)
FROM skills
UNION ALL
SELECT 'job_skills_composite_key_unique',
       count(*)
FROM (
    SELECT canonical_job_id, silver_job_id, skill_id
    FROM job_skills
    GROUP BY canonical_job_id, silver_job_id, skill_id
    HAVING count(*) > 1
)
UNION ALL
SELECT 'jobs_critical_fields_not_null',
       count(*)
FROM jobs
WHERE canonical_job_id IS NULL OR canonical_silver_job_id IS NULL
UNION ALL
SELECT 'job_source_map_critical_fields_not_null',
       count(*)
FROM job_source_map
WHERE canonical_job_id IS NULL OR silver_job_id IS NULL OR source_record_id IS NULL OR source_id IS NULL
UNION ALL
SELECT 'job_skills_critical_fields_not_null',
       count(*)
FROM job_skills
WHERE canonical_job_id IS NULL OR silver_job_id IS NULL OR skill_id IS NULL
UNION ALL
SELECT 'jobs_row_count_matches_input',
       abs((SELECT count(*) FROM jobs) - (SELECT count(*) FROM input_canonical_jobs))
UNION ALL
SELECT 'job_source_map_row_count_matches_input',
       abs((SELECT count(*) FROM job_source_map) - (SELECT count(*) FROM input_job_source_map))
UNION ALL
SELECT 'jobs_group_size_range',
       count(*)
FROM jobs
WHERE group_size < 1
UNION ALL
SELECT 'jobs_salary_range',
       count(*)
FROM jobs
WHERE NOT isfinite(salary_mid_monthly) OR salary_mid_monthly < 0
UNION ALL
SELECT 'skill_demand_coverage_range',
       count(*)
FROM skill_demand
WHERE job_coverage_rate < 0 OR job_coverage_rate > 1
UNION ALL
SELECT 'job_skills_references_existing_jobs',
       count(*)
FROM job_skills AS relation
LEFT JOIN jobs USING (canonical_job_id)
WHERE jobs.canonical_job_id IS NULL
UNION ALL
SELECT 'job_skills_references_existing_skills',
       count(*)
FROM job_skills AS relation
LEFT JOIN skills USING (skill_id)
WHERE skills.skill_id IS NULL;
