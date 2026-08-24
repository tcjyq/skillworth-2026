import type { ChinaSkillWorthRecord, ChinaSkillWorthResponse, RelatedSkill, RelatedSkills } from "@/lib/api/types";

export type FinalFindings = {
  frontier: ChinaSkillWorthRecord[];
  cpp: { demandRank: number; skillworthRank: number; learningHours: number; jobCount: number; companyCount: number };
  roles: Array<{ role: "DevOps" | "Data Engineer"; sampleSize: number; skills: Array<{ skill: string; globalRank: number; roleRank: number }> }>;
  synergy: {
    sampleSize: number;
    scale: { pair: "Python–SQL"; cooccurrence: number; jaccard: number; pmi: number };
    affinity: Array<{ pair: "NumPy–Pandas" | "Grafana–Prometheus"; cooccurrence: number; jaccard: number; pmi: number }>;
  };
  robustCore: Array<{ skill: string; min: number; max: number }>;
};

export type FinalFindingSources = {
  global: ChinaSkillWorthResponse | null | undefined;
  devops: ChinaSkillWorthResponse | null | undefined;
  data: ChinaSkillWorthResponse | null | undefined;
  allActive: ChinaSkillWorthResponse | null | undefined;
  pythonRelated: RelatedSkills | null | undefined;
  numpyRelated: RelatedSkills | null | undefined;
  grafanaRelated: RelatedSkills | null | undefined;
};

const findSkill = (response: ChinaSkillWorthResponse, skill: string) => response.records.find((item) => item.skill === skill);
const findRelated = (response: RelatedSkills, skill: string) => response.records.find((item) => item.canonical_name === skill);

function demandRank(records: ChinaSkillWorthRecord[], target: ChinaSkillWorthRecord) {
  return 1 + records.filter((record) => record.job_count > target.job_count).length;
}

function requiredSkill(response: ChinaSkillWorthResponse, skill: string) {
  const found = findSkill(response, skill);
  return found?.skillworth_rank != null ? found : null;
}

function requiredRange(response: ChinaSkillWorthResponse, skill: string) {
  const found = requiredSkill(response, skill);
  return found?.sensitivity_rank_min != null && found.sensitivity_rank_max != null ? found : null;
}

function relatedEvidence(record: RelatedSkill) {
  return { cooccurrence: record.cooccurrence_count, jaccard: record.jaccard, pmi: record.pmi };
}

export function deriveFinalFindings(sources: FinalFindingSources): FinalFindings | null {
  const { global, devops, data, allActive, pythonRelated, numpyRelated, grafanaRelated } = sources;
  if (!global || !devops || !data || !allActive || !pythonRelated || !numpyRelated || !grafanaRelated) return null;

  const python = requiredRange(global, "Python");
  const sql = requiredRange(global, "SQL");
  const git = requiredRange(global, "Git");
  const docker = requiredRange(global, "Docker");
  const cpp = requiredSkill(global, "C++");
  const kubernetes = requiredSkill(global, "Kubernetes");
  const terraform = requiredSkill(global, "Terraform");
  const spark = requiredSkill(global, "Apache Spark");
  const kafka = requiredSkill(global, "Apache Kafka");
  const tableau = requiredRange(global, "Tableau");
  const rag = requiredRange(global, "RAG");
  const azure = requiredRange(global, "Azure");
  const devopsKubernetes = requiredSkill(devops, "Kubernetes");
  const devopsTerraform = requiredSkill(devops, "Terraform");
  const dataSpark = requiredSkill(data, "Apache Spark");
  const dataKafka = requiredSkill(data, "Apache Kafka");
  const pythonSql = findRelated(pythonRelated, "SQL");
  const numpyPandas = findRelated(numpyRelated, "Pandas");
  const grafanaPrometheus = findRelated(grafanaRelated, "Prometheus");

  if (!python || !sql || !git || !docker || !cpp || !kubernetes || !terraform || !spark || !kafka || !tableau || !rag || !azure || !devopsKubernetes || !devopsTerraform || !dataSpark || !dataKafka || !pythonSql || !numpyPandas || !grafanaPrometheus) return null;

  return {
    frontier: [python, sql, git],
    cpp: { demandRank: demandRank(global.records, cpp), skillworthRank: cpp.skillworth_rank!, learningHours: cpp.learning_hours_expected, jobCount: cpp.job_count, companyCount: cpp.company_count },
    roles: [
      { role: "DevOps", sampleSize: devops.job_count, skills: [{ skill: "Kubernetes", globalRank: kubernetes.skillworth_rank!, roleRank: devopsKubernetes.skillworth_rank! }, { skill: "Terraform", globalRank: terraform.skillworth_rank!, roleRank: devopsTerraform.skillworth_rank! }] },
      { role: "Data Engineer", sampleSize: data.job_count, skills: [{ skill: "Spark", globalRank: spark.skillworth_rank!, roleRank: dataSpark.skillworth_rank! }, { skill: "Kafka", globalRank: kafka.skillworth_rank!, roleRank: dataKafka.skillworth_rank! }] },
    ],
    synergy: {
      sampleSize: allActive.job_count,
      scale: { pair: "Python–SQL", ...relatedEvidence(pythonSql) },
      affinity: [{ pair: "NumPy–Pandas", ...relatedEvidence(numpyPandas) }, { pair: "Grafana–Prometheus", ...relatedEvidence(grafanaPrometheus) }],
    },
    robustCore: [python, sql, git, docker, tableau, rag, azure].map((record) => ({ skill: record.skill, min: record.sensitivity_rank_min!, max: record.sensitivity_rank_max! })),
  };
}
