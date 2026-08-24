from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
from typing import Protocol
from zipfile import BadZipFile, ZipFile

import polars as pl


CONNECTOR_VERSION = "1.5.0"


@dataclass(frozen=True, slots=True)
class ConnectorReadResult:
    frame: pl.DataFrame
    raw_record_count: int
    accepted_record_count: int
    rejected_record_count: int
    warnings: tuple[str, ...] = ()


def _local_file(path: Path, expected_suffix: str, label: str) -> Path:
    value = str(path)
    if value.lower().startswith(("http:", "https:")) or "://" in value or path.suffix.lower() != expected_suffix:
        raise ValueError(f"{label} connector accepts only a local {expected_suffix.lstrip('.').upper()} file")
    if not path.is_file():
        raise FileNotFoundError(f"Source artifact does not exist: {path}")
    return path


class Connector(Protocol):
    def read(self, path: Path) -> pl.DataFrame: ...

    def read_result(self, path: Path) -> ConnectorReadResult: ...


class AuthorizedHttpConnector(Protocol):
    def fetch(self) -> pl.DataFrame: ...


class CsvConnector:
    def read(self, path: Path) -> pl.DataFrame:
        return self.read_result(path).frame

    def read_result(self, path: Path) -> ConnectorReadResult:
        frame = pl.read_csv(_local_file(path, ".csv", "CSV"), infer_schema=False)
        return ConnectorReadResult(frame, frame.height, frame.height, 0)


class ParquetConnector:
    def read(self, path: Path) -> pl.DataFrame:
        return self.read_result(path).frame

    def read_result(self, path: Path) -> ConnectorReadResult:
        frame = pl.read_parquet(_local_file(path, ".parquet", "Parquet"))
        return ConnectorReadResult(frame, frame.height, frame.height, 0)


class ManualExportConnector:
    def read(self, path: Path) -> pl.DataFrame:
        return self.read_result(path).frame

    def read_result(self, path: Path) -> ConnectorReadResult:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return CsvConnector().read_result(path)
        if suffix == ".parquet":
            return ParquetConnector().read_result(path)
        raise ValueError(f"Unsupported manual export format: {path.suffix or '<none>'}")


class PublicDatasetConnector(ManualExportConnector):
    pass


class TechsaleratorChinaJobsConnector:
    """Maps the licensed Kaggle v1 artifact without inferring absent source fields."""

    EXPECTED_COLUMNS = {
        "Website Domain",
        "Ticker",
        "Job Opening Title",
        "Job Opening URL",
        "First Seen At",
        "Last Seen At",
        "Location",
        "Location Data",
        "Category",
        "Seniority",
        "Keywords",
        "Description",
        "Salary",
        "Salary Data",
        "Contract Types",
        "Job Status",
        "Job Language",
        "Job Last Processed At",
        "O*NET Code",
        "O*NET Family",
        "O*NET Occupation Name",
    }

    def read(self, path: Path) -> pl.DataFrame:
        return self.read_result(path).frame

    def read_result(self, path: Path) -> ConnectorReadResult:
        frame = self._read_artifact(path)
        missing = self.EXPECTED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"Techsalerator dataset is missing columns: {sorted(missing)}")
        raw_record_count = frame.height
        mapped = frame.with_columns(
            pl.col("Location Data").str.json_path_match("$[0].country").alias("_dataset_country"),
            pl.col("Location Data").str.json_path_match("$[0].city").alias("_dataset_city"),
        ).filter(pl.col("_dataset_country") == "China")
        mapped = mapped.with_columns(
            pl.col("Job Opening URL").alias("source_job_id"),
            pl.col("Job Opening URL").alias("source_url"),
            pl.col("Website Domain").alias("company_name"),
            pl.col("Job Opening Title").alias("job_title"),
            pl.col("_dataset_city").alias("city"),
            pl.lit(None, dtype=pl.String).alias("education"),
            pl.lit(None, dtype=pl.String).alias("experience"),
            pl.col("Salary").alias("salary"),
            pl.col("First Seen At").alias("published_at"),
            pl.col("Description").alias("job_description"),
        )
        return ConnectorReadResult(
            frame=mapped,
            raw_record_count=raw_record_count,
            accepted_record_count=mapped.height,
            rejected_record_count=raw_record_count - mapped.height,
            warnings=(
                "artifact_decoded_as_utf8_lossy_due_to_invalid_source_bytes",
                "only_rows_with_structured_country_equal_to_china_are_in_scope",
                "company_name_is_mapped_from_corporate_website_domain",
            ),
        )

    @staticmethod
    def _read_artifact(path: Path) -> pl.DataFrame:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            local_path = _local_file(path, ".csv", "Techsalerator CSV")
            return pl.read_csv(local_path, infer_schema=False, encoding="utf8-lossy")
        if suffix != ".zip":
            raise ValueError("Techsalerator connector accepts only a local ZIP or CSV file")
        local_path = path.resolve()
        if not local_path.is_file():
            raise FileNotFoundError(f"Source artifact does not exist: {local_path}")
        try:
            with ZipFile(local_path) as archive:
                matches = [name for name in archive.namelist() if Path(name).name == "Job Posting.csv"]
                if len(matches) != 1:
                    raise ValueError("Techsalerator ZIP must contain exactly one Job Posting.csv")
                payload = archive.read(matches[0])
        except BadZipFile as error:
            raise ValueError("Techsalerator artifact is not a valid ZIP file") from error
        return pl.read_csv(BytesIO(payload), infer_schema=False, encoding="utf8-lossy")


