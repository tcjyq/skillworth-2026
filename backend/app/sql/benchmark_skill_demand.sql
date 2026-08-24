SELECT skill_id, canonical_name, job_count, job_coverage_rate
FROM skill_demand
ORDER BY job_count DESC, skill_id
LIMIT 50;
