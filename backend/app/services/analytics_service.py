"""Business Logic Service for M06 — Business Intelligence.

Computes read-only KPI summaries, daily/weekly/monthly time-series trajectories,
geographical country breakdowns, top/slow-moving SKU rankings, and MoM/QoQ/YoY
period comparisons with exact DECIMAL arithmetic and strict GBP (UCI) vs. INR
(operational) source separation per Technical Blueprint v2.2 & DDR-04.
"""

import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.core.provenance import RequestProvenance
from app.repositories.analytics_repository import (
    AnalyticsRepositoryProtocol,
    FIXED_POINT_SCALE,
    OperationalCatalogItem,
    analytics_repository,
    quantize_money,
    quantize_qty,
)
from app.schemas.analytics import (
    AnalyticsComparisonsResponse,
    AnalyticsCountriesResponse,
    AnalyticsSkuRankingsResponse,
    AnalyticsSummaryResponse,
    AnalyticsTimeSeriesResponse,
    ComparisonPeriodType,
    CountryBreakdownItem,
    CurrencyCode,
    DataSpanMetadata,
    GranularityType,
    PeriodMetricComparison,
    SingleSourceOrigin,
    SkuRankingItem,
    SkuRankingOrder,
    SkuRankingSortBy,
    SourceComparisonBlock,
    SourceCountryBlock,
    SourceKpiBlock,
    SourceOriginFilter,
    SourceSkuRankingBlock,
    SourceTimeSeriesBlock,
    TimeSeriesPoint,
)

ZERO_MONEY = Decimal("0.00")
ZERO_QTY = Decimal("0.0000")
DECIMAL_SCALE_DIVISOR = Decimal(FIXED_POINT_SCALE)

CURRENCY_NOTICE = (
    "Historical UCI Online Retail II records (2009-2011) are denominated in GBP, "
    "whereas live operational NEXORA records are denominated in INR (DDR-04). "
    "Sources are strictly separated and never blended into a single currency total."
)


class AnalyticsValidationError(ValueError):
    """Raised on invalid analytical query parameters (maps to HTTP 422)."""


def _scaled_to_money(scaled_int: int) -> Decimal:
    return quantize_money(Decimal(int(scaled_int)) / DECIMAL_SCALE_DIVISOR)


def _scaled_to_qty(scaled_int: int) -> Decimal:
    return quantize_qty(Decimal(int(scaled_int)) / DECIMAL_SCALE_DIVISOR)


def _safe_pct(numerator: Decimal, denominator: Decimal) -> Optional[Decimal]:
    if denominator == Decimal("0"):
        return None
    return quantize_money((numerator / denominator) * Decimal("100"))


def _safe_delta_pct(current: Decimal, previous: Decimal) -> Optional[Decimal]:
    """Returns percentage change, or None when prior baseline is 0 (never Inf/NaN)."""
    if previous == Decimal("0"):
        return None
    return quantize_money(((current - previous) / abs(previous)) * Decimal("100"))


def _source_meta(source: SingleSourceOrigin) -> Tuple[CurrencyCode, str]:
    if source == "uci_historical":
        return "GBP", "Historical UCI Dataset Baseline (2009-2011, GBP)"
    return "INR", "Live Operational Store Records (INR)"


def _subtract_months(anchor: date, months: int) -> date:
    """Shifts a date backwards by exact calendar months, clamping day to month end."""
    total_months = (anchor.year * 12 + (anchor.month - 1)) - months
    year = total_months // 12
    month = (total_months % 12) + 1
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(anchor.day, max_day))


