"""Shared Cross-Module Interfaces & Temporary Adapters for Parallel NEXORA Development.

Provides clean, replaceable Protocol contracts matching DATABASE_SCHEMA.md v2.9 for
unfinished sibling modules so M06 and M08 can operate independently and integrate
seamlessly once Phase 2 (MySQL + SYS-02 Audit, building on `app.services.contracts`),
Phase 4 (SYS-03 Smart Alerts), and Phase 5 (SYS-04 Reports & Export) are connected.
"""

import copy
import csv
import io
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Literal, Optional, Protocol

from app.core.provenance import ActionSource, WorkspaceCode
from app.services.contracts import AuditEventPayload

AuditOutcome = Literal["SUCCESS", "FAILURE", "REJECTED"]
AuditTier = Literal["TIER_1_FAIL_CLOSED", "TIER_2_OUTBOX_RESILIENT"]
AlertSourceModule = Literal[
    "inventory_control",
    "predictive_planner",
    "anomaly_detection",
    "lifecycle_intelligence",
    "procurement",
    "demand_forecasting",
    "system",
]
AlertSeverity = Literal["INFO", "WARNING", "ELEVATED", "CRITICAL"]
AlertStatus = Literal["active", "acknowledged", "resolved"]

# Formula prefixes neutralized per SYS-04 / Technical Blueprint v2.2
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class AuditWriteError(RuntimeError):
    """Raised when a Tier 1 fail-closed audit write fails (triggers atomic rollback)."""


@dataclass(frozen=True)
class AuditLogEntry:
    """Immutable audit record matching DATABASE_SCHEMA.md v2.9 `audit_logs`."""

    id: int
    timestamp: str
    module: str
    action: str
    entity_type: str
    entity_id: Optional[str]
    outcome: AuditOutcome
    audit_tier: AuditTier
    action_source: ActionSource
    selected_workspace: Optional[WorkspaceCode]
    operator_ref: Optional[str]
    correlation_id: str
    idempotency_key: Optional[str]
    before_values: Optional[Dict[str, Any]]
    after_values: Optional[Dict[str, Any]]
    error_summary: Optional[str]


    def to_stage1_audit_payload(self) -> AuditEventPayload:
        """Converts this record into Stage 1's `app.services.contracts.AuditEventPayload`."""
        return AuditEventPayload(
            module=self.module,
            action=self.action,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            outcome=self.outcome,
            action_source=self.action_source,
            correlation_id=self.correlation_id,
            selected_workspace=self.selected_workspace,
            operator_ref=self.operator_ref,
            idempotency_key=self.idempotency_key,
            before_values=self.before_values,
            after_values=self.after_values,
            error_summary=self.error_summary,
        )


class AuditLoggerProtocol(Protocol):
    """Interface for SYS-02 Centralized History & Audit (`DDR-10`)."""

    def record(
        self,
        *,
        module: str,
        action: str,
        entity_type: str,
        entity_id: Optional[str],
        outcome: AuditOutcome,
        audit_tier: AuditTier,
        action_source: ActionSource,
        selected_workspace: Optional[WorkspaceCode],
        operator_ref: Optional[str],
        correlation_id: str,
        idempotency_key: Optional[str] = None,
        before_values: Optional[Dict[str, Any]] = None,
        after_values: Optional[Dict[str, Any]] = None,
        error_summary: Optional[str] = None,
    ) -> AuditLogEntry:
        """Appends an immutable audit entry. Raises AuditWriteError on Tier 1 failure."""

    def list_entries(self, module: Optional[str] = None) -> List[AuditLogEntry]:
        """Returns immutable audit entries for inspection/verification."""


