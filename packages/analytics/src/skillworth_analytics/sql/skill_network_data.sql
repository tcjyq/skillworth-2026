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
)
SELECT
    filtered_skill_pairs.canonical_job_id,
    skills.skill_id,
    skills.canonical_name,
    skills.category
FROM filtered_skill_pairs
INNER JOIN skills USING (skill_id)
ORDER BY filtered_skill_pairs.canonical_job_id, skills.skill_id;
