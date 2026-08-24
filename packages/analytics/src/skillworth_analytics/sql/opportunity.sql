WITH target_jobs AS (
    {target_jobs}
), current_skills AS (
    SELECT unnest(?::VARCHAR[]) AS skill_id
), request_parameters AS (
    SELECT ?::DOUBLE AS match_threshold
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
), baseline AS (
    SELECT
        (SELECT count(*) FROM target_jobs)::BIGINT AS target_job_count,
        count(*)::BIGINT AS sample_size,
        avg(current_fit) AS current_average_fit,
        count(*) FILTER (
            WHERE current_fit >= request_parameters.match_threshold
        )::DOUBLE / nullif(count(*), 0) AS current_threshold_coverage,
        max(target_jobs.published_at) AS latest_posted_date,
        count(target_jobs.published_at)::DOUBLE / nullif(count(*), 0) AS posting_date_coverage
    FROM job_fit
    INNER JOIN target_jobs USING (canonical_job_id)
    CROSS JOIN request_parameters
), candidate_impacts AS (
    SELECT
        job_skill_pairs.skill_id,
        sum(1.0 / job_fit.required_skill_count)::DOUBLE
            / nullif((SELECT sample_size FROM baseline), 0) AS average_fit_gain,
        count(*) FILTER (
            WHERE job_fit.current_fit < request_parameters.match_threshold
              AND (job_fit.matched_skill_count + 1)::DOUBLE
                  / job_fit.required_skill_count >= request_parameters.match_threshold
        )::BIGINT AS jobs_crossing_threshold
    FROM job_skill_pairs
    INNER JOIN job_fit USING (canonical_job_id)
    CROSS JOIN request_parameters
    WHERE NOT EXISTS (
        SELECT 1 FROM current_skills
        WHERE current_skills.skill_id = job_skill_pairs.skill_id
    )
    GROUP BY job_skill_pairs.skill_id
)
SELECT
    baseline.target_job_count,
    baseline.sample_size,
    baseline.target_job_count - baseline.sample_size AS jobs_without_extracted_skills,
    baseline.current_average_fit,
    baseline.current_threshold_coverage,
    baseline.latest_posted_date,
    baseline.posting_date_coverage,
    candidate_impacts.skill_id,
    skills.canonical_name,
    skills.category,
    baseline.current_average_fit + candidate_impacts.average_fit_gain AS new_average_fit,
    candidate_impacts.average_fit_gain,
    baseline.current_threshold_coverage
        + candidate_impacts.jobs_crossing_threshold::DOUBLE
          / nullif(baseline.sample_size, 0) AS new_threshold_coverage,
    candidate_impacts.jobs_crossing_threshold::DOUBLE
        / nullif(baseline.sample_size, 0) AS threshold_coverage_gain,
    candidate_impacts.jobs_crossing_threshold
FROM baseline
LEFT JOIN candidate_impacts ON TRUE
LEFT JOIN skills USING (skill_id)
ORDER BY
    threshold_coverage_gain DESC NULLS LAST,
    average_fit_gain DESC NULLS LAST,
    candidate_impacts.skill_id;
