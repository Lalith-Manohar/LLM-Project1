"""SQLAlchemy Declarative Base and shared MySQL 8.x schema constants/enums."""

from sqlalchemy import BigInteger, DateTime, Enum, String, text
from sqlalchemy.dialects.mysql import BIGINT, DATETIME
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Unsigned BIGINT & microsecond DATETIME(6) variants matching DATABASE_SCHEMA.md v2.9
UNSIGNED_BIGINT = BigInteger().with_variant(BIGINT(unsigned=True), "mysql")
DATETIME6 = DateTime(timezone=False).with_variant(DATETIME(fsp=6), "mysql")

WORKSPACE_VALUES = ("store_manager", "inventory_staff", "purchase_manager", "finance_staff")
ACTION_SOURCE_VALUES = ("UI", "API", "SYSTEM", "ML_ENGINE")
LIFECYCLE_STAGE_VALUES = ("Introduction", "Growth", "Maturity", "Decline", "Discontinued")
AUDIT_OUTCOME_VALUES = ("SUCCESS", "FAILURE", "REJECTED")
AUDIT_TIER_VALUES = ("TIER_1_FAIL_CLOSED", "TIER_2_OUTBOX_RESILIENT")
OUTBOX_STATUS_VALUES = ("pending", "retrying", "delivered", "dead_letter")

WorkspaceEnum = Enum(*WORKSPACE_VALUES, name="selected_workspace_enum", native_enum=True)
ActionSourceEnum = Enum(*ACTION_SOURCE_VALUES, name="action_source_enum", native_enum=True)
LifecycleStageEnum = Enum(*LIFECYCLE_STAGE_VALUES, name="lifecycle_stage_enum", native_enum=True)
AuditOutcomeEnum = Enum(*AUDIT_OUTCOME_VALUES, name="audit_outcome_enum", native_enum=True)
AuditTierEnum = Enum(*AUDIT_TIER_VALUES, name="audit_tier_enum", native_enum=True)
OutboxStatusEnum = Enum(*OUTBOX_STATUS_VALUES, name="outbox_status_enum", native_enum=True)


class Base(DeclarativeBase):
    """Root Declarative Base for NEXORA Phase 2+ relational models."""


class ProvenanceMixin:
    """Shared non-authenticated UI/API provenance columns (SYS-01 / DDR-10)."""

    selected_workspace: Mapped[str | None] = mapped_column(
        Enum(*WORKSPACE_VALUES, name="selected_workspace_enum", native_enum=True),
        nullable=True,
    )
    action_source: Mapped[str] = mapped_column(
        Enum(*ACTION_SOURCE_VALUES, name="action_source_enum", native_enum=True),
        nullable=False,
        server_default=text("'UI'"),
        default="UI",
    )
    operator_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
