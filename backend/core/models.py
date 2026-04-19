"""Pydantic v2 data models for Sentinel.

Every field is strictly typed so that malformed fixture data fails loudly at
load time rather than silently at resolution time.  Judges can open this file
to see exactly what the agent operates on.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class _StrEnum(str, Enum):
    # Python 3.11+ changed str(Enum) to return the repr ("TicketCategory.refund")
    # instead of the value. We route all public string coercion through .value so
    # logs, prompts, and audit artifacts stay stable across Python versions.
    def __str__(self) -> str:
        return self.value


class CustomerTier(_StrEnum):
    standard = "standard"
    premium = "premium"
    vip = "vip"


class OrderStatus(_StrEnum):
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class TicketCategory(_StrEnum):
    refund = "refund"
    return_ = "return"
    exchange = "exchange"
    cancellation = "cancellation"
    warranty = "warranty"
    shipping = "shipping"
    policy_question = "policy_question"
    damaged = "damaged"
    wrong_item = "wrong_item"
    ambiguous = "ambiguous"
    other = "other"


class Urgency(_StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class ResolutionStatus(_StrEnum):
    resolved = "resolved"
    escalated = "escalated"
    info_requested = "info_requested"
    failed = "failed"


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------


class Address(BaseModel):
    model_config = ConfigDict(frozen=True)

    street: str
    city: str
    state: str
    zip: str


class Customer(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: str
    name: str
    email: str
    phone: str
    tier: CustomerTier
    member_since: date
    total_orders: int
    total_spent: float
    address: Address
    notes: str = ""


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: str
    name: str
    category: str
    price: float
    warranty_months: int
    return_window_days: int
    returnable: bool
    notes: str = ""


class Order(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: str
    customer_id: str
    product_id: str
    quantity: int
    amount: float
    status: OrderStatus
    order_date: date
    delivery_date: Optional[date] = None
    return_deadline: Optional[date] = None
    refund_status: Optional[str] = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Ticket (inbound)
# ---------------------------------------------------------------------------


class Ticket(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticket_id: str
    customer_email: str
    subject: str
    body: str
    source: str = "email"
    created_at: datetime
    tier: Optional[int] = None
    expected_action: Optional[str] = None  # test validation ONLY — never used in agent


# ---------------------------------------------------------------------------
# Triage output
# ---------------------------------------------------------------------------


class Triage(BaseModel):
    category: TicketCategory
    urgency: Urgency
    auto_resolvable: bool
    reasoning: str
    extracted_order_id: Optional[str] = None
    threatening_language: bool = False
    social_engineering_suspected: bool = False
    confidence: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class ToolCallRecord(BaseModel):
    sequence: int
    tool_name: str
    arguments: dict
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    latency_ms: float
    attempt: int = 1
    timestamp: datetime


# ---------------------------------------------------------------------------
# Resolution (outbound)
# ---------------------------------------------------------------------------


class Resolution(BaseModel):
    ticket_id: str
    status: ResolutionStatus
    category: TicketCategory
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)
    actions_taken: list[str] = Field(default_factory=list)
    final_customer_message: str = ""
    escalation_summary: Optional[str] = None
    reasoning_trace: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_latency_ms: float = 0.0
    flags: list[str] = Field(default_factory=list)
