"""Inventory ORM model (M09-owned schema) aligned with DATABASE_SCHEMA.md v2.9."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import DATETIME6, UNSIGNED_BIGINT, Base

if TYPE_CHECKING:
    from app.models.product import Product


class Inventory(Base):
    """Live 1:1 warehouse stock master owned by M09 Inventory Control."""

    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_inventory_product"),
        CheckConstraint("current_quantity >= 0.0000", name="chk_inv_phys_nonneg"),
        CheckConstraint("reserved_quantity >= 0.0000", name="chk_inv_res_nonneg"),
        CheckConstraint("reserved_quantity <= current_quantity", name="chk_inv_avail_nonneg"),
        CheckConstraint("minimum_stock >= 0.0000", name="chk_inv_min_stock"),
        CheckConstraint("safety_factor >= 1.00", name="chk_inv_safety_factor"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(UNSIGNED_BIGINT, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        UNSIGNED_BIGINT,
        ForeignKey("products.id", name="fk_inventory_product", ondelete="RESTRICT"),
        nullable=False,
    )
    current_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 4, asdecimal=True),
        nullable=False,
        server_default=text("0.0000"),
        default=Decimal("0.0000"),
    )
    reserved_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 4, asdecimal=True),
        nullable=False,
        server_default=text("0.0000"),
        default=Decimal("0.0000"),
    )
    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 4, asdecimal=True),
        nullable=False,
        server_default=text("10.0000"),
        default=Decimal("10.0000"),
    )
    safety_factor: Mapped[Decimal] = mapped_column(
        Numeric(4, 2, asdecimal=True),
        nullable=False,
        server_default=text("1.20"),
        default=Decimal("1.20"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME6,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"),
    )

    product: Mapped["Product"] = relationship("Product", back_populates="inventory")