class AnalyticsService:
    """Stateless analytical aggregation service for M06 Business Intelligence."""

    def __init__(self, repository: AnalyticsRepositoryProtocol = analytics_repository) -> None:
        self._repository = repository

    @staticmethod
    def validate_date_range(start_date: Optional[date], end_date: Optional[date]) -> None:
        if start_date is not None and end_date is not None and start_date > end_date:
            raise AnalyticsValidationError(
                f"Invalid date range: start_date ({start_date.isoformat()}) cannot be after "
                f"end_date ({end_date.isoformat()})."
            )

    def _selected_sources(self, source_origin: SourceOriginFilter) -> List[SingleSourceOrigin]:
        if source_origin == "all":
            return ["uci_historical", "operational"]
        return [source_origin]

    def _get_filtered_df(
        self,
        source: SingleSourceOrigin,
        *,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: Optional[str] = None,
        category_id: Optional[int] = None,
        stock_code: Optional[str] = None,
    ) -> pd.DataFrame:
        df = (
            self._repository.get_uci_dataframe()
            if source == "uci_historical"
            else self._repository.get_operational_dataframe()
        )
        if df.empty:
            return df

        mask = pd.Series(True, index=df.index)
        if start_date is not None:
            mask &= df["transaction_date"] >= start_date
        if end_date is not None:
            mask &= df["transaction_date"] <= end_date
        if country is not None and country.strip():
            target_country = country.strip().lower()
            mask &= df["country"].str.lower() == target_country
        if category_id is not None:
            mask &= df["category_id"] == category_id
        if stock_code is not None and stock_code.strip():
            target_sku = stock_code.strip().lower()
            mask &= df["stock_code"].str.lower() == target_sku

        return df[mask]

    @staticmethod
    def _build_data_span(df: pd.DataFrame, source: SingleSourceOrigin) -> DataSpanMetadata:
        if df.empty:
            reason = (
                "No live operational sales records exist yet in the operational store for the selected filters."
                if source == "operational"
                else "No historical UCI transaction records match the selected filters."
            )
            return DataSpanMetadata(
                start_date=None,
                end_date=None,
                record_count=0,
                has_data=False,
                empty_state_reason=reason,
            )
        min_d = df["transaction_date"].min()
        max_d = df["transaction_date"].max()
        return DataSpanMetadata(
            start_date=min_d.isoformat() if isinstance(min_d, date) else str(min_d),
            end_date=max_d.isoformat() if isinstance(max_d, date) else str(max_d),
            record_count=int(len(df)),
            has_data=True,
            empty_state_reason=None,
        )

    @staticmethod
    def _compute_stream_totals(df: pd.DataFrame) -> Dict[str, Any]:
        """Aggregates gross positive sales, returns, cancellations, and net totals exactly."""
        if df.empty:
            return {
                "gross_revenue": ZERO_MONEY,
                "return_amount": ZERO_MONEY,
                "cancellation_amount": ZERO_MONEY,
                "net_revenue": ZERO_MONEY,
                "gross_units": ZERO_QTY,
                "return_units": ZERO_QTY,
                "cancellation_units": ZERO_QTY,
                "net_units": ZERO_QTY,
                "unique_order_count": 0,
                "active_sku_count": 0,
            }

        # Valid positive sales stream (status='completed', transaction_type='standard')
        std_mask = (df["transaction_type"] == "standard") & (df["status"] == "completed")
        ret_mask = df["transaction_type"] == "return"
        can_mask = df["transaction_type"] == "cancellation"

        std_df = df[std_mask]
        ret_df = df[ret_mask]
        can_df = df[can_mask]

        gross_rev = _scaled_to_money(int(std_df["amount_scaled"].sum()))
        # Returns & cancellations store negative amounts/quantities in UCI; take absolute magnitudes
        ret_amt = _scaled_to_money(int(ret_df["amount_scaled"].abs().sum()))
        can_amt = _scaled_to_money(int(can_df["amount_scaled"].abs().sum()))
        net_rev = quantize_money(gross_rev - ret_amt - can_amt)

        gross_units = _scaled_to_qty(int(std_df["qty_scaled"].sum()))
        ret_units = _scaled_to_qty(int(ret_df["qty_scaled"].abs().sum()))
        can_units = _scaled_to_qty(int(can_df["qty_scaled"].abs().sum()))
        net_units = quantize_qty(gross_units - ret_units - can_units)

        unique_orders = int(std_df["invoice_number"].nunique()) if not std_df.empty else 0
        active_skus = int(std_df["stock_code"].nunique()) if not std_df.empty else 0

        return {
            "gross_revenue": gross_rev,
            "return_amount": ret_amt,
            "cancellation_amount": can_amt,
            "net_revenue": net_rev,
            "gross_units": gross_units,
            "return_units": ret_units,
            "cancellation_units": can_units,
            "net_units": net_units,
            "unique_order_count": unique_orders,
            "active_sku_count": active_skus,
        }

    def _build_kpi_block(self, source: SingleSourceOrigin, df: pd.DataFrame) -> SourceKpiBlock:
        currency, label = _source_meta(source)
        totals = self._compute_stream_totals(df)
        aov = (
            quantize_money(totals["gross_revenue"] / Decimal(totals["unique_order_count"]))
            if totals["unique_order_count"] > 0
            else None
        )
        return SourceKpiBlock(
            source_origin=source,
            currency=currency,
            label=label,
            data_span=self._build_data_span(df, source),
            gross_revenue=totals["gross_revenue"],
            return_amount=totals["return_amount"],
            cancellation_amount=totals["cancellation_amount"],
            net_revenue=totals["net_revenue"],
            gross_units_sold=totals["gross_units"],
            return_units=totals["return_units"],
            cancellation_units=totals["cancellation_units"],
            net_units_sold=totals["net_units"],
            unique_order_count=totals["unique_order_count"],
            active_sku_count=totals["active_sku_count"],
            average_order_value=aov,
            return_rate_pct=_safe_pct(totals["return_amount"], totals["gross_revenue"]),
            cancellation_rate_pct=_safe_pct(totals["cancellation_amount"], totals["gross_revenue"]),
        )

    def get_summary(
        self,
        *,
        provenance: RequestProvenance,
        source_origin: SourceOriginFilter = "all",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: Optional[str] = None,
        category_id: Optional[int] = None,
        stock_code: Optional[str] = None,
    ) -> AnalyticsSummaryResponse:
        self.validate_date_range(start_date, end_date)
        sources = self._selected_sources(source_origin)
        uci_block = None
        op_block = None

        for src in sources:
            filtered = self._get_filtered_df(
                src,
                start_date=start_date,
                end_date=end_date,
                country=country,
                category_id=category_id,
                stock_code=stock_code,
            )
            block = self._build_kpi_block(src, filtered)
            if src == "uci_historical":
                uci_block = block
            else:
                op_block = block

        return AnalyticsSummaryResponse(
            source_origin_filter=source_origin,
            currency_notice=CURRENCY_NOTICE,
            filters_applied={
                "source_origin": source_origin,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "country": country.strip() if country and country.strip() else None,
                "category_id": category_id,
                "stock_code": stock_code.strip() if stock_code and stock_code.strip() else None,
            },
            uci_historical=uci_block,
            operational=op_block,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _build_timeseries_block(
        self,
        source: SingleSourceOrigin,
        df: pd.DataFrame,
        granularity: GranularityType,
    ) -> SourceTimeSeriesBlock:
        currency, label = _source_meta(source)
        span = self._build_data_span(df, source)
        if df.empty:
            return SourceTimeSeriesBlock(
                source_origin=source,
                currency=currency,
                granularity=granularity,
                label=label,
                data_span=span,
                points=[],
            )

        work = df[["transaction_date", "transaction_type", "status", "invoice_number", "qty_scaled", "amount_scaled"]].copy()
        dt_series = pd.to_datetime(work["transaction_date"])

        if granularity == "day":
            work["period_key"] = dt_series.dt.strftime("%Y-%m-%d")
            work["period_start"] = work["transaction_date"]
            work["period_end"] = work["transaction_date"]
        elif granularity == "week":
            # ISO Monday-Sunday week alignment (matches DATABASE_SCHEMA.md v2.9)
            iso_cal = dt_series.dt.isocalendar()
            work["period_key"] = (
                iso_cal["year"].astype(str) + "-W" + iso_cal["week"].astype(str).str.zfill(2)
            )
            monday = (dt_series - pd.to_timedelta(dt_series.dt.weekday, unit="D")).dt.date
            sunday = (dt_series + pd.to_timedelta(6 - dt_series.dt.weekday, unit="D")).dt.date
            work["period_start"] = monday
            work["period_end"] = sunday
        else:
            work["period_key"] = dt_series.dt.strftime("%Y-%m")
            work["period_start"] = dt_series.dt.to_period("M").dt.start_time.dt.date
            work["period_end"] = dt_series.dt.to_period("M").dt.end_time.dt.date

        # Vectorized stream decomposition for fast, exact int64 aggregation
        is_std = (work["transaction_type"] == "standard") & (work["status"] == "completed")
        is_ret = work["transaction_type"] == "return"
        is_can = work["transaction_type"] == "cancellation"

        work["gross_amt_s"] = work["amount_scaled"].where(is_std, 0)
        work["ret_amt_s"] = work["amount_scaled"].abs().where(is_ret, 0)
        work["can_amt_s"] = work["amount_scaled"].abs().where(is_can, 0)
        work["gross_qty_s"] = work["qty_scaled"].where(is_std, 0)
        work["ret_qty_s"] = work["qty_scaled"].abs().where(is_ret, 0)
        work["can_qty_s"] = work["qty_scaled"].abs().where(is_can, 0)
        work["std_invoice"] = work["invoice_number"].where(is_std, None)

        grouped = (
            work.groupby("period_key", sort=True)
            .agg(
                period_start=("period_start", "first"),
                period_end=("period_end", "first"),
                gross_amt_s=("gross_amt_s", "sum"),
                ret_amt_s=("ret_amt_s", "sum"),
                can_amt_s=("can_amt_s", "sum"),
                gross_qty_s=("gross_qty_s", "sum"),
                ret_qty_s=("ret_qty_s", "sum"),
                can_qty_s=("can_qty_s", "sum"),
                order_count=("std_invoice", "nunique"),
            )
            .reset_index()
        )

        points: List[TimeSeriesPoint] = []
        for row in grouped.itertuples(index=False):
            gross_rev = _scaled_to_money(int(row.gross_amt_s))
            ret_amt = _scaled_to_money(int(row.ret_amt_s))
            can_amt = _scaled_to_money(int(row.can_amt_s))
            gross_u = _scaled_to_qty(int(row.gross_qty_s))
            ret_u = _scaled_to_qty(int(row.ret_qty_s))
            can_u = _scaled_to_qty(int(row.can_qty_s))
            points.append(
                TimeSeriesPoint(
                    period_key=str(row.period_key),
                    period_start=row.period_start.isoformat() if isinstance(row.period_start, date) else str(row.period_start),
                    period_end=row.period_end.isoformat() if isinstance(row.period_end, date) else str(row.period_end),
                    gross_revenue=gross_rev,
                    return_amount=ret_amt,
                    cancellation_amount=can_amt,
                    net_revenue=quantize_money(gross_rev - ret_amt - can_amt),
                    gross_units=gross_u,
                    net_units=quantize_qty(gross_u - ret_u - can_u),
                    order_count=int(row.order_count),
                )
            )

        return SourceTimeSeriesBlock(
            source_origin=source,
            currency=currency,
            granularity=granularity,
            label=label,
            data_span=span,
            points=points,
        )

    def get_timeseries(
        self,
        *,
        provenance: RequestProvenance,
        source_origin: SourceOriginFilter = "all",
        granularity: GranularityType = "month",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: Optional[str] = None,
        category_id: Optional[int] = None,
        stock_code: Optional[str] = None,
    ) -> AnalyticsTimeSeriesResponse:
        self.validate_date_range(start_date, end_date)
        uci_block = None
        op_block = None

        for src in self._selected_sources(source_origin):
            filtered = self._get_filtered_df(
                src,
                start_date=start_date,
                end_date=end_date,
                country=country,
                category_id=category_id,
                stock_code=stock_code,
            )
            block = self._build_timeseries_block(src, filtered, granularity)
            if src == "uci_historical":
                uci_block = block
            else:
                op_block = block

        return AnalyticsTimeSeriesResponse(
            source_origin_filter=source_origin,
            granularity=granularity,
            currency_notice=CURRENCY_NOTICE,
            filters_applied={
                "source_origin": source_origin,
                "granularity": granularity,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "country": country.strip() if country and country.strip() else None,
                "category_id": category_id,
                "stock_code": stock_code.strip() if stock_code and stock_code.strip() else None,
            },
            uci_historical=uci_block,
            operational=op_block,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _build_countries_block(
        self,
        source: SingleSourceOrigin,
        df: pd.DataFrame,
        limit: Optional[int] = None,
    ) -> SourceCountryBlock:
        currency, label = _source_meta(source)
        span = self._build_data_span(df, source)
        if df.empty:
            return SourceCountryBlock(
                source_origin=source,
                currency=currency,
                label=label,
                data_span=span,
                total_countries=0,
                total_gross_revenue=ZERO_MONEY,
                countries=[],
            )

        work = df[["country", "transaction_type", "status", "invoice_number", "qty_scaled", "amount_scaled"]].copy()
        is_std = (work["transaction_type"] == "standard") & (work["status"] == "completed")
        is_ret = work["transaction_type"] == "return"
        is_can = work["transaction_type"] == "cancellation"

        work["gross_amt_s"] = work["amount_scaled"].where(is_std, 0)
        work["ret_amt_s"] = work["amount_scaled"].abs().where(is_ret, 0)
        work["can_amt_s"] = work["amount_scaled"].abs().where(is_can, 0)
        work["gross_qty_s"] = work["qty_scaled"].where(is_std, 0)
        work["std_invoice"] = work["invoice_number"].where(is_std, None)

        grouped = (
            work.groupby("country", sort=False)
            .agg(
                gross_amt_s=("gross_amt_s", "sum"),
                ret_amt_s=("ret_amt_s", "sum"),
                can_amt_s=("can_amt_s", "sum"),
                gross_qty_s=("gross_qty_s", "sum"),
                order_count=("std_invoice", "nunique"),
            )
            .reset_index()
            .sort_values(by=["gross_amt_s", "country"], ascending=[False, True])
        )

        total_gross_rev = _scaled_to_money(int(grouped["gross_amt_s"].sum()))
        total_countries = int(len(grouped))
        if limit is not None:
            grouped = grouped.head(limit)

        items: List[CountryBreakdownItem] = []
        for row in grouped.itertuples(index=False):
            gross_rev = _scaled_to_money(int(row.gross_amt_s))
            ret_amt = _scaled_to_money(int(row.ret_amt_s))
            can_amt = _scaled_to_money(int(row.can_amt_s))
            share = _safe_pct(gross_rev, total_gross_rev) or ZERO_MONEY
            items.append(
                CountryBreakdownItem(
                    country=str(row.country),
                    gross_revenue=gross_rev,
                    return_amount=ret_amt,
                    cancellation_amount=can_amt,
                    net_revenue=quantize_money(gross_rev - ret_amt - can_amt),
                    gross_units=_scaled_to_qty(int(row.gross_qty_s)),
                    order_count=int(row.order_count),
                    revenue_share_pct=share,
                )
            )

        return SourceCountryBlock(
            source_origin=source,
            currency=currency,
            label=label,
            data_span=span,
            total_countries=total_countries,
            total_gross_revenue=total_gross_rev,
            countries=items,
        )

    def get_countries(
        self,
        *,
        provenance: RequestProvenance,
        source_origin: SourceOriginFilter = "all",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        stock_code: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> AnalyticsCountriesResponse:
        self.validate_date_range(start_date, end_date)
        uci_block = None
        op_block = None

        for src in self._selected_sources(source_origin):
            filtered = self._get_filtered_df(
                src,
                start_date=start_date,
                end_date=end_date,
                category_id=category_id,
                stock_code=stock_code,
            )
            block = self._build_countries_block(src, filtered, limit=limit)
            if src == "uci_historical":
                uci_block = block
            else:
                op_block = block

        return AnalyticsCountriesResponse(
            source_origin_filter=source_origin,
            currency_notice=CURRENCY_NOTICE,
            filters_applied={
                "source_origin": source_origin,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "category_id": category_id,
                "stock_code": stock_code.strip() if stock_code and stock_code.strip() else None,
                "limit": limit,
            },
            uci_historical=uci_block,
            operational=op_block,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _build_sku_rankings_block(
        self,
        source: SingleSourceOrigin,
        df: pd.DataFrame,
        *,
        order: SkuRankingOrder,
        sort_by: SkuRankingSortBy,
        page: int,
        page_size: int,
        category_id: Optional[int] = None,
        stock_code: Optional[str] = None,
    ) -> SourceSkuRankingBlock:
        currency, label = _source_meta(source)
        span = self._build_data_span(df, source)

        # Operational catalog map allows slow-moving analysis to include zero-sale active inventory (FEAT-V2-M06-07)
        op_catalog: Dict[str, OperationalCatalogItem] = {}
        if source == "operational":
            for item in self._repository.get_operational_catalog():
                if not item.is_active:
                    continue
                if category_id is not None and item.category_id != category_id:
                    continue
                if stock_code and stock_code.strip() and item.stock_code.lower() != stock_code.strip().lower():
                    continue
                op_catalog[item.stock_code] = item

        if df.empty and not op_catalog:
            return SourceSkuRankingBlock(
                source_origin=source,
                currency=currency,
                label=label,
                data_span=span,
                catalog_median_daily_velocity=ZERO_QTY,
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
            )

        # Compute observation window length in days for daily velocity
        if not df.empty:
            min_d = df["transaction_date"].min()
            max_d = df["transaction_date"].max()
            window_days = max(1, (max_d - min_d).days + 1)
        else:
            window_days = 1

        sku_rows: List[Dict[str, Any]] = []
        seen_skus: set[str] = set()

        if not df.empty:
            work = df[
                [
                    "stock_code",
                    "product_id",
                    "description",
                    "category_name",
                    "transaction_type",
                    "status",
                    "invoice_number",
                    "qty_scaled",
                    "amount_scaled",
                ]
            ].copy()
            is_std = (work["transaction_type"] == "standard") & (work["status"] == "completed")
            is_ret = work["transaction_type"] == "return"
            is_can = work["transaction_type"] == "cancellation"

            work["gross_amt_s"] = work["amount_scaled"].where(is_std, 0)
            work["ret_amt_s"] = work["amount_scaled"].abs().where(is_ret, 0)
            work["can_amt_s"] = work["amount_scaled"].abs().where(is_can, 0)
            work["gross_qty_s"] = work["qty_scaled"].where(is_std, 0)
            work["ret_qty_s"] = work["qty_scaled"].abs().where(is_ret, 0)
            work["can_qty_s"] = work["qty_scaled"].abs().where(is_can, 0)
            work["std_invoice"] = work["invoice_number"].where(is_std, None)

            grouped = (
                work.groupby("stock_code", sort=False)
                .agg(
                    product_id=("product_id", "first"),
                    description=("description", "first"),
                    category_name=("category_name", "first"),
                    gross_amt_s=("gross_amt_s", "sum"),
                    ret_amt_s=("ret_amt_s", "sum"),
                    can_amt_s=("can_amt_s", "sum"),
                    gross_qty_s=("gross_qty_s", "sum"),
                    ret_qty_s=("ret_qty_s", "sum"),
                    can_qty_s=("can_qty_s", "sum"),
                    order_count=("std_invoice", "nunique"),
                )
                .reset_index()
            )

            for row in grouped.itertuples(index=False):
                code = str(row.stock_code)
                seen_skus.add(code)
                gross_u = _scaled_to_qty(int(row.gross_qty_s))
                ret_u = _scaled_to_qty(int(row.ret_qty_s))
                can_u = _scaled_to_qty(int(row.can_qty_s))
                gross_rev = _scaled_to_money(int(row.gross_amt_s))
                ret_amt = _scaled_to_money(int(row.ret_amt_s))
                can_amt = _scaled_to_money(int(row.can_amt_s))
                velocity = quantize_qty(gross_u / Decimal(window_days))
                cat_item = op_catalog.get(code)
                sku_rows.append(
                    {
                        "product_id": int(row.product_id) if pd.notna(row.product_id) else (cat_item.product_id if cat_item else None),
                        "stock_code": code,
                        "description": str(row.description),
                        "category_name": str(row.category_name) if pd.notna(row.category_name) else (cat_item.category_name if cat_item else None),
                        "gross_units": gross_u,
                        "return_units": ret_u,
                        "cancellation_units": can_u,
                        "net_units": quantize_qty(gross_u - ret_u - can_u),
                        "gross_revenue": gross_rev,
                        "return_amount": ret_amt,
                        "cancellation_amount": can_amt,
                        "net_revenue": quantize_money(gross_rev - ret_amt - can_amt),
                        "order_count": int(row.order_count),
                        "avg_daily_velocity": velocity,
                        "current_inventory_qty": cat_item.current_quantity if cat_item else None,
                    }
                )

        # Include active operational catalog SKUs holding inventory with 0 sales in window
        if source == "operational":
            for code, cat_item in op_catalog.items():
                if code not in seen_skus and cat_item.current_quantity > Decimal("0"):
                    sku_rows.append(
                        {
                            "product_id": cat_item.product_id,
                            "stock_code": code,
                            "description": cat_item.description,
                            "category_name": cat_item.category_name,
                            "gross_units": ZERO_QTY,
                            "return_units": ZERO_QTY,
                            "cancellation_units": ZERO_QTY,
                            "net_units": ZERO_QTY,
                            "gross_revenue": ZERO_MONEY,
                            "return_amount": ZERO_MONEY,
                            "cancellation_amount": ZERO_MONEY,
                            "net_revenue": ZERO_MONEY,
                            "order_count": 0,
                            "avg_daily_velocity": ZERO_QTY,
                            "current_inventory_qty": cat_item.current_quantity,
                        }
                    )

        if not sku_rows:
            return SourceSkuRankingBlock(
                source_origin=source,
                currency=currency,
                label=label,
                data_span=span,
                catalog_median_daily_velocity=ZERO_QTY,
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
            )

        # Compute catalog median daily velocity for slow-moving classification
        velocities = sorted(r["avg_daily_velocity"] for r in sku_rows)
        mid = len(velocities) // 2
        if len(velocities) % 2 == 1:
            median_vel = velocities[mid]
        else:
            median_vel = quantize_qty((velocities[mid - 1] + velocities[mid]) / Decimal("2"))

        sort_field = {
            "revenue": "gross_revenue",
            "quantity": "gross_units",
            "order_count": "order_count",
        }[sort_by]

        if order == "top":
            # Deterministic descending sort with stock_code tie-breaker
            sku_rows.sort(key=lambda r: (-r[sort_field], -r["gross_revenue"], r["stock_code"]))
        else:
            # Slowest-moving: ascending velocity / sort metric, tie-break by highest held stock then code
            sku_rows.sort(
                key=lambda r: (
                    r["avg_daily_velocity"],
                    r[sort_field],
                    -(r["current_inventory_qty"] or ZERO_QTY),
                    r["stock_code"],
                )
            )

        total = len(sku_rows)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size
        page_slice = sku_rows[offset : offset + page_size]

        ranked_items = [
            SkuRankingItem(
                rank=offset + idx + 1,
                product_id=item["product_id"],
                stock_code=item["stock_code"],
                description=item["description"],
                category_name=item["category_name"],
                gross_units=item["gross_units"],
                return_units=item["return_units"],
                cancellation_units=item["cancellation_units"],
                net_units=item["net_units"],
                gross_revenue=item["gross_revenue"],
                return_amount=item["return_amount"],
                cancellation_amount=item["cancellation_amount"],
                net_revenue=item["net_revenue"],
                order_count=item["order_count"],
                avg_daily_velocity=item["avg_daily_velocity"],
                current_inventory_qty=item["current_inventory_qty"],
                is_slow_moving=bool(
                    item["avg_daily_velocity"] == ZERO_QTY
                    or item["avg_daily_velocity"] < median_vel
                ),
            )
            for idx, item in enumerate(page_slice)
        ]

        return SourceSkuRankingBlock(
            source_origin=source,
            currency=currency,
            label=label,
            data_span=span,
            catalog_median_daily_velocity=median_vel,
            items=ranked_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_sku_rankings(
        self,
        *,
        provenance: RequestProvenance,
        source_origin: SourceOriginFilter = "all",
        order: SkuRankingOrder = "top",
        sort_by: SkuRankingSortBy = "revenue",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: Optional[str] = None,
        category_id: Optional[int] = None,
        stock_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> AnalyticsSkuRankingsResponse:
        self.validate_date_range(start_date, end_date)
        uci_block = None
        op_block = None

        for src in self._selected_sources(source_origin):
            filtered = self._get_filtered_df(
                src,
                start_date=start_date,
                end_date=end_date,
                country=country,
                category_id=category_id,
                stock_code=stock_code,
            )
            block = self._build_sku_rankings_block(
                src,
                filtered,
                order=order,
                sort_by=sort_by,
                page=page,
                page_size=page_size,
                category_id=category_id,
                stock_code=stock_code,
            )
            if src == "uci_historical":
                uci_block = block
            else:
                op_block = block

        return AnalyticsSkuRankingsResponse(
            source_origin_filter=source_origin,
            order=order,
            sort_by=sort_by,
            currency_notice=CURRENCY_NOTICE,
            filters_applied={
                "source_origin": source_origin,
                "order": order,
                "sort_by": sort_by,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "country": country.strip() if country and country.strip() else None,
                "category_id": category_id,
                "stock_code": stock_code.strip() if stock_code and stock_code.strip() else None,
                "page": page,
                "page_size": page_size,
            },
            uci_historical=uci_block,
            operational=op_block,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _resolve_comparison_windows(
        anchor_date: date,
        period_type: ComparisonPeriodType,
    ) -> Tuple[date, date, str, date, date, str]:
        """Computes exact calendar-aligned current vs previous comparison windows."""
        if period_type == "mom":
            curr_start = date(anchor_date.year, anchor_date.month, 1)
            curr_end = date(
                anchor_date.year,
                anchor_date.month,
                calendar.monthrange(anchor_date.year, anchor_date.month)[1],
            )
            prev_anchor = _subtract_months(curr_start, 1)
            prev_start = date(prev_anchor.year, prev_anchor.month, 1)
            prev_end = date(
                prev_anchor.year,
                prev_anchor.month,
                calendar.monthrange(prev_anchor.year, prev_anchor.month)[1],
            )
            return (
                curr_start,
                curr_end,
                curr_start.strftime("%Y-%m"),
                prev_start,
                prev_end,
                prev_start.strftime("%Y-%m"),
            )

        if period_type == "qoq":
            q_index = (anchor_date.month - 1) // 3
            curr_q_start_month = q_index * 3 + 1
            curr_q_end_month = curr_q_start_month + 2
            curr_start = date(anchor_date.year, curr_q_start_month, 1)
            curr_end = date(
                anchor_date.year,
                curr_q_end_month,
                calendar.monthrange(anchor_date.year, curr_q_end_month)[1],
            )
            prev_start_ref = _subtract_months(curr_start, 3)
            prev_q_index = (prev_start_ref.month - 1) // 3
            prev_q_end_month = prev_start_ref.month + 2
            prev_start = date(prev_start_ref.year, prev_start_ref.month, 1)
            prev_end = date(
                prev_start_ref.year,
                prev_q_end_month,
                calendar.monthrange(prev_start_ref.year, prev_q_end_month)[1],
            )
            return (
                curr_start,
                curr_end,
                f"{anchor_date.year}-Q{q_index + 1}",
                prev_start,
                prev_end,
                f"{prev_start_ref.year}-Q{prev_q_index + 1}",
            )

        # YoY: compare exact 12-month window ending at anchor_date vs preceding 12 months
        curr_end = anchor_date
        curr_start = _subtract_months(anchor_date, 12) + timedelta(days=1)
        prev_end = curr_start - timedelta(days=1)
        prev_start = _subtract_months(prev_end, 12) + timedelta(days=1)
        return (
            curr_start,
            curr_end,
            f"{curr_start.isoformat()} to {curr_end.isoformat()}",
            prev_start,
            prev_end,
            f"{prev_start.isoformat()} to {prev_end.isoformat()}",
        )

    def _build_comparison_block(
        self,
        source: SingleSourceOrigin,
        base_df: pd.DataFrame,
        *,
        period_type: ComparisonPeriodType,
        reference_date: Optional[date],
    ) -> SourceComparisonBlock:
        currency, label = _source_meta(source)
        if base_df.empty:
            empty_span = self._build_data_span(base_df, source)
            return SourceComparisonBlock(
                source_origin=source,
                currency=currency,
                label=label,
                period_type=period_type,
                current_period_label="N/A",
                previous_period_label="N/A",
                current_span=empty_span,
                previous_span=empty_span,
                has_comparison_baseline=False,
                coverage_notice=empty_span.empty_state_reason,
                metrics=[],
            )

        max_available_date = base_df["transaction_date"].max()
        min_available_date = base_df["transaction_date"].min()
        anchor = reference_date or max_available_date

        curr_start, curr_end, curr_label, prev_start, prev_end, prev_label = (
            self._resolve_comparison_windows(anchor, period_type)
        )

        curr_df = base_df[(base_df["transaction_date"] >= curr_start) & (base_df["transaction_date"] <= curr_end)]
        prev_df = base_df[(base_df["transaction_date"] >= prev_start) & (base_df["transaction_date"] <= prev_end)]

        curr_totals = self._compute_stream_totals(curr_df)
        prev_totals = self._compute_stream_totals(prev_df)

        curr_span = self._build_data_span(curr_df, source)
        prev_span = self._build_data_span(prev_df, source)
        has_baseline = prev_span.has_data

        notices: List[str] = []
        if not has_baseline:
            notices.append(
                f"No baseline records exist in prior comparison window ({prev_label}); "
                "percentage deltas return null instead of Infinity."
            )
        if max_available_date < curr_end:
            notices.append(
                f"Current comparison window ({curr_label}) has partial coverage ending on "
                f"{max_available_date.isoformat()}."
            )
        if period_type == "yoy" and min_available_date > prev_start:
            notices.append(
                f"Single/partial multi-year coverage: available data starts on {min_available_date.isoformat()}, "
                f"after prior YoY window start ({prev_start.isoformat()})."
            )

        metric_specs = [
            ("gross_revenue", "Gross Revenue", currency, curr_totals["gross_revenue"], prev_totals["gross_revenue"], True),
            ("net_revenue", "Net Revenue", currency, curr_totals["net_revenue"], prev_totals["net_revenue"], True),
            ("gross_units_sold", "Gross Units Sold", "units", curr_totals["gross_units"], prev_totals["gross_units"], False),
            ("unique_order_count", "Unique Orders", "orders", Decimal(curr_totals["unique_order_count"]), Decimal(prev_totals["unique_order_count"]), False),
        ]

        metrics: List[PeriodMetricComparison] = []
        for key, m_label, unit, c_val, p_val, is_money in metric_specs:
            abs_delta = quantize_money(c_val - p_val) if is_money else (
                quantize_qty(c_val - p_val) if unit == "units" else (c_val - p_val)
            )
            metrics.append(
                PeriodMetricComparison(
                    metric_key=key,
                    label=m_label,
                    unit=unit,
                    current_value=c_val,
                    previous_value=p_val,
                    absolute_delta=abs_delta,
                    delta_pct=_safe_delta_pct(c_val, p_val),
                )
            )

        return SourceComparisonBlock(
            source_origin=source,
            currency=currency,
            label=label,
            period_type=period_type,
            current_period_label=curr_label,
            previous_period_label=prev_label,
            current_span=curr_span,
            previous_span=prev_span,
            has_comparison_baseline=has_baseline,
            coverage_notice=" ".join(notices) if notices else None,
            metrics=metrics,
        )

    def get_comparisons(
        self,
        *,
        provenance: RequestProvenance,
        source_origin: SourceOriginFilter = "all",
        period_type: ComparisonPeriodType = "mom",
        reference_date: Optional[date] = None,
        country: Optional[str] = None,
        category_id: Optional[int] = None,
        stock_code: Optional[str] = None,
    ) -> AnalyticsComparisonsResponse:
        uci_block = None
        op_block = None

        for src in self._selected_sources(source_origin):
            filtered = self._get_filtered_df(
                src,
                country=country,
                category_id=category_id,
                stock_code=stock_code,
            )
            block = self._build_comparison_block(
                src,
                filtered,
                period_type=period_type,
                reference_date=reference_date,
            )
            if src == "uci_historical":
                uci_block = block
            else:
                op_block = block

        return AnalyticsComparisonsResponse(
            source_origin_filter=source_origin,
            period_type=period_type,
            currency_notice=CURRENCY_NOTICE,
            filters_applied={
                "source_origin": source_origin,
                "period_type": period_type,
                "reference_date": reference_date.isoformat() if reference_date else None,
                "country": country.strip() if country and country.strip() else None,
                "category_id": category_id,
                "stock_code": stock_code.strip() if stock_code and stock_code.strip() else None,
            },
            uci_historical=uci_block,
            operational=op_block,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )


# Singleton service instance
analytics_service = AnalyticsService()
