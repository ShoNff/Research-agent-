"""Source reliability data models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ReliabilityTier(str, Enum):
    ESTABLISHED = "established"
    REPUTABLE = "reputable"
    EMERGING = "emerging"
    OPINION = "opinion"
    UNKNOWN = "unknown"


class SourceMetadata(BaseModel):
    url: str
    title: str
    domain: str
    snippet: str = ""
    reliability_tier: ReliabilityTier = ReliabilityTier.UNKNOWN
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    date_published: str | None = None
    reasoning: str = ""


class Finding(BaseModel):
    question: str
    summary: str
    details: str
    sources: list[SourceMetadata]
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
