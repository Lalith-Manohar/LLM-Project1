"""Automated Unit & API Tests for M08 — Product Lifecycle Intelligence.

Covers all DDR-08 & DDR-10 requirements:
  - 5 canonical stages: Introduction, Growth, Maturity, Decline, Discontinued
  - Cold-start SKU with zero sales -> Introduction (never Decline/Discontinued)
  - Zero-baseline prior velocity division safety (trend = None, never Inf/NaN)
  - UCI historical anchor pinned cleanly to 2011-12-09
  - Anti-flicker hysteresis across consecutive evaluations
  - Hard guard against auto-Discontinued (`chk_pls_no_auto_discontinued`)
  - Explicit manual Discontinued transition: Store Manager governance (409 otherwise),
    confirmation/reason validation (422), Tier 1 audit log, EXCL-04 compliance
  - DDR-10 Tier 1 fail-closed rollback on audit failure (both discontinue & settings)
  - Dead-stock identification & DECIMAL capital valuation (INR/GBP separated)
  - Bounded operational_settings (422 out-of-bounds, reset-to-default, forward-only
    preservation of immutable historical snapshots)
  - Deduplicated SYS-03 Smart Alerts on negative transitions & dormant stock
"""

from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.core.interfaces import InMemoryAlertPublisher, InMemoryAuditLogger
from app.core.provenance import RequestProvenance
from app.main import app
from app.repositories.lifecycle_repository import (
    HybridLifecycleRepository,
    ProductLifecycleRecord,
    UCI_ANCHOR_DATE,
)
from app.schemas.lifecycle import (
    DiscontinueProductRequest,
    LifecycleEvaluationRequest,
    LifecycleSettingsResetRequest,
    LifecycleSettingsUpdateRequest,
)
from app.services.lifecycle_service import LifecycleService, lifecycle_service


def _prov(workspace: str | None = "store_manager", operator_ref: str | None = None) -> RequestProvenance:
    return RequestProvenance(
        selected_workspace=workspace,  # type: ignore[arg-type]
        action_source="UI" if workspace else "API",
        operator_ref=operator_ref,
        correlation_id="test-m08-corr",
    )


