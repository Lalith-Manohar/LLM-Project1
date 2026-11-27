"""Automated Unit & API Tests for M06 — Business Intelligence (/api/v1/analytics/*).

Covers:
  - 4-stream demand consistency (Gross positive sales vs. Cancellations vs. Returns)
  - Exact DECIMAL precision (zero float drift)
  - Strict GBP (UCI) vs. INR (operational) separation & live update reflection
  - Date validation (422 when start_date > end_date) & empty-filter 200 OK safety
  - Daily / ISO-weekly / monthly time-series reconciliation
  - Geographical country breakdown & share % reconciliation
  - Top & Slow-Moving SKU rankings, pagination & active zero-sale inventory inclusion
  - MoM / QoQ / YoY comparisons with null zero-baseline safety
  - Non-auth X-NEXORA-Workspace & X-Correlation-ID provenance headers
  - SYS-04 formula-injection CSV neutralization
  - Real UCI dataset smoke test
"""

from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.core.interfaces import neutralize_csv_cell, serialize_formula_safe_csv
from app.core.provenance import RequestProvenance
from app.main import app
from app.repositories.analytics_repository import (
    HybridAnalyticsRepository,
    OperationalCatalogItem,
    OperationalSaleRecord,
    build_normalized_df_from_records,
)
from app.services.analytics_service import AnalyticsService, analytics_service


def _make_synthetic_repo() -> HybridAnalyticsRepository:
    """Builds a deterministic in-memory repository with both UCI (GBP) and Operational (INR) rows."""
    uci_rows = [
        # Dec 2010 baseline (prior YoY / prior period)
        {
            "invoice_number": "500001",
            "transaction_date": date(2010, 12, 10),
            "country": "United Kingdom",
            "transaction_type": "standard",
            "stock_code": "85123A",
            "description": "WHITE HANGING HEART",
            "quantity": "10",
            "unit_price": "2.55",
        },
        # Oct 2011
        {
            "invoice_number": "510001",
            "transaction_date": date(2011, 10, 15),
            "country": "United Kingdom",
            "transaction_type": "standard",
            "stock_code": "85123A",
            "description": "WHITE HANGING HEART",
            "quantity": "20",
            "unit_price": "2.55",
        },
        # Nov 2011 — standard + cancellation + return + second country
        {
            "invoice_number": "520001",
            "transaction_date": date(2011, 11, 5),
            "country": "United Kingdom",
            "transaction_type": "standard",
            "stock_code": "85123A",
            "description": "WHITE HANGING HEART",
            "quantity": "40",
            "unit_price": "2.50",
        },
        {
            "invoice_number": "520002",
            "transaction_date": date(2011, 11, 12),
            "country": "Germany",
            "transaction_type": "standard",
            "stock_code": "71053",
            "description": "WHITE METAL LANTERN",
            "quantity": "10",
            "unit_price": "5.00",
        },
        {
            "invoice_number": "C520001",
            "transaction_date": date(2011, 11, 14),
            "country": "United Kingdom",
            "transaction_type": "cancellation",
            "stock_code": "85123A",
            "description": "WHITE HANGING HEART",
            "quantity": "-4",
            "unit_price": "2.50",
        },
        {
            "invoice_number": "520099",
            "transaction_date": date(2011, 11, 16),
            "country": "Germany",
            "transaction_type": "return",
            "stock_code": "71053",
            "description": "WHITE METAL LANTERN",
            "quantity": "-2",
            "unit_price": "5.00",
        },
    ]
    uci_df = build_normalized_df_from_records(uci_rows, currency_code="GBP")
    return HybridAnalyticsRepository(uci_override_df=uci_df)


def _provenance(workspace: str = "store_manager") -> RequestProvenance:
    return RequestProvenance(
        selected_workspace=workspace,  # type: ignore[arg-type]
        action_source="UI",
        operator_ref=None,
        correlation_id="test-m06-corr",
    )


