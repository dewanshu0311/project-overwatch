"""
Pydantic schemas for the Agentic pipeline.

This enforces the IntelligenceReport structure, acting as the strict
typing gate between the Analyst and the Verifier.
"""
import re
from typing import List
from pydantic import BaseModel, Field, field_validator, model_validator


_CHANGE_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "of", "to", "in", "with",
    "added", "add", "support", "supports", "supporting", "improved",
    "improvement", "improves", "enhanced", "enhancement", "better",
    "new", "updates", "updated", "change", "changes", "client",
}


def _semantic_overlap(left: str, right: str) -> float:
    """Approximate semantic overlap without another model call."""
    left_tokens = {
        token for token in re.findall(r"[a-z0-9_]+", left.lower())
        if token not in _CHANGE_STOPWORDS
    }
    right_tokens = {
        token for token in re.findall(r"[a-z0-9_]+", right.lower())
        if token not in _CHANGE_STOPWORDS
    }
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))


def _clean_change_text(text: str) -> str:
    """Remove formatting artifacts that make architecture changes look LLM-shaped."""
    cleaned = re.sub(r"`https?://[^`]+`", "", text)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:;,.")
    return cleaned

class IntelligenceReport(BaseModel):
    """
    The final, structured competitive intelligence report.
    Must be fully populated by the CrewAI Verifier agent.
    """
    summary: str = Field(..., description="A 2-3 sentence executive summary of the changes detected.")
    architecture_changes: List[str] = Field(..., description="A list of specific architectural shifts or API changes.")
    cited_sources: List[str] = Field(..., description="A list of full URLs to GitHub commits, PRs, or release notes backing up the claims.")
    confidence_score: float = Field(..., description="A score between 0.0 and 1.0 indicating how confident the agent is in this analysis.", ge=0.0, le=1.0)
    requires_retry: bool = Field(False, description="Set to True if the agent hallucinates, lacks sources, or has low confidence.")
    missing_information: str = Field("", description="If requires_retry is True, explain what information is missing.")

    @field_validator("summary", mode="before")
    @classmethod
    def _normalize_summary(cls, value):
        text = re.sub(r"\s+", " ", str(value or "")).strip().strip('"')
        for marker in ("ACCEPTED_CLAIMS", "CHALLENGED_CLAIMS", "MISSING_EVIDENCE", "VERDICT"):
            text = text.replace(marker, "")
        return text[:600]

    @field_validator("architecture_changes", mode="before")
    @classmethod
    def _normalize_architecture_changes(cls, value):
        cleaned = []
        seen = set()
        for item in value or []:
            text = re.sub(r"\s+", " ", str(item or "")).strip()
            text = re.sub(r"^[\-\*\d\.\)\s]+", "", text)
            text = _clean_change_text(text)
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            if any(_semantic_overlap(text, existing) >= 0.6 for existing in cleaned):
                continue
            seen.add(key)
            cleaned.append(text)
        return cleaned[:3]

    @field_validator("cited_sources", mode="before")
    @classmethod
    def _normalize_cited_sources(cls, value):
        cleaned = []
        seen = set()
        for item in value or []:
            url = str(item or "").strip().rstrip(".,;")
            if not url:
                continue
            key = url.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(url)
        return cleaned[:6]

    @model_validator(mode="after")
    def _normalize_retry_fields(self):
        if self.requires_retry:
            self.missing_information = re.sub(r"\s+", " ", self.missing_information or "").strip()
            if not self.missing_information:
                self.missing_information = (
                    "The report still needs stronger current evidence for one or more claims."
                )
        else:
            self.missing_information = ""
        return self
