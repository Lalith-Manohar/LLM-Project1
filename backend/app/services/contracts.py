"""Cross-module service boundary contracts for M01, M09, and SYS-02 (Stage 1)."""

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from sqlalchemy.orm import Session

from app.models.audit import AuditLog, AuditOutbox
from app.models.inventory import Inventory


@dataclass(frozen=True)
class AuditEventPayload:
    """Typed payload shared between domain modules (M01) and SYS-02 audit services."""

    module: str
    action: str
    entity_type: str
    entity_id: Optional[str]
    outcome: str
    action_source: str
    correlation_id: str
    selected_workspace: Optional[str] = None
    operator_ref: Optional[str] = None
    idempotency_key: Optional[str] = None
    before_values: Optional[dict[str, Any]] = None
    after_values: Optional[dict[str, Any]] = None
    error_summary: Optional[str] = None


class InventoryInitializerProtocol(Protocol):
    """Contract owned by M09 for atomic initial inventory row creation during M01 onboarding."""

    def initialize_product_inventory(
        self,
        session: Session,
        *,
        product_id: int,
    ) -> Inventory:
        """Create the initial 1:1 inventory row inside the caller's active transaction."""
        ...


class AuditServiceProtocol(Protocol):
    """Contract owned by SYS-02 for Tier 1 fail-closed and Tier 2 durable outbox auditing."""

    def record_tier1_event(
        self,
        session: Session,
        event: AuditEventPayload,
    ) -> AuditLog:
        """Insert a Tier 1 fail-closed audit row inside the business transaction."""
        ...

    def record_tier2_event(
        self,
        session: Session,
        event: AuditEventPayload,
    ) -> AuditOutbox:
        """Persist a Tier 2 durable outbox row inside the business transaction."""
        ...