class HkCsbGovernmentVacanciesConnector:
    """Map the official DATA.GOV.HK government vacancy JSON snapshot.

    HKD pay is retained as native-source evidence. It is deliberately not
    converted into the warehouse's CNY monthly salary measure here.
    """

    DOWNLOAD_URL = "https://www.csb.gov.hk/datagovhk/gov-vacancies/gov-job-vacancies-en.json"
    REQUIRED_FIELDS = {
        "jobid", "jobname", "deptnamejve", "duties", "entreq", "pubdate", "entrypay"
    }

    def read(self, path: Path) -> pl.DataFrame:
        return self.read_result(path).frame

    def read_result(self, path: Path) -> ConnectorReadResult:
        local_path = _local_file(path, ".json", "HK CSB government vacancies JSON")
        payload = json.loads(local_path.read_text(encoding="utf-8-sig"))
        common = payload.get("common") if isinstance(payload, dict) else None
        if isinstance(common, list):
            merged_common: dict[str, object] = {}
            for item in common:
                if isinstance(item, dict):
                    merged_common.update(item)
            common = merged_common
        vacancies = common.get("vacancies") if isinstance(common, dict) else None
        if not isinstance(vacancies, list):
            raise ValueError("HK CSB dataset must contain common.vacancies as a list")
        rows: list[dict[str, object]] = []
        rejected = 0
        for vacancy in vacancies:
            if not isinstance(vacancy, dict) or not self.REQUIRED_FIELDS.issubset(vacancy):
                rejected += 1
                continue
            job_id = str(vacancy["jobid"]).strip()
            title = str(vacancy.get("jobname") or "").strip()
            company = str(vacancy.get("deptnamejve") or "").strip()
            if not job_id or not title or not company:
                rejected += 1
                continue
            rows.append(
                {
                    **vacancy,
                    "source_job_id": job_id,
                    "source_url": self.DOWNLOAD_URL,
                    "company_name": company,
                    "job_title": title,
                    "city": "Hong Kong",
                    "education": self._education(vacancy.get("academic")),
                    "experience": self._experience(vacancy.get("expfrom"), vacancy.get("expto")),
                    "salary": self._text(vacancy.get("entrypay")),
                    "salary_currency": self._currency(vacancy),
                    "salary_native_min_monthly": self._number(vacancy.get("minpaym")),
                    "salary_native_min_hourly": self._number(vacancy.get("minpayh")),
                    "salary_native_min_daily": self._number(vacancy.get("minpayd")),
                    "published_at": self._text(vacancy.get("pubdate")),
                    "job_description": self._description(vacancy),
                    "source_snapshot_at": self._text(common.get("timestamp")),
                }
            )
        frame = pl.from_dicts(rows, infer_schema_length=None) if rows else pl.DataFrame()
        return ConnectorReadResult(
            frame=frame,
            raw_record_count=len(vacancies),
            accepted_record_count=len(rows),
            rejected_record_count=rejected,
            warnings=(
                "public_sector_hong_kong_composition_is_not_representative_of_mainland_technical_hiring",
                "hkd_salary_is_preserved_as_native_evidence_and_not_mixed_with_cny_analytics",
                "source_url_points_to_the_official_snapshot_resource_and_source_job_id_identifies_the_record",
            ),
        )

    @staticmethod
    def _text(value: object) -> str | None:
        text = "" if value is None else str(value).strip()
        return text or None

    @staticmethod
    def _number(value: object) -> float | None:
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _education(cls, value: object) -> str | None:
        entries = value if isinstance(value, list) else []
        text = " ".join(str(item) for item in entries).casefold()
        for pattern, normalized in (
            ("master or higher", "硕士"),
            ("post-graduate", "硕士"),
            ("honours degree", "本科"),
            ("degree", "本科"),
            ("associate degree", "大专"),
            ("higher diploma", "大专"),
            ("secondary", "高中"),
            ("hkdsee", "高中"),
            ("hkcee", "高中"),
        ):
            if pattern in text:
                return normalized
        return None

    @staticmethod
    def _experience(minimum: object, maximum: object) -> str | None:
        try:
            minimum_value = float(minimum)
        except (TypeError, ValueError):
            return None
        if maximum is not None:
            try:
                maximum_value = float(maximum)
            except (TypeError, ValueError):
                maximum_value = None
            if maximum_value is not None and maximum_value >= minimum_value:
                return f"{minimum_value:g}-{maximum_value:g}年"
        if minimum_value <= 0:
            return "不限"
        return f"{minimum_value:g}年以上"

    @classmethod
    def _currency(cls, vacancy: dict[str, object]) -> str | None:
        values = " ".join(
            cls._text(vacancy.get(field)) or "" for field in ("ccym", "ccyh", "ccyd", "entrypay")
        ).upper()
        return "HKD" if "HK" in values or "$" in values else None

    @classmethod
    def _description(cls, vacancy: dict[str, object]) -> str | None:
        sections = []
        for label, field in (("Duties", "duties"), ("Entry requirements", "entreq"), ("Notes", "ernotes")):
            value = cls._text(vacancy.get(field))
            if value:
                sections.append(f"{label}:\n{value}")
        return "\n\n".join(sections) or None


