"""Report structure data models."""

from __future__ import annotations

from pydantic import BaseModel

from .source import SourceMetadata


class ReportSection(BaseModel):
    title: str
    content: str
    section_type: str  # executive_summary, finding, analysis, recommendation
    sources: list[SourceMetadata] = []
    diagrams: list[str] = []  # Mermaid source codes


class ReportDraft(BaseModel):
    title: str
    executive_summary: str
    sections: list[ReportSection]
    key_takeaways: list[str]
    sources: list[SourceMetadata]
    diagrams: list[str] = []


class QADimension(BaseModel):
    name: str
    score: float
    feedback: str


class QAReview(BaseModel):
    overall_pass: bool
    dimensions: list[QADimension]
    specific_issues: list[str]
    missing_coverage: list[str]