class TestM06BusinessLogic:
    """Unit tests verifying M06 exact DECIMAL arithmetic and business invariants."""

    def test_stream_isolation_and_exact_decimal_reconciliation(self):
        repo = _make_synthetic_repo()
        svc = AnalyticsService(repository=repo)

        res = svc.get_summary(
            provenance=_provenance(),
            source_origin="uci_historical",
            start_date=date(2011, 11, 1),
            end_date=date(2011, 11, 30),
        )
        assert res.currency_blending_prohibited is True
        assert res.operational is None
        block = res.uci_historical
        assert block is not None
        assert block.currency == "GBP"
        # Gross: (40 * 2.50 = 100.00) + (10 * 5.00 = 50.00) = 150.00
        assert block.gross_revenue == Decimal("150.00")
        # Cancellation: 4 * 2.50 = 10.00; Return: 2 * 5.00 = 10.00
        assert block.cancellation_amount == Decimal("10.00")
        assert block.return_amount == Decimal("10.00")
        # Net: 150.00 - 10.00 - 10.00 = 130.00
        assert block.net_revenue == Decimal("130.00")
        assert block.gross_units_sold == Decimal("50.0000")
        assert block.net_units_sold == Decimal("44.0000")
        assert block.unique_order_count == 2
        assert block.active_sku_count == 2
        assert block.average_order_value == Decimal("75.00")

    def test_empty_operational_store_and_live_addition_reflection(self):
        repo = _make_synthetic_repo()
        svc = AnalyticsService(repository=repo)

        # 1. Initially empty operational store returns clean empty state without ZeroDivisionError
        empty_res = svc.get_summary(provenance=_provenance(), source_origin="operational")
        assert empty_res.uci_historical is None
        op = empty_res.operational
        assert op is not None
        assert op.currency == "INR"
        assert op.data_span.has_data is False
        assert op.gross_revenue == Decimal("0.00")
        assert op.average_order_value is None
        assert op.return_rate_pct is None

        # 2. Immediately reflects newly committed INR operational sale & return
        repo.add_operational_records(
            [
                OperationalSaleRecord(
                    invoice_number="INV-2026-001",
                    transaction_date=date(2026, 11, 20),
                    country="India",
                    transaction_type="standard",
                    product_id=101,
                    stock_code="NEX-INR-01",
                    description="Operational Desk Lamp",
                    category_id=1,
                    category_name="Lighting",
                    quantity=Decimal("3.0000"),
                    base_uom_quantity=Decimal("3.0000"),
                    unit_price=Decimal("333.33"),
                    line_total=Decimal("999.99"),
                ),
                OperationalSaleRecord(
                    invoice_number="RET-2026-001",
                    transaction_date=date(2026, 11, 21),
                    country="India",
                    transaction_type="return",
                    product_id=101,
                    stock_code="NEX-INR-01",
                    description="Operational Desk Lamp",
                    category_id=1,
                    category_name="Lighting",
                    quantity=Decimal("-1.0000"),
                    base_uom_quantity=Decimal("-1.0000"),
                    unit_price=Decimal("333.33"),
                    line_total=Decimal("-333.33"),
                ),
            ]
        )

        combined = svc.get_summary(provenance=_provenance(), source_origin="all")
        assert combined.uci_historical is not None and combined.uci_historical.currency == "GBP"
        assert combined.operational is not None and combined.operational.currency == "INR"
        assert combined.operational.data_span.has_data is True
        assert combined.operational.gross_revenue == Decimal("999.99")
        assert combined.operational.return_amount == Decimal("333.33")
        assert combined.operational.net_revenue == Decimal("666.66")

    def test_timeseries_granularities_reconcile_with_summary(self):
        repo = _make_synthetic_repo()
        svc = AnalyticsService(repository=repo)

        summary = svc.get_summary(provenance=_provenance(), source_origin="uci_historical")
        expected_gross = summary.uci_historical.gross_revenue  # type: ignore[union-attr]

        for gran in ("day", "week", "month"):
            ts = svc.get_timeseries(
                provenance=_provenance(),
                source_origin="uci_historical",
                granularity=gran,  # type: ignore[arg-type]
            )
            assert ts.uci_historical is not None
            summed = sum((p.gross_revenue for p in ts.uci_historical.points), Decimal("0.00"))
            assert summed == expected_gross

    def test_countries_breakdown_and_share_sum(self):
        repo = _make_synthetic_repo()
        svc = AnalyticsService(repository=repo)

        res = svc.get_countries(
            provenance=_provenance(),
            source_origin="uci_historical",
            start_date=date(2011, 11, 1),
            end_date=date(2011, 11, 30),
        )
        block = res.uci_historical
        assert block is not None
        assert block.total_countries == 2
        assert block.countries[0].country == "United Kingdom"
        assert block.countries[0].gross_revenue == Decimal("100.00")
        assert block.countries[1].country == "Germany"
        assert block.countries[1].gross_revenue == Decimal("50.00")
        share_total = sum((c.revenue_share_pct for c in block.countries), Decimal("0.00"))
        assert share_total == Decimal("100.00")

    def test_slow_moving_includes_zero_sale_active_operational_inventory(self):
        repo = _make_synthetic_repo()
        repo.add_operational_records(
            [
                OperationalSaleRecord(
                    invoice_number="INV-1",
                    transaction_date=date(2026, 11, 1),
                    country="India",
                    transaction_type="standard",
                    product_id=1,
                    stock_code="FAST-01",
                    description="Fast Mover",
                    category_id=1,
                    category_name="Core",
                    quantity=Decimal("100.0000"),
                    base_uom_quantity=Decimal("100.0000"),
                    unit_price=Decimal("50.00"),
                    line_total=Decimal("5000.00"),
                ),
            ]
        )
        repo.upsert_operational_catalog(
            [
                OperationalCatalogItem(
                    product_id=1,
                    stock_code="FAST-01",
                    description="Fast Mover",
                    category_id=1,
                    category_name="Core",
                    current_quantity=Decimal("20.0000"),
                ),
                OperationalCatalogItem(
                    product_id=2,
                    stock_code="ZERO-SALE-02",
                    description="Slow Active Holding Stock",
                    category_id=1,
                    category_name="Core",
                    current_quantity=Decimal("45.0000"),
                ),
            ]
        )

        svc = AnalyticsService(repository=repo)
        res = svc.get_sku_rankings(
            provenance=_provenance(),
            source_origin="operational",
            order="slowest",
            page=1,
            page_size=10,
        )
        block = res.operational
        assert block is not None
        assert block.total == 2
        assert block.items[0].stock_code == "ZERO-SALE-02"
        assert block.items[0].gross_units == Decimal("0.0000")
        assert block.items[0].current_inventory_qty == Decimal("45.0000")
        assert block.items[0].is_slow_moving is True

    def test_comparisons_mom_qoq_yoy_and_zero_baseline_null_safety(self):
        repo = _make_synthetic_repo()
        svc = AnalyticsService(repository=repo)

        # MoM: Nov 2011 (150.00 gross) vs Oct 2011 (51.00 gross)
        mom = svc.get_comparisons(
            provenance=_provenance(),
            source_origin="uci_historical",
            period_type="mom",
            reference_date=date(2011, 11, 20),
        )
        block = mom.uci_historical
        assert block is not None
        assert block.has_comparison_baseline is True
        gross_m = next(m for m in block.metrics if m.metric_key == "gross_revenue")
        assert gross_m.current_value == Decimal("150.00")
        assert gross_m.previous_value == Decimal("51.00")
        assert gross_m.delta_pct is not None

        # MoM on Oct 2011 where Sep 2011 has 0 sales -> delta_pct MUST be None (never Inf/NaN)
        zero_base = svc.get_comparisons(
            provenance=_provenance(),
            source_origin="uci_historical",
            period_type="mom",
            reference_date=date(2011, 10, 20),
        )
        zb = zero_base.uci_historical
        assert zb is not None
        assert zb.has_comparison_baseline is False
        gross_zb = next(m for m in zb.metrics if m.metric_key == "gross_revenue")
        assert gross_zb.previous_value == Decimal("0.00")
        assert gross_zb.delta_pct is None

        # YoY coverage notice when dataset has partial 2-year span
        yoy = svc.get_comparisons(
            provenance=_provenance(),
            source_origin="uci_historical",
            period_type="yoy",
            reference_date=date(2011, 11, 30),
        )
        assert yoy.uci_historical is not None
        assert yoy.uci_historical.coverage_notice is not None

    def test_sys04_csv_formula_neutralization(self):
        assert neutralize_csv_cell("=CMD|' /C calc'!A0") == "'=CMD|' /C calc'!A0"
        assert neutralize_csv_cell("+SUM(A1:A2)") == "'+SUM(A1:A2)"
        assert neutralize_csv_cell("-100") == "'-100"
        assert neutralize_csv_cell("@HYPERLINK") == "'@HYPERLINK"
        assert neutralize_csv_cell("\tTabFormula") == "'\tTabFormula"
        assert neutralize_csv_cell("NormalSKU") == "NormalSKU"
        csv_out = serialize_formula_safe_csv(["sku", "formula"], [{"sku": "85123A", "formula": "=1+1"}])
        assert "'=1+1" in csv_out