def _build_test_fixture():
    """Creates an isolated M08 repository, audit logger, alert publisher, and service."""
    audit = InMemoryAuditLogger()
    alerts = InMemoryAlertPublisher()
    repo = HybridLifecycleRepository(audit=audit, load_uci_on_demand=False)
    today = date(2026, 11, 27)

    # 1. Brand-new cold-start SKU (onboarded today, 0 sales -> Introduction)
    repo.register_product(
        ProductLifecycleRecord(
            product_id=1,
            stock_code="SKU-INTRO-01",
            description="Brand New Arrival",
            category_name="New",
            source_origin="operational",
            currency_code="INR",
            current_unit_price=Decimal("450.00"),
            current_quantity=Decimal("25.0000"),
            is_active=True,
            onboarded_date=today,
            lifecycle_stage="Introduction",
            daily_sales={},
        )
    )

    # 2. Growing SKU (established 180d ago, prior window 2/day, current window 5/day = +150%)
    growth_sales = {}
    for d in range(1, 31):
        growth_sales[today - timedelta(days=d - 1)] = (Decimal("5.0000"), 1)
    for d in range(31, 61):
        growth_sales[today - timedelta(days=d - 1)] = (Decimal("2.0000"), 1)
    repo.register_product(
        ProductLifecycleRecord(
            product_id=2,
            stock_code="SKU-GROW-02",
            description="Rapidly Growing SKU",
            category_name="Core",
            source_origin="operational",
            currency_code="INR",
            current_unit_price=Decimal("200.00"),
            current_quantity=Decimal("60.0000"),
            is_active=True,
            onboarded_date=today - timedelta(days=180),
            lifecycle_stage="Introduction",
            daily_sales=growth_sales,
        )
    )

    # 3. Mature SKU (steady 4/day across both windows -> 0% change -> Maturity)
    mature_sales = {}
    for d in range(1, 61):
        mature_sales[today - timedelta(days=d - 1)] = (Decimal("4.0000"), 1)
    repo.register_product(
        ProductLifecycleRecord(
            product_id=3,
            stock_code="SKU-MATURE-03",
            description="Steady Flagship SKU",
            category_name="Core",
            source_origin="operational",
            currency_code="INR",
            current_unit_price=Decimal("100.00"),
            current_quantity=Decimal("50.0000"),
            is_active=True,
            onboarded_date=today - timedelta(days=240),
            lifecycle_stage="Introduction",
            daily_sales=mature_sales,
        )
    )

    # 4. Dormant / Dead-Stock SKU (last sold 150 days ago, holds 12.5 units @ ₹120.00 = ₹1500.00)
    repo.register_product(
        ProductLifecycleRecord(
            product_id=4,
            stock_code="SKU-DORMANT-04",
            description="Stagnant Seasonal Stock",
            category_name="Seasonal",
            source_origin="operational",
            currency_code="INR",
            current_unit_price=Decimal("120.00"),
            current_quantity=Decimal("12.5000"),
            is_active=True,
            onboarded_date=today - timedelta(days=300),
            lifecycle_stage="Maturity",
            daily_sales={today - timedelta(days=150): (Decimal("3.0000"), 1)},
        )
    )

    # 5. Zero-prior-baseline SKU (0 sales in prior window, active in current window)
    zero_prior_sales = {today - timedelta(days=i): (Decimal("3.0000"), 1) for i in range(10)}
    repo.register_product(
        ProductLifecycleRecord(
            product_id=5,
            stock_code="SKU-ZEROPRIOR-05",
            description="Resumed Demand SKU",
            category_name="Core",
            source_origin="operational",
            currency_code="INR",
            current_unit_price=Decimal("75.00"),
            current_quantity=Decimal("10.0000"),
            is_active=True,
            onboarded_date=today - timedelta(days=150),
            lifecycle_stage="Introduction",
            daily_sales=zero_prior_sales,
        )
    )

    # 6. UCI Historical SKU (must anchor cleanly to 2011-12-09, NOT 2026 wall-clock!)
    uci_sales = {UCI_ANCHOR_DATE - timedelta(days=i): (Decimal("10.0000"), 1) for i in range(60)}
    repo.register_product(
        ProductLifecycleRecord(
            product_id=6,
            stock_code="85123A",
            description="UCI Historical Baseline SKU",
            category_name="UCI Historical Baseline",
            source_origin="uci_historical",
            currency_code="GBP",
            current_unit_price=Decimal("2.55"),
            current_quantity=Decimal("0.0000"),
            is_active=True,
            onboarded_date=date(2010, 1, 1),
            lifecycle_stage="Introduction",
            daily_sales=uci_sales,
        )
    )

    svc = LifecycleService(repository=repo, alerts=alerts)
    return repo, audit, alerts, svc, today


