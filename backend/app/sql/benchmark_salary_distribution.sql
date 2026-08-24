SELECT role_id, city_code, salary_job_count, salary_median_monthly
FROM salary_distribution
ORDER BY salary_job_count DESC, role_id, city_code;
