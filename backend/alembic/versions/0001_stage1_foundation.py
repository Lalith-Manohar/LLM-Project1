"""Stage 1 foundation tables (categories, products, uom_conversions, inventory, audit_logs, audit_outbox).

Revision ID: 0001_stage1_foundation
Revises: None
Create Date: 2026-11-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "0001_stage1_foundation"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WORKSPACE_ENUM = sa.Enum(
    "store_manager",
    "inventory_staff",
    "purchase_manager",
    "finance_staff",
    name="selected_workspace_enum",
)
ACTION_SOURCE_ENUM = sa.Enum("UI", "API", "SYSTEM", "ML_ENGINE", name="action_source_enum")
LIFECYCLE_STAGE_ENUM = sa.Enum(
    "Introduction",
    "Growth",
    "Maturity",
    "Decline",
    "Discontinued",
    name="lifecycle_stage_enum",
)
AUDIT_OUTCOME_ENUM = sa.Enum("SUCCESS", "FAILURE", "REJECTED", name="audit_outcome_enum")
AUDIT_TIER_ENUM = sa.Enum(
    "TIER_1_FAIL_CLOSED",
    "TIER_2_OUTBOX_RESILIENT",
    name="audit_tier_enum",
)
OUTBOX_STATUS_ENUM = sa.Enum(
    "pending",
    "retrying",
    "delivered",
    "dead_letter",
    name="outbox_status_enum",
)


def upgrade() -> None:
    # 1. Independent foundation tables
    op.create_table(
        "categories",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("selected_workspace", WORKSPACE_ENUM, nullable=True),
        sa.Column("action_source", ACTION_SOURCE_ENUM, server_default=sa.text("'UI'"), nullable=False),
        sa.Column("operator_ref", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("idx_categories_active", "categories", ["is_active"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp",
            mysql.DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("outcome", AUDIT_OUTCOME_ENUM, nullable=False),
        sa.Column("audit_tier", AUDIT_TIER_ENUM, nullable=False),
        sa.Column("action_source", ACTION_SOURCE_ENUM, nullable=False),
        sa.Column("selected_workspace", WORKSPACE_ENUM, nullable=True),
        sa.Column("operator_ref", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("before_values", sa.JSON(), nullable=True),
        sa.Column("after_values", sa.JSON(), nullable=True),
        sa.Column("error_summary", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_audit_idempotency"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("idx_audit_timestamp", "audit_logs", ["timestamp"], unique=False)
    op.create_index("idx_audit_module_action", "audit_logs", ["module", "action", "timestamp"], unique=False)
    op.create_index("idx_audit_entity", "audit_logs", ["entity_type", "entity_id", "timestamp"], unique=False)
    op.create_index("idx_audit_workspace", "audit_logs", ["selected_workspace", "timestamp"], unique=False)
    op.create_index("idx_audit_outcome", "audit_logs", ["outcome", "timestamp"], unique=False)
    op.create_index("idx_audit_correlation", "audit_logs", ["correlation_id"], unique=False)

    op.create_table(
        "audit_outbox",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("next_retry_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("status", OUTBOX_STATUS_ENUM, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "retry_count >= 0 AND max_retries >= 1 AND retry_count <= max_retries",
            name="chk_outbox_retry",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_outbox_idempotency"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "idx_outbox_dispatch",
        "audit_outbox",
        ["status", "next_retry_at", "created_at"],
        unique=False,
    )
    op.create_index("idx_outbox_correlation", "audit_outbox", ["correlation_id"], unique=False)

    # 2. Catalog tier (depends on categories)
    op.create_table(
        "products",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("stock_code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("category_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("base_uom", sa.String(length=32), server_default=sa.text("'unit'"), nullable=False),
        sa.Column("allow_fractional_qty", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "current_unit_price",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column("currency_code", sa.CHAR(length=3), server_default=sa.text("'INR'"), nullable=False),
        sa.Column(
            "lifecycle_stage",
            LIFECYCLE_STAGE_ENUM,
            server_default=sa.text("'Introduction'"),
            nullable=False,
        ),
        sa.Column("is_uci_baseline", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("selected_workspace", WORKSPACE_ENUM, nullable=True),
        sa.Column("action_source", ACTION_SOURCE_ENUM, server_default=sa.text("'UI'"), nullable=False),
        sa.Column("operator_ref", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("current_unit_price >= 0.00", name="chk_products_price_nonneg"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name="fk_products_category", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_code", name="uq_products_stock_code"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("idx_products_category_active", "products", ["category_id", "is_active"], unique=False)
    op.create_index("idx_products_lifecycle", "products", ["lifecycle_stage"], unique=False)
    op.create_index("idx_products_uci", "products", ["is_uci_baseline"], unique=False)

    # 3. Product-dependent tables (uom_conversions and M09 inventory)
    op.create_table(
        "uom_conversions",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("product_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("uom_code", sa.String(length=32), nullable=False),
        sa.Column("conversion_to_base", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column(
            "effective_from",
            mysql.DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column("effective_to", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "active_product_id",
            mysql.BIGINT(unsigned=True),
            sa.Computed("IF(is_active = TRUE, product_id, NULL)", persisted=False),
            nullable=True,
        ),
        sa.Column(
            "active_uom_code",
            sa.String(length=32),
            sa.Computed("IF(is_active = TRUE, uom_code, NULL)", persisted=False),
            nullable=True,
        ),
        sa.Column("selected_workspace", WORKSPACE_ENUM, nullable=True),
        sa.Column("action_source", ACTION_SOURCE_ENUM, server_default=sa.text("'UI'"), nullable=False),
        sa.Column("operator_ref", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.CheckConstraint("conversion_to_base > 0.000000", name="chk_uom_factor_pos"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_uom_effective_window",
        ),
        sa.CheckConstraint(
            "is_active = TRUE OR effective_to IS NOT NULL",
            name="chk_uom_inactive_closed",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_uom_product", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "uom_code", "effective_from", name="uq_uom_product_code_eff"),
        sa.UniqueConstraint("active_product_id", "active_uom_code", name="uq_uom_one_active"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "idx_uom_lookup",
        "uom_conversions",
        ["product_id", "uom_code", "is_active", "effective_from"],
        unique=False,
    )

    op.create_table(
        "inventory",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("product_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column(
            "current_quantity",
            sa.Numeric(precision=14, scale=4),
            server_default=sa.text("0.0000"),
            nullable=False,
        ),
        sa.Column(
            "reserved_quantity",
            sa.Numeric(precision=14, scale=4),
            server_default=sa.text("0.0000"),
            nullable=False,
        ),
        sa.Column(
            "minimum_stock",
            sa.Numeric(precision=14, scale=4),
            server_default=sa.text("10.0000"),
            nullable=False,
        ),
        sa.Column(
            "safety_factor",
            sa.Numeric(precision=4, scale=2),
            server_default=sa.text("1.20"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.CheckConstraint("current_quantity >= 0.0000", name="chk_inv_phys_nonneg"),
        sa.CheckConstraint("reserved_quantity >= 0.0000", name="chk_inv_res_nonneg"),
        sa.CheckConstraint("reserved_quantity <= current_quantity", name="chk_inv_avail_nonneg"),
        sa.CheckConstraint("minimum_stock >= 0.0000", name="chk_inv_min_stock"),
        sa.CheckConstraint("safety_factor >= 1.00", name="chk_inv_safety_factor"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_inventory_product", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", name="uq_inventory_product"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )


def downgrade() -> None:
    op.drop_table("inventory")
    op.drop_index("idx_uom_lookup", table_name="uom_conversions")
    op.drop_table("uom_conversions")
    op.drop_index("idx_products_uci", table_name="products")
    op.drop_index("idx_products_lifecycle", table_name="products")
    op.drop_index("idx_products_category_active", table_name="products")
    op.drop_table("products")
    op.drop_index("idx_outbox_correlation", table_name="audit_outbox")
    op.drop_index("idx_outbox_dispatch", table_name="audit_outbox")
    op.drop_table("audit_outbox")
    op.drop_index("idx_audit_correlation", table_name="audit_logs")
    op.drop_index("idx_audit_outcome", table_name="audit_logs")
    op.drop_index("idx_audit_workspace", table_name="audit_logs")
    op.drop_index("idx_audit_entity", table_name="audit_logs")
    op.drop_index("idx_audit_module_action", table_name="audit_logs")
    op.drop_index("idx_audit_timestamp", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("idx_categories_active", table_name="categories")
    op.drop_table("categories")