class TestM08BusinessLogic:
    """Unit tests covering DDR-08 classification, hysteresis, dead-stock, alerts, and DDR-10 rollback."""

    def test_five_stage_classification_cold_start_zero_baseline_and_uci_anchor(self):
        repo, _, _, svc, today = _build_test_fixture()

        eval_res = svc.evaluate_lifecycle(
            request=LifecycleEvaluationRequest(as_of_date=today.isoformat(), source_origin="operational"),
            provenance=_prov(),
        )
        stages = {r.stock_code: r.resulting_stage for r in eval_res.results}
        assert stages["SKU-INTRO-01"] == "Introduction"
        assert stages["SKU-GROW-02"] == "Growth"
        assert stages["SKU-MATURE-03"] == "Maturity"
        # Dormant SKU transitions to Decline — NEVER Discontinued!
        assert stages["SKU-DORMANT-04"] == "Decline"
        assert stages["SKU-ZEROPRIOR-05"] == "Growth"

        # Verify zero-prior division guard returns None (not Inf/NaN)
        zp_detail = svc.get_sku_detail(product_identifier="SKU-ZEROPRIOR-05", provenance=_prov())
        assert zp_detail.sku.velocity_trend_pct is None

        # Verify UCI anchor pins cleanly to 2011-12-09 (so active Dec 2011 SKU is Maturity, NOT Decline!)
        uci_eval = svc.evaluate_lifecycle(
            request=LifecycleEvaluationRequest(source_origin="uci_historical"),
            provenance=_prov(),
        )
        assert uci_eval.results[0].resulting_stage == "Maturity"
        uci_detail = svc.get_sku_detail(product_identifier="85123A", provenance=_prov())
        assert uci_detail.sku.anchor_date == "2011-12-09"
        assert uci_detail.sku.days_since_last_sale == 0

    def test_anti_flicker_hysteresis_requires_consecutive_windows(self):
        repo, _, alerts, svc, today = _build_test_fixture()

        # Baseline evaluation sets SKU-MATURE-03 to Maturity
        svc.evaluate_lifecycle(
            request=LifecycleEvaluationRequest(stock_codes=["SKU-MATURE-03"], as_of_date=today.isoformat()),
            provenance=_prov(),
        )
        assert repo.get_product(3).lifecycle_stage == "Maturity"  # type: ignore[union-attr]

        # Simulate sudden demand drop: 0 sales in current 30d window
        prod = repo.get_product(3)
        assert prod is not None
        prod.daily_sales = {today - timedelta(days=40): (Decimal("10.0000"), 1)}

        # Window 1 of hysteresis (default lifecycle_hysteresis_windows = 2): buffered, stage stays Maturity
        r1 = svc.evaluate_lifecycle(
            request=LifecycleEvaluationRequest(stock_codes=["SKU-MATURE-03"], as_of_date=today.isoformat()),
            provenance=_prov(),
        )
        assert r1.results[0].raw_candidate_stage == "Decline"
        assert r1.results[0].resulting_stage == "Maturity"
        assert r1.results[0].hysteresis_pending is True
        assert r1.results[0].transitioned is False

        # Window 2 of consecutive Decline signal: commits transition Maturity -> Decline + emits SYS-03 alert!
        r2 = svc.evaluate_lifecycle(
            request=LifecycleEvaluationRequest(stock_codes=["SKU-MATURE-03"], as_of_date=today.isoformat()),
            provenance=_prov(),
        )
        assert r2.results[0].resulting_stage == "Decline"
        assert r2.results[0].transitioned is True
        assert r2.alerts_emitted == 1
        assert len(alerts.list_alerts(source_module="lifecycle_intelligence")) == 1

    def test_non_auto_discontinued_constraint_enforced_at_repository(self):
        repo, _, _, _, _ = _build_test_fixture()
        with pytest.raises(ValueError, match="chk_pls_no_auto_discontinued"):
            repo.append_evaluation_snapshot(
                product_id=4,
                new_stage="Discontinued",
                previous_stage="Decline",
                rolling_velocity=Decimal("0.0000"),
                order_frequency=Decimal("0.0000"),
                sku_age_days=300,
                days_since_last_sale=150,
                is_dormant_stock=True,
                applied_settings_snapshot={},
                provenance=_prov(),
            )

    def test_dead_stock_valuation_decimal_and_dedup_alert_suppression(self):
        _, _, alerts, svc, today = _build_test_fixture()

        dead = svc.get_dead_stock(provenance=_prov(), source_origin="operational")
        assert dead.total_dead_stock_skus == 1
        assert dead.items[0].stock_code == "SKU-DORMANT-04"
        # 12.5000 * 120.00 = 1500.00 exact INR DECIMAL
        assert dead.items[0].dead_stock_value == Decimal("1500.00")
        assert dead.operational_dead_stock_value_inr == Decimal("1500.00")
        assert "EXCL-04" in dead.policy_notice

        # Run dormant evaluation twice -> 1st creates alert, 2nd suppresses duplicate unresolved alert
        e1 = svc.evaluate_lifecycle(
            request=LifecycleEvaluationRequest(stock_codes=["SKU-DORMANT-04"], as_of_date=today.isoformat()),
            provenance=_prov(),
        )
        e2 = svc.evaluate_lifecycle(
            request=LifecycleEvaluationRequest(stock_codes=["SKU-DORMANT-04"], as_of_date=today.isoformat()),
            provenance=_prov(),
        )
        assert e1.alerts_emitted == 1
        assert e2.alerts_emitted == 0
        assert e2.alerts_suppressed_duplicates == 1
        assert len(alerts.list_alerts(source_module="lifecycle_intelligence")) == 1

    def test_manual_discontinue_and_tier1_audit_fail_closed_rollback(self):
        repo, audit, _, svc, today = _build_test_fixture()

        # Simulate audit DB failure -> must roll back BOTH product.lifecycle_stage and snapshot!
        audit.set_simulate_failure(True)
        with pytest.raises(Exception):
            svc.discontinue_product(
                product_identifier=4,
                request=DiscontinueProductRequest(
                    confirm_discontinue=True,
                    reason="End of seasonal line",
                    operator_ref="MGR-01",
                ),
                provenance=_prov("store_manager"),
            )
        assert repo.get_product(4).lifecycle_stage == "Maturity"  # type: ignore[union-attr]
        assert len(repo.get_snapshots(4)) == 0

        # Restore audit -> succeeds atomically with Tier 1 audit entry
        audit.set_simulate_failure(False)
        disc = svc.discontinue_product(
            product_identifier=4,
            request=DiscontinueProductRequest(
                confirm_discontinue=True,
                reason="End of seasonal line",
                operator_ref="MGR-01",
            ),
            provenance=_prov("store_manager"),
        )
        assert disc.lifecycle_stage == "Discontinued"
        assert disc.snapshot.trigger_type == "manual_discontinued"
        assert len(audit.list_entries("M08_LIFECYCLE")) == 1
        assert audit.list_entries("M08_LIFECYCLE")[0].action == "PRODUCT_DISCONTINUED"

        # Subsequent automated evaluation MUST skip Discontinued SKU without overwriting it
        after_eval = svc.evaluate_lifecycle(
            request=LifecycleEvaluationRequest(stock_codes=["SKU-DORMANT-04"], as_of_date=today.isoformat()),
            provenance=_prov(),
        )
        assert after_eval.skipped_discontinued_count == 1
        assert repo.get_product(4).lifecycle_stage == "Discontinued"  # type: ignore[union-attr]

    def test_bounded_settings_forward_only_snapshot_immutability_and_rollback(self):
        repo, audit, _, svc, today = _build_test_fixture()

        # Record a snapshot under default settings (hysteresis=2, inactivity=90)
        svc.evaluate_lifecycle(
            request=LifecycleEvaluationRequest(stock_codes=["SKU-INTRO-01"], as_of_date=today.isoformat()),
            provenance=_prov(),
        )
        orig_snapshot = repo.get_snapshots(1)[0]
        assert orig_snapshot.applied_settings_snapshot["lifecycle_inactivity_days"] == 90  # type: ignore[index]

        # Update settings inside valid bounds
        upd = svc.update_settings(
            request=LifecycleSettingsUpdateRequest(
                lifecycle_inactivity_days=120,
                lifecycle_hysteresis_windows=3,
                operator_ref="OPS-LEAD",
            ),
            provenance=_prov("store_manager"),
        )
        assert upd.audit_log_id is not None
        by_key = {s.setting_key: s.setting_value for s in upd.settings}
        assert by_key["lifecycle_inactivity_days"] == 120
        assert by_key["lifecycle_hysteresis_windows"] == 3

        # Prior historical snapshot MUST remain completely untouched (forward-only rule DDR-08)
        assert repo.get_snapshots(1)[0].applied_settings_snapshot["lifecycle_inactivity_days"] == 90  # type: ignore[index]

        # Tier 1 audit failure rolls back settings update atomically
        audit.set_simulate_failure(True)
        with pytest.raises(Exception):
            svc.update_settings(
                request=LifecycleSettingsUpdateRequest(lifecycle_inactivity_days=150),
                provenance=_prov("store_manager"),
            )
        assert repo.get_settings()["lifecycle_inactivity_days"].setting_value == 120
        audit.set_simulate_failure(False)

        # Reset to defaults restores 90 & 2 with Tier 1 LIFECYCLE_CONFIG_RESET audit
        reset_res = svc.reset_settings(
            request=LifecycleSettingsResetRequest(operator_ref="OPS-LEAD"),
            provenance=_prov("store_manager"),
        )
        reset_map = {s.setting_key: s.setting_value for s in reset_res.settings}
        assert reset_map["lifecycle_inactivity_days"] == 90
        assert reset_map["lifecycle_hysteresis_windows"] == 2
        assert audit.list_entries("M08_LIFECYCLE")[-1].action == "LIFECYCLE_CONFIG_RESET"


