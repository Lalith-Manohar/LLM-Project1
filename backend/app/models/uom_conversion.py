"""Unit-of-Measure conversion ORM model (M01, DDR-06) aligned with Schema v2.9."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import DATETIME6, UNSIGNED_BIGINT, Base, ProvenanceMixin

if TYPE_CHECKING:
    from app.models.product import Product


class UomConversion(ProvenanceMixin, Base):
    """Effective-dated, product-specific UoM conversion factor table with immediate rollover."""

    __tablename__ = "uom_conversions"
    __table_args__ = (
        UniqueConstraint("product_id", "uom_code", "effective_from", name="uq_uom_product_code_eff"),
        UniqueConstraint("active_product_id", "active_uom_code", name="uq_uom_one_active"),
        CheckConstraint("conversion_to_base > 0.000000", name="chk_uom_factor_pos"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_uom_effective_window",
        ),
        CheckConstraint(
            "is_active = TRUE OR effective_to IS NOT NULL",
            name="chk_uom_inactive_closed",
        ),
        Index("idx_uom_lookup", "product_id", "uom_code", "is_active", "effective_from"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(UNSIGNED_BIGINT, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        UNSIGNED_BIGINT,
        ForeignKey("products.id", name="fk_uom_product", ondelete="RESTRICT"),
        nullable=False,
    )
    uom_code: Mapped[str] = mapped_column(String(32), nullable=False)
    conversion_to_base: Mapped[Decimal] = mapped_column(
        Numeric(12, 6, asdecimal=True),
        nullable=False,
    )
    effective_from: Mapped[datetime] = mapped_column(
        DATETIME6,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
    )
    effective_to: Mapped[datetime | None] = mapped_column(DATETIME6, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("1"),
        default=True,
    )
    active_product_id: Mapped[int | None] = mapped_column(
        UNSIGNED_BIGINT,
        Computed("IF(is_active = TRUE, product_id, NULL)", persisted=False),
        nullable=True,
    )
    active_uom_code: Mapped[str | None] = mapped_column(
        String(32),
        Computed("IF(is_active = TRUE, uom_code, NULL)", persisted=False),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME6,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
    )

    product: Mapped["Product"] = relationship("Product", back_populates="uom_conversions")
