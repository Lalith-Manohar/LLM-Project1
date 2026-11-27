"""Centralized Audit Log and Outbox ORM models (SYS-02-owned schema, DDR-10)."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, Enum, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    ACTION_SOURCE_VALUES,
    AUDIT_OUTCOME_VALUES,
    AUDIT_TIER_VALUES,
    DATETIME6,
    OUTBOX_STATUS_VALUES,
    UNSIGNED_BIGINT,
    WORKSPACE_VALUES,
    Base,
)


class AuditLog(Base):
    """Append-only governance audit ledger owned by SYS-02."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_audit_idempotency"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_module_action", "module", "action", "timestamp"),
        Index("idx_audit_entity", "entity_type", "entity_id", "timestamp"),
        Index("idx_audit_workspace", "selected_workspace", "timestamp"),
        Index("idx_audit_outcome", "outcome", "timestamp"),
        Index("idx_audit_correlation", "correlation_id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(UNSIGNED_BIGINT, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DATETIME6,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
    )
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(
        Enum(*AUDIT_OUTCOME_VALUES, name="audit_outcome_enum", native_enum=True),
        nullable=False,
    )
    audit_tier: Mapped[str] = mapped_column(
        Enum(*AUDIT_TIER_VALUES, name="audit_tier_enum", native_enum=True),
        nullable=False,
    )
    action_source: Mapped[str] = mapped_column(
        Enum(*ACTION_SOURCE_VALUES, name="action_source_enum", native_enum=True),
        nullable=False,
    )
    selected_workspace: Mapped[str | None] = mapped_column(
        Enum(*WORKSPACE_VALUES, name="selected_workspace_enum", native_enum=True),
        nullable=True,
    )
    operator_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    before_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AuditOutbox(Base):
    """Durable Tier 2 audit retry and dead-letter outbox owned by SYS-02."""

    __tablename__ = "audit_outbox"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_outbox_idempotency"),
        CheckConstraint(
            "retry_count >= 0 AND max_retries >= 1 AND retry_count <= max_retries",
            name="chk_outbox_retry",
        ),
        Index("idx_outbox_dispatch", "status", "next_retry_at", "created_at"),
        Index("idx_outbox_correlation", "correlation_id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(UNSIGNED_BIGINT, primary_key=True, autoincrement=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("5"),
        default=5,
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(DATETIME6, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(*OUTBOX_STATUS_VALUES, name="outbox_status_enum", native_enum=True),
        nullable=False,
        server_default=text("'pending'"),
        default="pending",
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DATETIME6,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME6,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"),
    )
