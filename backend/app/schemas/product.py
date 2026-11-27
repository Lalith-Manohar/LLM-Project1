"""Pydantic v2 schemas for M01 Product Management and UoM Conversions."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.category import ActionSourceLiteral, WorkspaceLiteral
from app.services.quantity_validation import QuantityValidationError, parse_exact_decimal


def _strip_required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty or whitespace.")
    return cleaned


def _normalize_stock_code(value: str) -> str:
    cleaned = _strip_required_text(value, "stock_code").upper()
    if any(ch.isspace() for ch in cleaned):
        raise ValueError("stock_code cannot contain whitespace characters.")
    return cleaned


class ProductCreate(BaseModel):
    """Request schema for creating a master SKU product."""

    stock_code: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=255)
    category_id: Optional[int] = Field(default=None, ge=1)
    base_uom: str = Field(default="unit", min_length=1, max_length=32)
    allow_fractional_qty: bool = False
    current_unit_price: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )
    currency_code: str = Field(default="INR", min_length=3, max_length=3)
    is_uci_baseline: bool = False
    selected_workspace: Optional[WorkspaceLiteral] = None
    action_source: ActionSourceLiteral = "UI"
    operator_ref: Optional[str] = Field(default=None, max_length=64)

    @field_validator("stock_code")
    @classmethod
    def validate_stock_code(cls, value: str) -> str:
        return _normalize_stock_code(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        return _strip_required_text(value, "description")

    @field_validator("base_uom")
    @classmethod
    def validate_base_uom(cls, value: str) -> str:
        return _strip_required_text(value, "base_uom")

    @field_validator("currency_code")
    @classmethod
    def validate_currency_code(cls, value: str) -> str:
        return _strip_required_text(value, "currency_code").upper()


class ProductUpdate(BaseModel):
    """Request schema for updating an existing product."""

    description: str = Field(..., min_length=1, max_length=255)
    category_id: Optional[int] = Field(default=None, ge=1)
    base_uom: Optional[str] = Field(default=None, min_length=1, max_length=32)
    allow_fractional_qty: Optional[bool] = None
    current_unit_price: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )
    selected_workspace: Optional[WorkspaceLiteral] = None
    action_source: ActionSourceLiteral = "UI"
    operator_ref: Optional[str] = Field(default=None, max_length=64)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        return _strip_required_text(value, "description")

    @field_validator("base_uom")
    @classmethod
    def validate_base_uom(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _strip_required_text(value, "base_uom")


class ProductStatusUpdate(BaseModel):
    """Request schema for soft-activating or soft-deactivating a product."""

    is_active: bool
    selected_workspace: Optional[WorkspaceLiteral] = None
    action_source: ActionSourceLiteral = "UI"
    operator_ref: Optional[str] = Field(default=None, max_length=64)


class ProductResponse(BaseModel):
    """Response schema representing a persisted master product."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_code: str
    description: str
    category_id: Optional[int] = None
    base_uom: str
    allow_fractional_qty: bool
    current_unit_price: Decimal
    currency_code: str
    lifecycle_stage: str
    is_uci_baseline: bool
    is_active: bool
    selected_workspace: Optional[str] = None
    action_source: str
    operator_ref: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaginatedProductResponse(BaseModel):
    """Documented pagination envelope for product catalog listings."""

    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UomConversionCreate(BaseModel):
    """Request schema for immediate operational UoM conversion rollover (Schema v2.9 Section 6.6)."""

    uom_code: str = Field(..., min_length=1, max_length=32)
    conversion_to_base: Decimal = Field(..., gt=Decimal("0.000000"), max_digits=12, decimal_places=6)
    effective_from: Optional[Any] = None
    effective_to: Optional[Any] = None
    selected_workspace: Optional[WorkspaceLiteral] = None
    action_source: ActionSourceLiteral = "UI"
    operator_ref: Optional[str] = Field(default=None, max_length=64)

    @field_validator("uom_code")
    @classmethod
    def validate_uom_code(cls, value: str) -> str:
        return _strip_required_text(value, "uom_code")

    @field_validator("conversion_to_base", mode="before")
    @classmethod
    def validate_exact_factor(cls, value: Any) -> Decimal:
        try:
            parsed = parse_exact_decimal(value)
        except QuantityValidationError as exc:
            raise ValueError(str(exc)) from exc
        if parsed <= Decimal("0"):
            raise ValueError("conversion_to_base must be strictly greater than zero.")
        return parsed

    @field_validator("effective_from", "effective_to")
    @classmethod
    def reject_caller_timestamps(cls, value: Optional[Any]) -> None:
        if value is not None:
            raise ValueError(
                "Caller-supplied effective_from/effective_to timestamps are prohibited; "
                "operational UoM rollovers take effect immediately at server time."
            )
        return None


class UomConversionResponse(BaseModel):
    """Response schema representing an effective-dated UoM conversion version."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    uom_code: str
    conversion_to_base: Decimal
    effective_from: datetime
    effective_to: Optional[datetime] = None
    is_active: bool
    selected_workspace: Optional[str] = None
    action_source: str
    operator_ref: Optional[str] = None
    created_at: datetime
