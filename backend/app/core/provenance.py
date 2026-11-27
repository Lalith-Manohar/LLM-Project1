"""NEXORA Request Provenance & Non-Authenticated Workspace Context Utilities.

Extracts X-NEXORA-Workspace, X-Correlation-ID, and optional X-NEXORA-Operator-Ref
headers per Technical Blueprint v2.2 (SYS-01) and DATABASE_SCHEMA.md v2.9 Section 2.1.

IMPORTANT:
- Workspace selection is strictly UI operational context and provenance metadata.
- It does NOT represent authentication, identity verification, JWT sessions, or RBAC.
"""

import uuid
from dataclasses import dataclass
from typing import Literal, Optional

from fastapi import Header, HTTPException, status

WorkspaceCode = Literal[
    "store_manager",
    "inventory_staff",
    "purchase_manager",
    "finance_staff",
]
ActionSource = Literal["UI", "API", "SYSTEM", "ML_ENGINE"]

# Maps accepted header values (DB enum keys and Blueprint v2.2 UI labels) to canonical DB enum codes
WORKSPACE_HEADER_MAP: dict[str, WorkspaceCode] = {
    "store_manager": "store_manager",
    "store manager": "store_manager",
    "store manager (admin)": "store_manager",
    "inventory_staff": "inventory_staff",
    "inventory staff": "inventory_staff",
    "purchase_manager": "purchase_manager",
    "purchase manager": "purchase_manager",
    "finance_staff": "finance_staff",
    "finance staff": "finance_staff",
}

WORKSPACE_DISPLAY_LABELS: dict[WorkspaceCode, str] = {
    "store_manager": "Store Manager (Admin)",
    "inventory_staff": "Inventory Staff",
    "purchase_manager": "Purchase Manager",
    "finance_staff": "Finance Staff",
}


@dataclass(frozen=True)
class RequestProvenance:
    """Standardized non-authenticated provenance triad + correlation ID."""

    selected_workspace: Optional[WorkspaceCode]
    action_source: ActionSource
    operator_ref: Optional[str]
    correlation_id: str

    @property
    def workspace_label(self) -> Optional[str]:
        if self.selected_workspace is None:
            return None
        return WORKSPACE_DISPLAY_LABELS[self.selected_workspace]


def normalize_workspace_header(raw_workspace: Optional[str]) -> Optional[WorkspaceCode]:
    """Validates and normalizes X-NEXORA-Workspace header into canonical DB enum code."""
    if raw_workspace is None:
        return None
    cleaned = raw_workspace.strip()
    if not cleaned:
        return None
    normalized = WORKSPACE_HEADER_MAP.get(cleaned.lower())
    if normalized is None:
        allowed = ", ".join(WORKSPACE_DISPLAY_LABELS.values())
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported X-NEXORA-Workspace value '{cleaned}'. "
                f"Approved workspaces: {allowed}."
            ),
        )
    return normalized


def normalize_correlation_id(raw_correlation_id: Optional[str]) -> str:
    """Returns caller-provided correlation ID or generates a deterministic-format prefix ID."""
    if raw_correlation_id is not None:
        cleaned = raw_correlation_id.strip()
        if cleaned:
            return cleaned[:64]
    return f"req-{uuid.uuid4().hex[:12]}"


def normalize_operator_ref(raw_operator_ref: Optional[str]) -> Optional[str]:
    """Normalizes optional non-authenticated operator reference token (max 64 chars)."""
    if raw_operator_ref is None:
        return None
    cleaned = raw_operator_ref.strip()
    if not cleaned:
        return None
    return cleaned[:64]


def get_request_provenance(
    x_nexora_workspace: Optional[str] = Header(default=None, alias="X-NEXORA-Workspace"),
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
    x_nexora_operator_ref: Optional[str] = Header(default=None, alias="X-NEXORA-Operator-Ref"),
) -> RequestProvenance:
    """FastAPI dependency extracting non-authenticated NEXORA request provenance."""
    workspace = normalize_workspace_header(x_nexora_workspace)
    action_source: ActionSource = "UI" if workspace is not None else "API"
    return RequestProvenance(
        selected_workspace=workspace,
        action_source=action_source,
        operator_ref=normalize_operator_ref(x_nexora_operator_ref),
        correlation_id=normalize_correlation_id(x_correlation_id),
    )
