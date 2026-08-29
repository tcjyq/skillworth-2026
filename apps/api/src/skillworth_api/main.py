from __future__ import annotations

import logging
from time import perf_counter
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from skillworth_analytics import (
    AnalyticsFilters,
    LearningOptimizerRequest,
    LearningOptimizerResult,
    OpportunityRequest,
    PersonalSkillOpportunityResult,
)
from skillworth_analytics.advanced import AdjustedSalaryAssociationRecord, SkillTrendRecord, SkillTrendResult
from skillworth_analytics.analytics import SalaryBySkillRecord, SkillDemandResult

from .schemas import (
    DataQualityResponse,
    ChinaSkillWorthSummaryResponse,
    ChinaSkillWorthQuery,
    ChinaSkillRelationsQuery,
    ChinaSkillRelationsResponse,
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    MarketQuery,
    MarketSummaryResponse,
    RelatedSkillsResponse,
    RoleDetailResponse,
    RolesResponse,
    SourcesResponse,
    SkillDetailResponse,
    SkillSalaryResponse,
)
from .service import ApiService
from .settings import ApiSettings
from .production_safe import ProductionSafeApiService


LOGGER = logging.getLogger("skillworth.api")
ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    settings = settings or ApiSettings.from_environment()
    app = FastAPI(
        title="SkillWorth Live API",
        version=settings.service_version,
        description="Read-only service layer over reproducible SkillWorth analytics. No endpoint recomputes statistical methodology.",
        openapi_tags=[
            {"name": "system", "description": "Service health and data availability."},
            {"name": "market", "description": "Market metrics produced by the analytics module."},
            {"name": "skills", "description": "Skill demand, trend, salary association, and network outputs."},
            {"name": "portfolio", "description": "Personal Skill Coverage and learning optimization; not employment probability."},
        ],
    )
    app.state.service = (
        ProductionSafeApiService(settings)
        if settings.data_mode == "production_safe"
        else ApiService(settings)
    )

    @app.middleware("http")
    async def request_observability(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{(perf_counter() - started) * 1000:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-SkillWorth-Market-Scope"] = settings.market_scope
        response.headers["X-SkillWorth-Source-Role"] = settings.source_role
        response.headers["X-SkillWorth-Snapshot"] = settings.snapshot
        LOGGER.info("api_request method=%s path=%s status=%s request_id=%s", request.method, request.url.path, response.status_code, request_id)
        return response

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request could not be completed"
        return _error_response(exc.status_code, "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "REQUEST_ERROR", detail)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = tuple({"location": list(error["loc"]), "message": error["msg"], "type": error["type"]} for error in exc.errors())
        return _error_response(422, "VALIDATION_ERROR", "Request validation failed", details)

    @app.exception_handler(FileNotFoundError)
    async def unavailable_handler(request: Request, _: FileNotFoundError) -> JSONResponse:
        LOGGER.warning("api_data_unavailable path=%s", request.url.path)
        return _error_response(503, "DATA_UNAVAILABLE", "Required analytical data is unavailable")

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        return _error_response(422, "VALIDATION_ERROR", str(exc))

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health(service: ApiService = Depends(_service)) -> HealthResponse:
        return HealthResponse(status="ok", service_version=service.settings.service_version, warehouse_available=service.data_available)

    @app.get("/market/summary", response_model=MarketSummaryResponse, responses=ERROR_RESPONSES, tags=["market"])
    def market_summary(response: Response, filters: MarketQuery = Depends(_market_query), service: ApiService = Depends(_service)) -> MarketSummaryResponse:
        return _cached(response, service, "market_summary", filters.to_filters(), lambda: service.market_summary(filters.to_filters()))

    @app.get("/market/trends", response_model=SkillTrendResult, responses=ERROR_RESPONSES, tags=["market"])
    def market_trends(response: Response, filters: MarketQuery = Depends(_market_query), service: ApiService = Depends(_service)) -> SkillTrendResult:
        return _cached(response, service, "market_trends", filters.to_filters(), lambda: service.market_trends(filters.to_filters()))

    @app.get("/market/china-skillworth", response_model=ChinaSkillWorthSummaryResponse, responses=ERROR_RESPONSES, tags=["market"])
    def china_skillworth(
        response: Response,
        query: ChinaSkillWorthQuery = Depends(),
        service: ApiService = Depends(_service),
    ) -> ChinaSkillWorthSummaryResponse:
        return _cached(
            response,
            service,
            f"china_skillworth:{query.model_dump_json()}",
            None,
            lambda: service.china_skillworth_summary(query),
        )

    @app.get(
        "/market/china-skill-relations",
        response_model=ChinaSkillRelationsResponse,
        responses=ERROR_RESPONSES,
        tags=["market"],
    )
    def china_skill_relations(
        response: Response,
        query: ChinaSkillRelationsQuery = Depends(),
        service: ApiService = Depends(_service),
    ) -> ChinaSkillRelationsResponse:
        return _cached(
            response,
            service,
            f"china_skill_relations:{query.model_dump_json()}",
            None,
            lambda: service.china_skill_relations(query),
        )

    @app.get("/skills", response_model=SkillDemandResult, responses=ERROR_RESPONSES, tags=["skills"])
    def skills(response: Response, filters: MarketQuery = Depends(_market_query), service: ApiService = Depends(_service)) -> SkillDemandResult:
        return _cached(response, service, "skills", filters.to_filters(), lambda: service.skill_demand(filters.to_filters()))

    @app.get("/skills/{skill_id}", response_model=SkillDetailResponse, responses=ERROR_RESPONSES, tags=["skills"])
    def skill_detail(skill_id: str, response: Response, filters: MarketQuery = Depends(_market_query), service: ApiService = Depends(_service)) -> SkillDetailResponse:
        result = _cached(response, service, f"skill:{skill_id}", filters.to_filters(), lambda: service.skill_detail(skill_id, filters.to_filters()))
        return _require(result, f"Unknown skill_id: {skill_id}")

    @app.get("/skills/{skill_id}/trend", response_model=SkillTrendRecord | None, responses=ERROR_RESPONSES, tags=["skills"])
    def skill_trend(skill_id: str, response: Response, filters: MarketQuery = Depends(_market_query), service: ApiService = Depends(_service)) -> SkillTrendRecord | None:
        result = _cached(response, service, f"skill_trend:{skill_id}", filters.to_filters(), lambda: service.skill_trend(skill_id, filters.to_filters()))
        return result

    @app.get("/skills/{skill_id}/salary", response_model=SkillSalaryResponse, responses=ERROR_RESPONSES, tags=["skills"])
    def skill_salary(skill_id: str, response: Response, filters: MarketQuery = Depends(_market_query), service: ApiService = Depends(_service)) -> SkillSalaryResponse:
        result = _cached(response, service, f"skill_salary:{skill_id}", filters.to_filters(), lambda: service.skill_salary(skill_id, filters.to_filters()))
        salary, association = _require(result, f"Unknown skill_id: {skill_id}")
        return SkillSalaryResponse(salary_distribution=salary, adjusted_salary_association=association)

    @app.get("/skills/{skill_id}/related", response_model=RelatedSkillsResponse, responses=ERROR_RESPONSES, tags=["skills"])
    def related_skills(skill_id: str, response: Response, service: ApiService = Depends(_service)) -> RelatedSkillsResponse:
        result = _cached(response, service, f"related:{skill_id}", None, lambda: service.related_skills(skill_id))
        return _require(result, f"Unknown skill_id: {skill_id}")

    @app.get("/roles", response_model=RolesResponse, responses=ERROR_RESPONSES, tags=["market"])
    def roles(response: Response, service: ApiService = Depends(_service)) -> RolesResponse:
        return _cached(response, service, "roles", None, service.roles)

    @app.get("/roles/{role_id}", response_model=RoleDetailResponse, responses=ERROR_RESPONSES, tags=["market"])
    def role_detail(role_id: str, response: Response, service: ApiService = Depends(_service)) -> RoleDetailResponse:
        def loader() -> RoleDetailResponse | None:
            role = service.role(role_id)
            if role is None:
                return None
            return RoleDetailResponse(role=role, skill_demand=service.role_skill_demand(role_id))
        return _require(_cached(response, service, f"role:{role_id}", None, loader), f"Unknown role_id: {role_id}")

    @app.get("/sources", response_model=SourcesResponse, responses=ERROR_RESPONSES, tags=["market"])
    def sources(response: Response, service: ApiService = Depends(_service)) -> SourcesResponse:
        return _cached(response, service, "sources", None, service.sources)

    @app.get("/data-quality", response_model=DataQualityResponse, responses=ERROR_RESPONSES, tags=["system"])
    def data_quality(response: Response, service: ApiService = Depends(_service)) -> DataQualityResponse:
        return _cached(response, service, "data_quality", None, service.data_quality)

    @app.post("/portfolio/analyze", response_model=PersonalSkillOpportunityResult, responses=ERROR_RESPONSES, tags=["portfolio"])
    def portfolio_analyze(request: OpportunityRequest, service: ApiService = Depends(_service)) -> PersonalSkillOpportunityResult:
        return service.analyze_portfolio(request)

    @app.post("/portfolio/optimize", response_model=LearningOptimizerResult, responses=ERROR_RESPONSES, tags=["portfolio"])
    def portfolio_optimize(request: LearningOptimizerRequest, service: ApiService = Depends(_service)) -> LearningOptimizerResult:
        return service.optimize_portfolio(request)

    return app


def _service(request: Request) -> ApiService | ProductionSafeApiService:
    return request.app.state.service


def _market_query(
    role_id: Annotated[str | None, Query()] = None,
    city_code: Annotated[str | None, Query()] = None,
    experience_band: Annotated[str | None, Query()] = None,
    education_band: Annotated[str | None, Query()] = None,
    source_id: Annotated[list[str] | None, Query()] = None,
    published_from: Annotated[str | None, Query()] = None,
    published_to: Annotated[str | None, Query()] = None,
    market_scope: Annotated[Literal["target", "all"], Query()] = "target",
    source_scope: Annotated[Literal["core", "all"], Query()] = "core",
) -> MarketQuery:
    return MarketQuery(
        role_id=role_id,
        city_code=city_code,
        experience_band=experience_band,
        education_band=education_band,
        source_id=tuple(source_id or ()),
        published_from=published_from,
        published_to=published_to,
        market_scope=market_scope,
        source_scope=source_scope,
    )


def _cached(response: Response, service: ApiService | ProductionSafeApiService, name: str, filters: AnalyticsFilters | None, loader):
    suffix = filters.model_dump_json() if filters is not None else ""
    result = service.cached(f"{name}:{suffix}", loader)
    response.headers["X-Cache"] = "HIT" if result.hit else "MISS"
    return result.value


def _require(value, message: str):
    if value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    return value


def _error_response(status_code: int, code: str, message: str, details: tuple[dict, ...] = ()) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=ErrorResponse(error=ErrorBody(code=code, message=message, details=details)).model_dump(mode="json"))


app = create_app()