class NcssPublicExportConnector:
    """Map a local NCSS export after independent data-permission review.

    The connector deliberately contains no HTTP client. The source registry
    blocks pipeline import until the data-use status is changed to reviewed.
    """

    REQUIRED_FIELDS = {"source_job_id", "job_name", "company_name"}

    def read(self, path: Path) -> pl.DataFrame:
        return self.read_result(path).frame

    def read_result(self, path: Path) -> ConnectorReadResult:
        value = str(path)
        suffix = path.suffix.lower()
        if value.lower().startswith(("http:", "https:")) or "://" in value:
            raise ValueError("NCSS connector accepts only a local authorized export")
        if suffix not in {".csv", ".jsonl"}:
            raise ValueError("NCSS connector accepts only a local CSV or JSONL export")
        if not path.is_file():
            raise FileNotFoundError(f"Source artifact does not exist: {path}")

        if suffix == ".csv":
            raw_rows = pl.read_csv(path, infer_schema=False).to_dicts()
        else:
            raw_rows = []
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8-sig").splitlines(), start=1
            ):
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError(f"NCSS JSONL line {line_number} must be an object")
                raw_rows.append(payload)

        mapped_rows: list[dict[str, object]] = []
        rejected = 0
        for row in raw_rows:
            if any(not self._text(row.get(field)) for field in self.REQUIRED_FIELDS):
                rejected += 1
                continue
            description = self._text(row.get("job_description"))
            responsibility = self._text(row.get("job_responsibility"))
            requirements = self._text(row.get("job_requirement"))
            unique_sections = list(
                dict.fromkeys(
                    section
                    for section in (description, responsibility, requirements)
                    if section
                )
            )
            mapped_rows.append(
                {
                    **row,
                    "source_job_id": self._text(row.get("source_job_id")),
                    "source_url": self._text(row.get("source_url")),
                    "company_name": self._text(row.get("company_name")),
                    "job_title": self._text(row.get("job_name")),
                    "city": self._text(row.get("city")),
                    "education": self._text(row.get("education_text")),
                    "experience": self._text(row.get("experience_text")),
                    "salary": self._text(row.get("salary_text")),
                    "published_at": self._text(row.get("publish_time")),
                    "description": description,
                    "responsibility": responsibility,
                    "requirements": requirements,
                    "job_description": "\n".join(unique_sections) or None,
                }
            )
        frame = pl.from_dicts(mapped_rows, infer_schema_length=None) if mapped_rows else pl.DataFrame()
        return ConnectorReadResult(
            frame=frame,
            raw_record_count=len(raw_rows),
            accepted_record_count=len(mapped_rows),
            rejected_record_count=rejected,
            warnings=(
                "local_export_only_no_network_collection_implemented",
                "data_use_permission_must_be_reviewed_before_pipeline_import",
                "description_responsibility_and_requirements_are_combined_for_skill_extraction",
            ),
        )

    @staticmethod
    def _text(value: object) -> str | None:
        text = "" if value is None else str(value).strip()
        return text or None


