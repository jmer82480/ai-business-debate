"""Shared types used across all schema modules."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Evidence(BaseModel):
    """A sourced claim with the mandatory evidence standard."""

    claim: str
    source: str = Field(description="URL, publication, or 'UNSOURCED ESTIMATE'")
    date: str = Field(description="Date of source or 'undated'")
    key_assumption: str
    confidence: ConfidenceLevel


class CostLineItem(BaseModel):
    """A single line item in a startup cost breakdown."""

    item: str
    cost_usd: float = Field(ge=0)
    notes: str = ""
