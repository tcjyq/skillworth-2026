CREATE OR REPLACE TABLE job_source_map AS
SELECT
    canonical_job_id,
    silver_job_id,
    source_record_id,
    source_id,
    source_job_id,
    source_url,
    observed_at,
    upstream_source,
    upstream_external_id,
    source_company_slug,
    api_accessed_at,
    source_payload_sha256,
    match_method,
    match_score,
    match_reason,
    deduplication_rule_version
FROM input_job_source_map;

CREATE OR REPLACE TABLE jobs AS
SELECT
    canonical_job_id,
    canonical_silver_job_id,
    title_source_silver_job_id,
    description_source_silver_job_id,
    CASE
        WHEN company_name_normalized IS NULL THEN NULL
        ELSE concat('company_', substr(sha256(company_name_normalized), 1, 24))
    END AS company_id,
    company_name_normalized,
    job_title_raw,
    job_title_normalized,
    role_id,
    city_code,
    experience_band,
    education_band,
    market_scope,
    market_scope_method,
    market_scope_version,
    try_cast(published_at AS DATE) AS published_at,
    try_cast(first_posted_at AS DATE) AS first_posted_at,
    try_cast(first_seen_at AS TIMESTAMPTZ) AS first_seen_at,
    try_cast(last_seen_at AS TIMESTAMPTZ) AS last_seen_at,
    job_description_raw,
    salary_observations,
    try_cast(canonical_salary AS DOUBLE) AS canonical_salary,
    try_cast(salary_mid_monthly AS DOUBLE) AS salary_mid_monthly,
    salary_source_count,
    salary_conflict_flag,
    salary_months,
    salary_parse_status,
    group_size,
    deduplication_status,
    canonicalization_method,
    deduplication_rule_version,
    canonical_merge_version
FROM input_canonical_jobs;

CREATE OR REPLACE TABLE companies AS
SELECT
    company_id,
    min(company_name_normalized) AS company_name_normalized,
    count(DISTINCT canonical_job_id) AS canonical_job_count
FROM jobs
WHERE company_id IS NOT NULL
GROUP BY company_id;

CREATE OR REPLACE TABLE skills AS
SELECT
    skill_id,
    canonical_name,
    category,
    aliases,
    learning_hours_min,
    learning_hours_expected,
    learning_hours_max,
    learning_cost_source,
    notes,
    skill_type,
    skillworth_eligibility,
    skillworth_reason,
    taxonomy_version
FROM input_skills;

CREATE OR REPLACE TABLE job_skills AS
SELECT DISTINCT
    mapping.canonical_job_id,
    extracted.silver_job_id,
    extracted.skill_id,
    extracted.canonical_skill,
    extracted.matched_text,
    extracted.extraction_method,
    extracted.confidence,
    extracted.taxonomy_version
FROM input_job_skills AS extracted
INNER JOIN job_source_map AS mapping
    ON mapping.silver_job_id = extracted.silver_job_id;

CREATE OR REPLACE TABLE sources AS
SELECT
    source_id,
    count(DISTINCT silver_job_id) AS source_job_count,
    count(DISTINCT canonical_job_id) AS canonical_job_count,
    min(try_cast(observed_at AS TIMESTAMPTZ)) AS first_observed_at,
    max(try_cast(observed_at AS TIMESTAMPTZ)) AS last_observed_at
FROM job_source_map
GROUP BY source_id;
