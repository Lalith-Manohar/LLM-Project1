"""Product ORM model (M01) aligned with DATABASE_SCHEMA.md v2.9 and Stage 1 decisions."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import LIFECYCLE_STAGE_VALUES, UNSIGNED_BIGINT, Base, ProvenanceMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.inventory import Inventory
    from app.models.uom_conversion import UomConversion


class Product(ProvenanceMixin, Base):
    """Master SKU catalog entity owned by M01 Product Management."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("stock_code", name="uq_products_stock_code"),
        CheckConstraint("current_unit_price >= 0.00", name="chk_products_price_nonneg"),
        Index("idx_products_category_active", "category_id", "is_active"),
        Index("idx_products_lifecycle", "lifecycle_stage"),
        Index("idx_products_uci", "is_uci_baseline"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(UNSIGNED_BIGINT, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        UNSIGNED_BIGINT,
        ForeignKey("categories.id", name="fk_products_category", ondelete="RESTRICT"),
        nullable=True,
    )
    base_uom: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'unit'"),
        default="unit",
    )
    allow_fractional_qty: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        default=False,
    )
    current_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2, asdecimal=True),
        nullable=False,
        server_default=text("0.00"),
        default=Decimal("0.00"),
    )
    currency_code: Mapped[str] = mapped_column(
        CHAR(3),
        nullable=False,
        server_default=text("'INR'"),
        default="INR",
    )
    lifecycle_stage: Mapped[str] = mapped_column(
        Enum(*LIFECYCLE_STAGE_VALUES, name="lifecycle_stage_enum", native_enum=True),
        nullable=False,
        server_default=text("'Introduction'"),
        default="Introduction",
    )
    is_uci_baseline: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        default=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("1"),
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products")
    uom_conversions: Mapped[List["UomConversion"]] = relationship(
        "UomConversion",
        back_populates="product",
        passive_deletes=True,
    )
    inventory: Mapped[Optional["Inventory"]] = relationship(
        "Inventory",
        back_populates="product",
        uselist=False,
        passive_deletes=True,
    )