class TestM08LifecycleEndpoints:
    """FastAPI HTTP integration tests for M08 routes."""

    @pytest.fixture
    def client_with_isolated_m08(self, monkeypatch):
        repo, audit, alerts, _, today = _build_test_fixture()
        monkeypatch.setattr(lifecycle_service, "_repository", repo)
        monkeypatch.setattr(lifecycle_service, "_alerts", alerts)
        return TestClient(app), repo, audit, alerts, today

    def test_portfolio_detail_history_and_404(self, client_with_isolated_m08):
        client, _, _, _, _ = client_with_isolated_m08

        resp = client.get(
            "/api/v1/intelligence/lifecycle",
            headers={"X-NEXORA-Workspace": "Store Manager (Admin)"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6
        assert set(data["distribution"].keys()) == {
            "Introduction",
            "Growth",
            "Maturity",
            "Decline",
            "Discontinued",
        }

        detail = client.get("/api/v1/intelligence/lifecycle/SKU-GROW-02")
        assert detail.status_code == 200
        assert detail.json()["sku"]["stock_code"] == "SKU-GROW-02"

        hist = client.get("/api/v1/intelligence/lifecycle/2/history")
        assert hist.status_code == 200
        assert hist.json()["product_id"] == 2

        missing = client.get("/api/v1/intelligence/lifecycle/NON_EXISTENT_SKU")
        assert missing.status_code == 404

    def test_discontinue_governance_409_and_validation_422(self, client_with_isolated_m08):
        client, _, _, _, _ = client_with_isolated_m08

        # Inventory Staff cannot execute manual Discontinued -> 409 Workflow Governance Conflict
        blocked = client.patch(
            "/api/v1/intelligence/lifecycle/4/discontinue",
            headers={"X-NEXORA-Workspace": "Inventory Staff"},
            json={"confirm_discontinue": True, "reason": "Trying from wrong workspace"},
        )
        assert blocked.status_code == 409

        # confirm_discontinue=False -> 422
        unconfirmed = client.patch(
            "/api/v1/intelligence/lifecycle/4/discontinue",
            headers={"X-NEXORA-Workspace": "store_manager"},
            json={"confirm_discontinue": False, "reason": "Not confirmed"},
        )
        assert unconfirmed.status_code == 422

        # Valid Store Manager discontinuation -> 200
        ok = client.patch(
            "/api/v1/intelligence/lifecycle/4/discontinue",
            headers={"X-NEXORA-Workspace": "store_manager"},
            json={"confirm_discontinue": True, "reason": "Approved clearance complete"},
        )
        assert ok.status_code == 200
        assert ok.json()["lifecycle_stage"] == "Discontinued"

        # Second attempt on already-Discontinued SKU -> 409
        dup = client.patch(
            "/api/v1/intelligence/lifecycle/4/discontinue",
            headers={"X-NEXORA-Workspace": "store_manager"},
            json={"confirm_discontinue": True, "reason": "Duplicate attempt"},
        )
        assert dup.status_code == 409

    def test_settings_out_of_bounds_returns_422_and_wrong_workspace_returns_409(self, client_with_isolated_m08):
        client, _, _, _, _ = client_with_isolated_m08

        # Out of bounds (lifecycle_inactivity_days max is 365) -> 422
        oob = client.put(
            "/api/v1/settings/lifecycle",
            headers={"X-NEXORA-Workspace": "store_manager"},
            json={"lifecycle_inactivity_days": 999},
        )
        assert oob.status_code == 422

        # Out of bounds (lifecycle_hysteresis_windows min is 1) -> 422
        oob_low = client.put(
            "/api/v1/settings/lifecycle",
            headers={"X-NEXORA-Workspace": "store_manager"},
            json={"lifecycle_hysteresis_windows": 0},
        )
        assert oob_low.status_code == 422

        # Wrong workspace -> 409
        wrong_ws = client.put(
            "/api/v1/settings/lifecycle",
            headers={"X-NEXORA-Workspace": "purchase_manager"},
            json={"lifecycle_inactivity_days": 100},
        )
        assert wrong_ws.status_code == 409

        # Valid update & reset
        ok = client.put(
            "/api/v1/settings/lifecycle",
            headers={"X-NEXORA-Workspace": "store_manager"},
            json={"lifecycle_inactivity_days": 100},
        )
        assert ok.status_code == 200

        reset = client.post(
            "/api/v1/settings/lifecycle/reset",
            headers={"X-NEXORA-Workspace": "store_manager"},
            json={},
        )
        assert reset.status_code == 200
