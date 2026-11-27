"""FastAPI Routes for M06 — Business Intelligence (/api/v1/analytics/*).

Read-only analytical endpoints exposing executive KPIs, time-series trajectories,
geographical country splits, top/slow-moving SKU velocity rankings, and period-over-period
comparisons with strict GBP (UCI) vs. INR (operational) separation.
"""

from datetime import date
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.provenance import RequestProvenance, get_request_provenance
from app.repositories.analytics_repository import AnalyticsDataUnavailableError
from app.schemas.analytics import (
    AnalyticsComparisonsResponse,
    AnalyticsCountriesResponse,
    AnalyticsSkuRankingsResponse,
    AnalyticsSummaryResponse,
    AnalyticsTimeSeriesResponse,
    ComparisonPeriodType,
    GranularityType,
    SkuRankingOrder,
    SkuRankingSortBy,
    SourceOriginFilter,
)
from app.services.analytics_service import AnalyticsValidationError, analytics_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["M06 Business Intelligence"])


def _handle_analytics_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, AnalyticsValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, AnalyticsDataUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    logger.error("Unexpected M06 analytics failure: %s", exc, exc_info=True)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred while computing business intelligence metrics.",
    )


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Global Business Intelligence KPI Summary",
    description=(
        "Aggregates gross/net revenue, gross/net units sold, unique order count, active SKU count, "
        "return totals, cancellation totals, and average order value strictly separated by "
        "source_origin (GBP UCI baseline vs. INR live operational records)."
    ),
)
def get_analytics_summary(
    source_origin: SourceOriginFilter = Query(default="all", description="Filter by 'uci_historical', 'operational', or 'all'"),
    start_date: Optional[date] = Query(default=None, description="Inclusive start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(default=None, description="Inclusive end date (YYYY-MM-DD)"),
    country: Optional[str] = Query(default=None, description="Exact country filter (case-insensitive)"),
    category_id: Optional[int] = Query(default=None, ge=1, description="Optional operational category ID filter"),
    stock_code: Optional[str] = Query(default=None, description="Optional product SKU filter"),
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> AnalyticsSummaryResponse:
    try:
        return analytics_service.get_summary(
            provenance=provenance,
            source_origin=source_origin,
            start_date=start_date,
            end_date=end_date,
            country=country,
            category_id=category_id,
            stock_code=stock_code,
        )
    except Exception as exc:
        raise _handle_analytics_errors(exc) from exc


@router.get(
    "/timeseries",
    response_model=AnalyticsTimeSeriesResponse,
    summary="Time-Series Sales Revenue & Unit Velocity",
    description="Returns daily, ISO-weekly, or monthly revenue and unit trajectories separated by source_origin and currency.",
)
def get_analytics_timeseries(
    source_origin: SourceOriginFilter = Query(default="all"),
    granularity: GranularityType = Query(default="month", description="Aggregation bucket: day, week, or month"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    country: Optional[str] = Query(default=None),
    category_id: Optional[int] = Query(default=None, ge=1),
    stock_code: Optional[str] = Query(default=None),
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> AnalyticsTimeSeriesResponse:
    try:
        return analytics_service.get_timeseries(
            provenance=provenance,
            source_origin=source_origin,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date,
            country=country,
            category_id=category_id,
            stock_code=stock_code,
        )
    except Exception as exc:
        raise _handle_analytics_errors(exc) from exc


@router.get(
    "/countries",
    response_model=AnalyticsCountriesResponse,
    summary="Geographical Country-Level Sales Breakdown",
    description="Aggregates order volume, units, gross/net revenue, and revenue share % across countries.",
)
def get_analytics_countries(
    source_origin: SourceOriginFilter = Query(default="all"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    category_id: Optional[int] = Query(default=None, ge=1),
    stock_code: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None, ge=1, le=200, description="Optional cap on top countries returned"),
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> AnalyticsCountriesResponse:
    try:
        return analytics_service.get_countries(
            provenance=provenance,
            source_origin=source_origin,
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            stock_code=stock_code,
            limit=limit,
        )
    except Exception as exc:
        raise _handle_analytics_errors(exc) from exc


@router.get(
    "/sku-rankings",
    response_model=AnalyticsSkuRankingsResponse,
    summary="Top-Performing and Slow-Moving SKU Leaderboards",
    description=(
        "Returns paginated SKU velocity tables with Gross, Returns, Cancellations, and Net metrics. "
        "Supports order='top' and order='slowest' (distinct from M08 lifecycle classification)."
    ),
)
def get_analytics_sku_rankings(
    source_origin: SourceOriginFilter = Query(default="all"),
    order: SkuRankingOrder = Query(default="top", description="Ranking direction: 'top' or 'slowest'"),
    sort_by: SkuRankingSortBy = Query(default="revenue", description="Primary metric: 'revenue', 'quantity', or 'order_count'"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    country: Optional[str] = Query(default=None),
    category_id: Optional[int] = Query(default=None, ge=1),
    stock_code: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> AnalyticsSkuRankingsResponse:
    try:
        return analytics_service.get_sku_rankings(
            provenance=provenance,
            source_origin=source_origin,
            order=order,
            sort_by=sort_by,
            start_date=start_date,
            end_date=end_date,
            country=country,
            category_id=category_id,
            stock_code=stock_code,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        raise _handle_analytics_errors(exc) from exc


@router.get(
    "/comparisons",
    response_model=AnalyticsComparisonsResponse,
    summary="Period-over-Period Variance Comparisons (MoM / QoQ / YoY)",
    description=(
        "Compares adjacent monthly, quarterly, or year-over-year performance windows. "
        "Safely returns null percentage deltas when prior baseline equals zero."
    ),
)
def get_analytics_comparisons(
    source_origin: SourceOriginFilter = Query(default="all"),
    period_type: ComparisonPeriodType = Query(default="mom", description="Comparison cadence: 'mom', 'qoq', or 'yoy'"),
    reference_date: Optional[date] = Query(default=None, description="Anchor date for comparison window (defaults to latest available date)"),
    country: Optional[str] = Query(default=None),
    category_id: Optional[int] = Query(default=None, ge=1),
    stock_code: Optional[str] = Query(default=None),
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> AnalyticsComparisonsResponse:
    try:
        return analytics_service.get_comparisons(
            provenance=provenance,
            source_origin=source_origin,
            period_type=period_type,
            reference_date=reference_date,
            country=country,
            category_id=category_id,
            stock_code=stock_code,
        )
    except Exception as exc:
        raise _handle_analytics_errors(exc) from exc
