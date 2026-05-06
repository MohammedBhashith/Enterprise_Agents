from typing import Literal, Optional
from pydantic import BaseModel, Field


IntentType = Literal[
    "greeting",
    "thanks",
    "bye",
    "policy",
    "apply_leave",
    "leave_balance",
    "leave_history",
    "pending_leaves",
    "cancel_leave",
    "approve_leave",
    "reject_leave",
    "create_ticket",
    "ticket_status",
    "view_all_tickets",
    "assign_ticket",
    "resolve_ticket",
    "request_asset",
    "asset_status",
    "approve_asset_manager",
    "approve_asset_it",
    "inventory_status",
    "memory_query",
    "web_search",
    "out_of_scope",
]


class IntentResult(BaseModel):
    intent: IntentType = Field(description="Detected user intent")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reason: str = Field(description="Short reason for the detected intent")


class LeaveDetails(BaseModel):
    leave_type: Optional[Literal["sick", "casual", "other"]] = Field(default=None)
    start_date: Optional[str] = Field(default=None)
    end_date: Optional[str] = Field(default=None)
    reason: Optional[str] = Field(default=None)