class InMemoryAuditLogger:
    """Replaceable append-only in-memory adapter for SYS-02 (`audit_logs`).

    Enforces append-only semantics (zero update/delete methods), idempotency_key
    deduplication, and optional fault injection for Tier 1 fail-closed rollback tests.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: List[AuditLogEntry] = []
        self._idempotency_index: Dict[str, AuditLogEntry] = {}
        self._next_id: int = 1
        self._simulate_failure: bool = False

    def set_simulate_failure(self, enabled: bool) -> None:
        """Test hook to verify DDR-10 Tier 1 fail-closed atomic rollback."""
        with self._lock:
            self._simulate_failure = enabled

    def record(
        self,
        *,
        module: str,
        action: str,
        entity_type: str,
        entity_id: Optional[str],
        outcome: AuditOutcome,
        audit_tier: AuditTier,
        action_source: ActionSource,
        selected_workspace: Optional[WorkspaceCode],
        operator_ref: Optional[str],
        correlation_id: str,
        idempotency_key: Optional[str] = None,
        before_values: Optional[Dict[str, Any]] = None,
        after_values: Optional[Dict[str, Any]] = None,
        error_summary: Optional[str] = None,
    ) -> AuditLogEntry:
        with self._lock:
            if self._simulate_failure:
                raise AuditWriteError(
                    f"Simulated audit_logs write failure for {module}.{action} "
                    f"(tier={audit_tier}, correlation_id={correlation_id})"
                )

            if idempotency_key and idempotency_key in self._idempotency_index:
                return self._idempotency_index[idempotency_key]

            entry = AuditLogEntry(
                id=self._next_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                module=module,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                outcome=outcome,
                audit_tier=audit_tier,
                action_source=action_source,
                selected_workspace=selected_workspace,
                operator_ref=operator_ref,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                before_values=copy.deepcopy(before_values) if before_values is not None else None,
                after_values=copy.deepcopy(after_values) if after_values is not None else None,
                error_summary=error_summary[:500] if error_summary else None,
            )
            self._next_id += 1
            self._entries.append(entry)
            if idempotency_key:
                self._idempotency_index[idempotency_key] = entry
            return entry

    def list_entries(self, module: Optional[str] = None) -> List[AuditLogEntry]:
        with self._lock:
            if module is None:
                return list(self._entries)
            return [e for e in self._entries if e.module == module]

    def reset_for_tests(self) -> None:
        """Clears in-memory test state only (never exposed via API)."""
        with self._lock:
            self._entries.clear()
            self._idempotency_index.clear()
            self._next_id = 1
            self._simulate_failure = False


@dataclass
class AlertRecord:
    """Alert entity matching DATABASE_SCHEMA.md v2.9 `alerts`."""

    id: int
    product_id: Optional[int]
    source_module: AlertSourceModule
    alert_type: str
    severity: AlertSeverity
    dedup_key: Optional[str]
    title: str
    message: str
    alert_status: AlertStatus = "active"
    created_source: ActionSource = "SYSTEM"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AlertPublisherProtocol(Protocol):
    """Interface for SYS-03 Smart Alerts with unresolved duplicate suppression (`DDR-08`)."""

    def publish(
        self,
        *,
        product_id: Optional[int],
        source_module: AlertSourceModule,
        alert_type: str,
        severity: AlertSeverity,
        dedup_key: Optional[str],
        title: str,
        message: str,
        created_source: ActionSource = "SYSTEM",
    ) -> tuple[AlertRecord, bool]:
        """Creates alert or suppresses duplicate active/acknowledged alert.

        Returns:
            Tuple of (AlertRecord, created: bool). created=False if suppressed as duplicate.
        """

    def list_alerts(
        self,
        source_module: Optional[AlertSourceModule] = None,
        status_filter: Optional[AlertStatus] = None,
    ) -> List[AlertRecord]:
        """Lists stored alerts for inspection/integration verification."""


class InMemoryAlertPublisher:
    """Replaceable in-memory adapter for SYS-03 (`alerts`) with `uq_alerts_open_dedup` semantics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._alerts: List[AlertRecord] = []
        self._next_id: int = 1

    def publish(
        self,
        *,
        product_id: Optional[int],
        source_module: AlertSourceModule,
        alert_type: str,
        severity: AlertSeverity,
        dedup_key: Optional[str],
        title: str,
        message: str,
        created_source: ActionSource = "SYSTEM",
    ) -> tuple[AlertRecord, bool]:
        with self._lock:
            # Mirror `uq_alerts_open_dedup` (`active_dedup_key` active when status IN ('active', 'acknowledged'))
            if dedup_key is not None:
                for existing in self._alerts:
                    if (
                        existing.dedup_key == dedup_key
                        and existing.alert_status in ("active", "acknowledged")
                    ):
                        return existing, False

            record = AlertRecord(
                id=self._next_id,
                product_id=product_id,
                source_module=source_module,
                alert_type=alert_type,
                severity=severity,
                dedup_key=dedup_key,
                title=title[:150],
                message=message,
                alert_status="active",
                created_source=created_source,
            )
            self._next_id += 1
            self._alerts.append(record)
            return record, True

    def resolve_by_dedup_key(self, dedup_key: str) -> int:
        """Marks matching unresolved alerts as resolved (used in tests/lifecycle recovery)."""
        with self._lock:
            count = 0
            for alert in self._alerts:
                if alert.dedup_key == dedup_key and alert.alert_status != "resolved":
                    alert.alert_status = "resolved"
                    count += 1
            return count

    def list_alerts(
        self,
        source_module: Optional[AlertSourceModule] = None,
        status_filter: Optional[AlertStatus] = None,
    ) -> List[AlertRecord]:
        with self._lock:
            result = list(self._alerts)
            if source_module is not None:
                result = [a for a in result if a.source_module == source_module]
            if status_filter is not None:
                result = [a for a in result if a.alert_status == status_filter]
            return result

    def reset_for_tests(self) -> None:
        with self._lock:
            self._alerts.clear()
            self._next_id = 1


def neutralize_csv_cell(value: Any) -> str:
    """Neutralizes spreadsheet formula injection prefixes per SYS-04 specification.

    Cells beginning with '=', '+', '-', '@', '\\t', or '\\r' are prefixed with a
    leading single quote so Excel/Sheets cannot execute formulas when opening exports.
    """
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in CSV_FORMULA_PREFIXES:
        return f"'{text}"
    return text


def serialize_formula_safe_csv(headers: List[str], rows: Iterable[Dict[str, Any]]) -> str:
    """Serializes tabular analytical rows into formula-neutralized CSV text (SYS-04 contract)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([neutralize_csv_cell(h) for h in headers])
    for row in rows:
        writer.writerow([neutralize_csv_cell(row.get(h, "")) for h in headers])
    return buffer.getvalue()


# Shared module-level adapter singletons (replaceable during Phase 2/4/5 integration)
audit_logger = InMemoryAuditLogger()
alert_publisher = InMemoryAlertPublisher()
