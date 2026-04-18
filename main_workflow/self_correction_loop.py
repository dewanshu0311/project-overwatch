"""
Self-Correction Loop - retries with Pydantic validation and automatic key rotation.

Inspired by multi-agent-patterns skill:
  - "Implement retry logic with circuit breakers"
  - "Validate outputs before passing between agents"

On rate limit errors, marks the exhausted key and rotates to next one.
"""
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import urlparse

from crewai import Crew
from rich.console import Console

from .config import CONFIDENCE_THRESHOLD, MAX_RETRIES
from .key_manager import get_key_pool_status, mark_key_exhausted
from .schemas import IntelligenceReport

console = Console()

RETRY_DELAY_SECONDS = 10
_CRITIQUE_TOKENS = ("ACCEPTED_CLAIMS", "CHALLENGED_CLAIMS", "MISSING_EVIDENCE", "VERDICT")


@dataclass
class SelfCorrectionResult:
    """Outcome wrapper for the self-correction loop."""
    report: Optional[IntelligenceReport]
    verified: bool
    attempts_used: int
    last_errors: list[str] = field(default_factory=list)


def _has_precise_source(url: str) -> bool:
    """Return True when the URL points to claim-level evidence, not a generic homepage."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    path = (parsed.path or "").lower()
    return any(
        marker in path
        for marker in (
            "/commit/",
            "/pull/",
            "/blob/",
            "/releases",
            "/compare/",
            "/tag/",
            "/docs/",
        )
    ) or path.endswith(("/readme.md", "/changelog.md", "/api.md", ".md"))


def _extract_urls(text: str) -> list[str]:
    """Extract URLs from a free-form evidence block."""
    return [match.rstrip(".,;)") for match in re.findall(r"https?://\S+", text or "")]


def _source_score(url: str) -> float:
    """Score a source URL by how directly it can support a specific claim."""
    try:
        parsed = urlparse(url)
    except Exception:
        return 0.0

    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    if "github.com" in host:
        if "/commit/" in path:
            return 1.0
        if "/releases" in path or "/compare/" in path or "/tag/" in path:
            return 0.95
        if path.endswith("/changelog.md") or "changelog.md" in path:
            return 0.92
        if "/blob/" in path and "/src/" in path:
            return 0.88
        if "/blob/" in path:
            return 0.8
        if path.endswith("/readme.md") or "readme.md" in path:
            return 0.55
        return 0.3
    if "pypi.org" in host:
        return 0.25
    return 0.2


def _validate_report(report: IntelligenceReport, context: Optional[dict] = None) -> list[str]:
    """Validate report against quality thresholds."""
    failed = []
    context = context or {}

    strong_report_despite_caveats = (
        report.requires_retry
        and report.confidence_score >= 0.8
        and bool(report.cited_sources)
        and len(report.architecture_changes) >= 2
    )
    if report.requires_retry and not strong_report_despite_caveats:
        failed.append(report.missing_information)
    if report.confidence_score < CONFIDENCE_THRESHOLD:
        failed.append(f"Low confidence ({report.confidence_score:.2f} < {CONFIDENCE_THRESHOLD})")

    if not report.cited_sources:
        failed.append("No cited sources")
    else:
        source_scores = [_source_score(url) for url in report.cited_sources]
        average_source_score = sum(source_scores) / len(source_scores)
        if not any(_has_precise_source(url) for url in report.cited_sources):
            failed.append("Cited sources are too generic")
        elif average_source_score < 0.72:
            failed.append(f"Weak source quality (avg score {average_source_score:.2f})")

    current_evidence_urls = (
        _extract_urls(context.get("monitor_seed", ""))
        + _extract_urls(context.get("research_seed", ""))
    )
    if current_evidence_urls and not any(url in current_evidence_urls for url in report.cited_sources):
        failed.append("Cited sources are not tied to the currently detected commit/file evidence")
    if current_evidence_urls:
        drifted_sources = [
            url for url in report.cited_sources
            if url not in current_evidence_urls and _source_score(url) < 0.85
        ]
        if drifted_sources:
            failed.append("Some cited sources drift beyond the current evidence pack")

    if not report.architecture_changes:
        failed.append("No architecture changes listed")
    elif len(report.architecture_changes) < 2:
        failed.append("Need at least 2 distinct architecture changes for a strong final report")
    if len(report.architecture_changes) > 3:
        failed.append("Too many architecture changes; keep only the strongest 2-3")
    if any(token in report.summary for token in _CRITIQUE_TOKENS):
        failed.append("Summary leaked critique formatting")
    return failed


def _handle_rate_limit_error(error_str: str) -> bool:
    """Detect rate limit errors and mark the exhausted key for rotation."""
    lower_error = error_str.lower()
    if "rate_limit" in lower_error or "429" in error_str or "ratelimit" in lower_error:
        match = re.search(r"try again in (\d+\.?\d*)s", error_str)
        cooldown = float(match.group(1)) + 2 if match else 62.0
        mark_key_exhausted("GROQ", "", cooldown_seconds=cooldown)

        status = get_key_pool_status("GROQ")
        console.print(
            f"[yellow]Rate limit detected. "
            f"Available Groq keys: {status['available_keys']}/{status['total_keys']}. "
            f"Rotating...[/yellow]"
        )
        return True
    return False


def run_with_self_correction(
    crew_factory: Callable,
    research_context: dict,
    dashboard_callback: Optional[dict] = None,
) -> SelfCorrectionResult:
    """Run the crew pipeline with automatic self-correction and key rotation."""
    attempt = 0
    context = research_context.copy()
    last_report = None
    last_errors: list[str] = []
    cb = dashboard_callback or {}

    while attempt <= MAX_RETRIES:
        if "attempt_start" in cb:
            cb["attempt_start"](attempt, MAX_RETRIES)
        else:
            console.print(f"\n[bold magenta]--- Attempt {attempt + 1}/{MAX_RETRIES + 1} ---[/bold magenta]")

        try:
            crew = crew_factory(context)
            raw_result = crew.kickoff()

            if hasattr(raw_result, "pydantic_output") and raw_result.pydantic_output:
                report = raw_result.pydantic_output
            elif hasattr(raw_result, "pydantic") and raw_result.pydantic:
                report = raw_result.pydantic
            else:
                raw_str = raw_result.raw if hasattr(raw_result, "raw") else str(raw_result)
                report = IntelligenceReport.model_validate_json(raw_str)

            last_report = report
            failed = _validate_report(report, context)
            last_errors = failed

            if not failed:
                cb["attempts_used"] = attempt + 1
                cb["verified"] = True
                cb["final_errors"] = []
                cb.setdefault("attempt_history", []).append(
                    {
                        "attempt": attempt + 1,
                        "status": "passed",
                        "confidence": report.confidence_score,
                        "reason": "Verification passed",
                    }
                )
                if "attempt_result" in cb:
                    cb["attempt_result"](True, report.confidence_score, [])
                else:
                    console.print("[bold green]Verification Passed![/bold green]")
                return SelfCorrectionResult(
                    report=report,
                    verified=True,
                    attempts_used=attempt + 1,
                    last_errors=[],
                )

            cb.setdefault("attempt_history", []).append(
                {
                    "attempt": attempt + 1,
                    "status": "failed",
                    "confidence": report.confidence_score,
                    "reason": " | ".join(failed),
                }
            )
            if "attempt_result" in cb:
                cb["attempt_result"](False, report.confidence_score, failed)
            else:
                console.print(f"[bold red]Verification Failed: {' | '.join(failed)}[/bold red]")
            context["correction_feedback"] = f"MUST FIX: {' | '.join(failed)}"

        except Exception as e:
            error_str = str(e)
            console.print(f"[bold red]Failure: {error_str[:200]}[/bold red]")
            last_errors = [error_str[:200]]

            was_rate_limit = _handle_rate_limit_error(error_str)
            if was_rate_limit:
                cb.setdefault("attempt_history", []).append(
                    {
                        "attempt": attempt + 1,
                        "status": "rate_limited",
                        "confidence": None,
                        "reason": "Rate limited; rotated API key",
                    }
                )
                if "attempt_result" in cb:
                    cb["attempt_result"](False, None, ["Rate limited"], True)
                context["correction_feedback"] = "RATE_LIMITED: Retrying with rotated API key."
                last_errors = ["Rate limited; rotated API key"]
            else:
                cb.setdefault("attempt_history", []).append(
                    {
                        "attempt": attempt + 1,
                        "status": "crashed",
                        "confidence": None,
                        "reason": error_str[:200],
                    }
                )
                context["correction_feedback"] = f"CRASH: {error_str[:200]}"

        attempt += 1
        if attempt <= MAX_RETRIES:
            console.print(f"[dim]Cooling down {RETRY_DELAY_SECONDS}s before retry...[/dim]")
            time.sleep(RETRY_DELAY_SECONDS)

    console.print("[yellow]Max retries exhausted. No verified report was produced.[/yellow]")
    cb["attempts_used"] = attempt
    cb["verified"] = False
    cb["final_errors"] = last_errors
    return SelfCorrectionResult(
        report=last_report,
        verified=False,
        attempts_used=attempt,
        last_errors=last_errors,
    )
