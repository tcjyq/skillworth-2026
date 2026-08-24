WITH target_jobs AS (
    {target_jobs}
), current_skills AS (
    SELECT unnest(?::VARCHAR[]) AS skill_id
), job_skill_pairs AS (
    SELECT DISTINCT job_skills.canonical_job_id, job_skills.skill_id
    FROM job_skills
    INNER JOIN target_jobs USING (canonical_job_id)
), job_fit AS (
    SELECT
        job_skill_pairs.canonical_job_id,
        count(*)::BIGINT AS required_skill_count,
        count(current_skills.skill_id)::BIGINT AS matched_skill_count,
        count(current_skills.skill_id)::DOUBLE / count(*) AS current_fit
    FROM job_skill_pairs
    LEFT JOIN current_skills USING (skill_id)
    GROUP BY job_skill_pairs.canonical_job_id
), source_jobs AS (
    SELECT DISTINCT
        job_source_map.source_id,
        job_fit.canonical_job_id,
        job_fit.required_skill_count,
        job_fit.current_fit,
        target_jobs.published_at
    FROM job_fit
    INNER JOIN target_jobs USING (canonical_job_id)
    INNER JOIN job_source_map USING (canonical_job_id)
), source_baseline AS (
    SELECT
        source_id,
        count(*)::BIGINT AS source_sample_size,
        max(published_at) AS latest_observation_date,
        avg(current_fit) AS current_average_fit
    FROM source_jobs
    GROUP BY source_id
), candidates AS (
    SELECT DISTINCT job_skill_pairs.skill_id
    FROM job_skill_pairs
    WHERE NOT EXISTS (
        SELECT 1 FROM current_skills
        WHERE current_skills.skill_id = job_skill_pairs.skill_id
    )
), source_candidate_impacts AS (
    SELECT
        source_jobs.source_id,
        job_skill_pairs.skill_id,
        sum(1.0 / source_jobs.required_skill_count)::DOUBLE
            / max(source_baseline.source_sample_size) AS average_fit_gain
    FROM source_jobs
    INNER JOIN job_skill_pairs USING (canonical_job_id)
    INNER JOIN candidates USING (skill_id)
    INNER JOIN source_baseline USING (source_id)
    GROUP BY source_jobs.source_id, job_skill_pairs.skill_id
)
SELECT
    source_baseline.source_id,
    source_baseline.source_sample_size,
    source_baseline.latest_observation_date,
    source_baseline.current_average_fit,
    candidates.skill_id,
    coalesce(source_candidate_impacts.average_fit_gain, 0.0) AS candidate_average_fit_gain
FROM source_baseline
LEFT JOIN candidates ON TRUE
LEFT JOIN source_candidate_impacts
    ON source_candidate_impacts.source_id = source_baseline.source_id
    AND source_candidate_impacts.skill_id = candidates.skill_id
ORDER BY source_baseline.source_id, candidates.skill_id;
