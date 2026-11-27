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


class FractionalPolicyCheckerProtocol(Protocol):
    """Contract owned by M09/M05 to check fractional stock or open commitments before disabling.

    Shared Lock Order (parent-before-child — No Lock-Order Inversions):
    - `products -> orders -> order_items -> purchase_orders -> purchase_order_items -> inventory`
    - Acquire locks only on rows relevant to the operation; all M01, M05, and M09
      writers must follow this same order. A `products` row lock in M01 alone cannot
      prevent races unless concrete M05/M09 writers participate in this protocol.

    Transaction & Commitment Rules (`DATABASE_SCHEMA.md` v2.9):
    - Implementations MUST execute strictly inside the caller's active SQLAlchemy `session`
      and database transaction (after M01 acquires `SELECT ... FOR UPDATE` on `products`).
    - Customer orders (`orders` / `order_items`):
      - `draft` and `pending`: do NOT count as confirmed commitments.
      - `confirmed` and `partially_fulfilled`: count only the unfulfilled remainder
        (`base_uom_quantity - base_uom_fulfilled_quantity > 0.0000`), never mixing
        commercial UoM quantities with base-UoM quantities.
      - `fulfilled` and `cancelled`: do NOT count.
    - Purchase orders (`purchase_orders` / `purchase_order_items`, DDR-02):
      - `draft` and `submitted`: do NOT count as approved incoming commitments.
      - `approved` and `partially_received`: count only the outstanding unreceived remainder
        (`base_uom_ordered_quantity - base_uom_received_quantity > 0.0000`).
      - `received`, `cancelled`, and `rejected`: do NOT count.
    - Inventory (`inventory`, DDR-02 / DDR-03):
      - Check physical `current_quantity` and `reserved_quantity` in the same transaction;
        never treat incoming PO stock as physical stock.
    """

    def has_fractional_inventory_or_commitments(
        self,
        session: Session,
        *,
        product_id: int,
    ) -> tuple[bool, bool]:
        """Return (has_fractional_inventory, has_fractional_open_commitments) for product_id."""
        ...