class TestM06AnalyticsEndpoints:
    """FastAPI HTTP integration tests for /api/v1/analytics/*."""

    @pytest.fixture
    def client_with_synthetic_repo(self, monkeypatch):
        repo = _make_synthetic_repo()
        monkeypatch.setattr(analytics_service, "_repository", repo)
        return TestClient(app), repo

    def test_invalid_date_range_returns_422(self, client_with_synthetic_repo):
        client, _ = client_with_synthetic_repo
        for path in (
            "/api/v1/analytics/summary",
            "/api/v1/analytics/timeseries",
            "/api/v1/analytics/countries",
            "/api/v1/analytics/sku-rankings",
        ):
            resp = client.get(
                path,
                params={"start_date": "2011-12-01", "end_date": "2011-01-01"},
            )
            assert resp.status_code == 422

    def test_unknown_country_or_sku_returns_empty_200(self, client_with_synthetic_repo):
        client, _ = client_with_synthetic_repo
        resp = client.get(
            "/api/v1/analytics/sku-rankings",
            params={"source_origin": "uci_historical", "stock_code": "DOES_NOT_EXIST_999"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["uci_historical"]["total"] == 0
        assert body["uci_historical"]["items"] == []

        resp_country = client.get(
            "/api/v1/analytics/summary",
            params={"source_origin": "uci_historical", "country": "Atlantis"},
        )
        assert resp_country.status_code == 200
        assert resp_country.json()["uci_historical"]["data_span"]["record_count"] == 0

    def test_workspace_and_correlation_headers_propagated_and_validated(self, client_with_synthetic_repo):
        client, _ = client_with_synthetic_repo
        resp = client.get(
            "/api/v1/analytics/summary",
            headers={
                "X-NEXORA-Workspace": "Finance Staff",
                "X-Correlation-ID": "corr-m06-999",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workspace_context"] == "Finance Staff"
        assert data["correlation_id"] == "corr-m06-999"

        bad = client.get(
            "/api/v1/analytics/summary",
            headers={"X-NEXORA-Workspace": "UnauthorizedHackerRole"},
        )
        assert bad.status_code == 422

    def test_pagination_on_sku_rankings(self, client_with_synthetic_repo):
        client, _ = client_with_synthetic_repo
        resp = client.get(
            "/api/v1/analytics/sku-rankings",
            params={"source_origin": "uci_historical", "page": 1, "page_size": 1},
        )
        assert resp.status_code == 200
        block = resp.json()["uci_historical"]
        assert block["total"] == 2
        assert block["total_pages"] == 2
        assert len(block["items"]) == 1
        assert block["items"][0]["rank"] == 1

    def test_real_uci_dataset_smoke_check(self):
        """Verifies real tracked online_retail_II.csv loads cleanly with authentic UK dominance."""
        real_client = TestClient(app)
        resp = real_client.get(
            "/api/v1/analytics/countries",
            params={"source_origin": "uci_historical", "limit": 5},
        )
        assert resp.status_code == 200
        block = resp.json()["uci_historical"]
        assert block["currency"] == "GBP"
        assert block["data_span"]["has_data"] is True
        assert block["data_span"]["start_date"] == "2009-12-01"
        assert block["data_span"]["end_date"] == "2011-12-09"
        assert block["countries"][0]["country"] == "United Kingdom"
        assert Decimal(block["countries"][0]["revenue_share_pct"]) > Decimal("80.00")
