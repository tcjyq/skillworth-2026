CREATE OR REPLACE VIEW role_summary AS
SELECT
    role_id,
    count(*) AS canonical_job_count,
    count(DISTINCT company_id) AS company_count,
    count(DISTINCT city_code) AS city_count,
    median(salary_mid_monthly) AS salary_mid_median
FROM jobs
GROUP BY role_id;

CREATE OR REPLACE VIEW city_summary AS
SELECT
    city_code,
    count(*) AS canonical_job_count,
    count(DISTINCT company_id) AS company_count,
    count(DISTINCT role_id) AS role_count,
    median(salary_mid_monthly) AS salary_mid_median
FROM jobs
GROUP BY city_code;

CREATE OR REPLACE VIEW source_summary AS
SELECT
    source_id,
    source_job_count,
    canonical_job_count,
    first_observed_at,
    last_observed_at
FROM sources;

CREATE OR REPLACE VIEW skill_demand AS
WITH job_total AS (
    SELECT count(*) AS canonical_job_total
    FROM jobs
), skill_counts AS (
    SELECT skill_id, count(DISTINCT canonical_job_id) AS job_count
    FROM job_skills
    GROUP BY skill_id
)
SELECT
    skills.skill_id,
    skills.canonical_name,
    skills.category,
    coalesce(skill_counts.job_count, 0) AS job_count,
    coalesce(skill_counts.job_count, 0)::DOUBLE / nullif(job_total.canonical_job_total, 0) AS job_coverage_rate,
    job_total.canonical_job_total
FROM skills
CROSS JOIN job_total
LEFT JOIN skill_counts USING (skill_id);

CREATE OR REPLACE VIEW source_skill_demand AS
WITH source_totals AS (
    SELECT source_id, count(DISTINCT silver_job_id) AS source_job_count
    FROM job_source_map
    GROUP BY source_id
), source_skill_counts AS (
    SELECT
        mapping.source_id,
        extracted.skill_id,
        count(DISTINCT extracted.silver_job_id) AS source_job_count_with_skill
    FROM job_source_map AS mapping
    INNER JOIN job_skills AS extracted
        ON extracted.silver_job_id = mapping.silver_job_id
    GROUP BY mapping.source_id, extracted.skill_id
)
SELECT
    source_skill_counts.source_id,
    skills.skill_id,
    skills.canonical_name,
    skills.category,
    source_skill_counts.source_job_count_with_skill,
    source_totals.source_job_count,
    source_skill_counts.source_job_count_with_skill::DOUBLE / nullif(source_totals.source_job_count, 0) AS source_job_coverage_rate
FROM source_skill_counts
INNER JOIN source_totals USING (source_id)
INNER JOIN skills USING (skill_id);

CREATE OR REPLACE VIEW monthly_skill_demand AS
WITH monthly_jobs AS (
    SELECT date_trunc('month', published_at)::DATE AS month, canonical_job_id
    FROM jobs
    WHERE published_at IS NOT NULL
), monthly_totals AS (
    SELECT month, count(DISTINCT canonical_job_id) AS canonical_job_total
    FROM monthly_jobs
    GROUP BY month
), monthly_skill_counts AS (
    SELECT
        monthly_jobs.month,
        job_skills.skill_id,
        count(DISTINCT monthly_jobs.canonical_job_id) AS job_count
    FROM monthly_jobs
    INNER JOIN job_skills USING (canonical_job_id)
    GROUP BY monthly_jobs.month, job_skills.skill_id
)
SELECT
    monthly_skill_counts.month,
    monthly_skill_counts.skill_id,
    skills.canonical_name,
    skills.category,
    monthly_skill_counts.job_count,
    monthly_totals.canonical_job_total,
    monthly_skill_counts.job_count::DOUBLE / nullif(monthly_totals.canonical_job_total, 0) AS job_coverage_rate
FROM monthly_skill_counts
INNER JOIN monthly_totals USING (month)
INNER JOIN skills USING (skill_id);

CREATE OR REPLACE VIEW salary_distribution AS
SELECT
    role_id,
    city_code,
    count(*) AS salary_job_count,
    min(salary_mid_monthly) AS salary_min_monthly,
    median(salary_mid_monthly) AS salary_median_monthly,
    max(salary_mid_monthly) AS salary_max_monthly
FROM jobs
WHERE salary_mid_monthly IS NOT NULL
GROUP BY role_id, city_code;

CREATE OR REPLACE VIEW skill_salary AS
WITH canonical_skill_pairs AS (
    SELECT DISTINCT canonical_job_id, skill_id
    FROM job_skills
)
SELECT
    skills.skill_id,
    skills.canonical_name,
    skills.category,
    count(*) AS salary_job_count,
    median(jobs.salary_mid_monthly) AS salary_median_monthly
FROM canonical_skill_pairs
INNER JOIN jobs USING (canonical_job_id)
INNER JOIN skills USING (skill_id)
WHERE jobs.salary_mid_monthly IS NOT NULL
GROUP BY skills.skill_id, skills.canonical_name, skills.category;

CREATE OR REPLACE VIEW skill_role AS
SELECT
    job_skills.skill_id,
    jobs.role_id,
    count(DISTINCT job_skills.canonical_job_id) AS job_count
FROM job_skills
INNER JOIN jobs USING (canonical_job_id)
GROUP BY job_skills.skill_id, jobs.role_id;

CREATE OR REPLACE VIEW skill_city AS
SELECT
    job_skills.skill_id,
    jobs.city_code,
    count(DISTINCT job_skills.canonical_job_id) AS job_count
FROM job_skills
INNER JOIN jobs USING (canonical_job_id)
GROUP BY job_skills.skill_id, jobs.city_code;
