"""Pydantic models for daily newspaper editions.

The paper pipeline's orchestrating agent writes edition.json; these models
are the contract that gets validated IN CODE before anything downstream
happens (email send, web build, commit). A malformed edition fails the run
loudly instead of shipping a half-broken paper.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EditionSource(BaseModel):
    url: str
    title: str = ""
    domain: str = ""
    reliability_tier: str = "unknown"


class EditionItem(BaseModel):
    headline: str
    body: str = Field(description="2-4 sentence briefing on what happened")
    so_what: str = Field(default="", description="Why this matters to the reader specifically")
    sources: list[EditionSource] = Field(default_factory=list)
    related_slug: str = Field(
        default="", description="Slug of a related library project, if any"
    )


class EditionSection(BaseModel):
    id: str
    title: str
    items: list[EditionItem] = Field(default_factory=list)


class Edition(BaseModel):
    date: str = Field(description="ISO date of this edition, YYYY-MM-DD")
    headline: str = Field(description="The single most important takeaway of the day")
    overview: str = Field(default="", description="2-3 sentence front-page summary")
    sections: list[EditionSection] = Field(default_factory=list)
    refresh_recommendations: list[str] = Field(
        default_factory=list,
        description="Library project slugs that look stale and deserve a full research refresh",
    )

    def section(self, section_id: str) -> EditionSection | None:
        for s in self.sections:
            if s.id == section_id:
                return s
        return None