class NextGigJune2026Connector:
    """Map the pinned NextGig June 2026 Parquet snapshot.

    NextGig contains globally scoped, enriched records. The source's generated
    description summary and derived geography are explicitly labelled. Native
    salaries are normalized only across time units and never across currencies.
    """

    REQUIRED_COLUMNS = {
        "title", "company_name", "ats_name", "skills_required",
        "salary_min", "salary_max", "salary_currency", "salary_rate_unit",
        "city", "country", "date_posted", "job_description",
    }
    SNAPSHOT_CUTOFF = date(2026, 6, 6)
    MONTHLY_FACTORS = {
        "year": 1 / 12,
        "annual": 1 / 12,
        "annually": 1 / 12,
        "yearly": 1 / 12,
        "yr": 1 / 12,
        "month": 1.0,
        "monthly": 1.0,
        "week": 52 / 12,
        "weekly": 52 / 12,
        "day": 260 / 12,
        "daily": 260 / 12,
        "hour": 2080 / 12,
        "hourly": 2080 / 12,
        "hr": 2080 / 12,
    }

    def read(self, path: Path) -> pl.DataFrame:
        return self.read_result(path).frame

    def read_result(self, path: Path) -> ConnectorReadResult:
        frame = pl.read_parquet(_local_file(path, ".parquet", "NextGig Parquet"))
        missing = self.REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"NextGig dataset is missing columns: {sorted(missing)}")
        rows: list[dict[str, object]] = []
        rejected = 0
        for row_index, row in enumerate(frame.iter_rows(named=True)):
            title = self._text(row.get("title"))
            company = self._text(row.get("company_name"))
            if not title or not company:
                rejected += 1
                continue
            minimum, maximum, midpoint, method = self._monthly_salary(
                row.get("salary_min"), row.get("salary_max"), row.get("salary_rate_unit")
            )
            evidence_sections = [
                self._text(row.get("responsibilities")),
                self._text(row.get("minimum_qualifications")),
                self._text(row.get("preferred_qualifications")),
            ]
            dataset_row_index = row.get("_nextgig_dataset_row_index", row_index)
            identity = json.dumps(
                [title, company, row.get("city"), row.get("country"), row.get("ats_name"), dataset_row_index],
                ensure_ascii=False,
                default=str,
            )
            source_job_id = f"nextgig:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"
            rows.append(
                {
                    **row,
                    "source_job_id": source_job_id,
                    "source_url": None,
                    "job_title": title,
                    "company_name": company,
                    "city": self._text(row.get("city")),
                    "country_raw": self._text(row.get("country")),
                    "education": self._text(row.get("education_level")),
                    "experience": self._text(row.get("experience_level")),
                    "salary": None,
                    "salary_raw_structured": self._salary_raw(row),
                    "salary_currency": self._text(row.get("salary_currency")),
                    "salary_currency_original": self._text(row.get("salary_currency")),
                    "salary_rate_unit_original": self._text(row.get("salary_rate_unit")),
                    "salary_min_normalized": minimum,
                    "salary_max_normalized": maximum,
                    "salary_mid_normalized": midpoint,
                    "salary_normalization_method": method,
                    "fx_rate": None,
                    "fx_rate_date": None,
                    "fx_source": None,
                    "published_at": self._date(row.get("date_posted")),
                    "source_job_description": self._text(row.get("job_description")),
                    "job_description": "\n\n".join(value for value in evidence_sections if value) or None,
                    "description_type": "llm_summary",
                    "skill_evidence_source": "source_structured_enrichment_and_qualification_text",
                    "structured_skills_raw": self._json_value(row.get("skills_required")),
                    "geography_source": "derived",
                }
            )
        mapped = pl.from_dicts(rows, infer_schema_length=None) if rows else pl.DataFrame()
        return ConnectorReadResult(
            frame=mapped,
            raw_record_count=frame.height,
            accepted_record_count=mapped.height,
            rejected_record_count=rejected,
            warnings=(
                "global_dataset_not_china_market_representative",
                "job_description_is_llm_summary_and_excluded_from_rule_extraction_text",
                "geography_is_source_derived",
                "native_salary_is_not_currency_converted_or_mixed_with_cny_analytics",
                "source_application_urls_and_original_upstream_job_ids_are_unavailable",
            ),
        )

    @staticmethod
    def _text(value: object) -> str | None:
        text = "" if value is None else str(value).strip()
        return text or None

    @classmethod
    def _date(cls, value: object) -> str | None:
        text = cls._text(value)
        if not text or text == "MM/DD/YYYY":
            return None
        for pattern in ("%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(text[:10], pattern).date()
                if parsed > cls.SNAPSHOT_CUTOFF:
                    return None
                return parsed.isoformat()
            except ValueError:
                continue
        return None

    @classmethod
    def _monthly_salary(
        cls, minimum: object, maximum: object, rate_unit: object
    ) -> tuple[float | None, float | None, float | None, str]:
        try:
            low = float(minimum) if minimum is not None else None
            high = float(maximum) if maximum is not None else None
        except (TypeError, ValueError):
            return None, None, None, "invalid_numeric_salary"
        unit = (cls._text(rate_unit) or "").casefold()
        factor = cls.MONTHLY_FACTORS.get(unit)
        if factor is None:
            return None, None, None, "unsupported_or_missing_rate_unit"
        if low is not None and low <= 0 or high is not None and high <= 0:
            return None, None, None, "invalid_non_positive_salary"
        if low is not None and high is not None and low > high:
            return None, None, None, "invalid_salary_range"
        normalized_low = low * factor if low is not None else None
        normalized_high = high * factor if high is not None else None
        midpoint = (
            (normalized_low + normalized_high) / 2
            if normalized_low is not None and normalized_high is not None
            else normalized_low if normalized_low is not None else normalized_high
        )
        return normalized_low, normalized_high, midpoint, f"native_currency_monthly_from_{unit}"

    @classmethod
    def _salary_raw(cls, row: dict[str, object]) -> str | None:
        values = [row.get("salary_min"), row.get("salary_max")]
        if all(value is None for value in values):
            return None
        return json.dumps(
            {
                "min": row.get("salary_min"),
                "max": row.get("salary_max"),
                "currency": row.get("salary_currency"),
                "rate_unit": row.get("salary_rate_unit"),
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _json_value(value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip() or None
        return json.dumps(value, ensure_ascii=False, default=str)


def connector_for(name: str) -> Connector:
    if name == "freehire_public_api":
        from app.freehire import FreehirePublicApiConnector

        return FreehirePublicApiConnector()
    connectors: dict[str, Connector] = {
        "csv": CsvConnector(),
        "parquet": ParquetConnector(),
        "manual_export": ManualExportConnector(),
        "public_dataset": PublicDatasetConnector(),
        "techsalerator_china_jobs_v1": TechsaleratorChinaJobsConnector(),
        "hk_csb_gov_vacancies": HkCsbGovernmentVacanciesConnector(),
        "ncss_public_export": NcssPublicExportConnector(),
        "nextgig_june_2026": NextGigJune2026Connector(),
    }
    if name == "external_benchmark":
        raise ValueError("External benchmarks use the isolated benchmark loader, not the jobs connector")
    if name == "authorized_http":
        raise NotImplementedError("AuthorizedHttpConnector requires a separately reviewed authorized implementation")
    try:
        return connectors[name]
    except KeyError as error:
        raise ValueError(f"Unsupported connector: {name}") from error
