"""Pydantic v2 schemas for M01 Category Management."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

WorkspaceLiteral = Literal[
    "store_manager",
    "inventory_staff",
    "purchase_manager",
    "finance_staff",
]
ActionSourceLiteral = Literal["UI", "API", "SYSTEM", "ML_ENGINE"]


def _strip_required_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Category name cannot be empty or whitespace.")
    return cleaned


def _strip_optional_description(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


class CategoryCreate(BaseModel):
    """Request schema for creating a new product category."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    selected_workspace: Optional[WorkspaceLiteral] = None
    action_source: ActionSourceLiteral = "UI"
    operator_ref: Optional[str] = Field(default=None, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _strip_required_name(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        return _strip_optional_description(value)


class CategoryUpdate(BaseModel):
    """Request schema for updating an existing product category."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    selected_workspace: Optional[WorkspaceLiteral] = None
    action_source: ActionSourceLiteral = "UI"
    operator_ref: Optional[str] = Field(default=None, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _strip_required_name(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        return _strip_optional_description(value)


class CategoryStatusUpdate(BaseModel):
    """Request schema for soft-activating or soft-deactivating a category."""

    is_active: bool
    selected_workspace: Optional[WorkspaceLiteral] = None
    action_source: ActionSourceLiteral = "UI"
    operator_ref: Optional[str] = Field(default=None, max_length=64)


class CategoryResponse(BaseModel):
    """Response schema representing a persisted product category."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    selected_workspace: Optional[str] = None
    action_source: str
    operator_ref: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaginatedCategoryResponse(BaseModel):
    """Documented pagination envelope for category listings."""

    items: list[CategoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
