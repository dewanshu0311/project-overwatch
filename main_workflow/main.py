"""
Main entry point — CLI interface for the intelligence pipeline.

Modes:
  --mock       : Loads fixture data BUT still uses live LLM + tools.
  --fast-demo  : Fixture-seeded fast path using the lighter model profile.
  --dashboard  : Enables the Rich terminal dashboard for visual demo.
  --demo       : Combines --fast-demo + --dashboard + HTML export + auto-open.
  --open-report: Auto-opens the HTML report in browser after pipeline completes.
  (no flags)   : Fully live mode — detects real GitHub changes.
"""
import argparse
import json
import os
import re
import sys
import time

# Force UTF-8 output to prevent CrewAI's internal emojis from crashing on Windows cp1252
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from crewai import Crew, Process
from rich.console import Console

from .config import TARGET_REPOS, MOCK_FIXTURE, CONFIDENCE_THRESHOLD
from .state_manager import check_for_changes
from .tasks import monitor_task, signal_gathering_task, research_task, analysis_task, red_team_task, verification_task
from .self_correction_loop import run_with_self_correction
from .tools import (
    slack_alert_tool,
    github_monitor_tool,
    deep_scrape_tool,
    hackernews_signal_tool,
    pypi_stats_tool,
)

console = Console()


def _compact_monitor_seed(seed_text: str) -> str:
    """Keep only the highest-signal current evidence lines for downstream prompts."""
    lines = [
        line.strip()
        for line in (seed_text or "").splitlines()
        if line.strip() and ("https://" in line or line.startswith("Repository:"))
    ]
    compact = "\n".join(lines[:6])
    return compact or "Current monitor evidence unavailable."


def _extract_urls(text: str) -> list[str]:
    """Extract URLs from tool output."""
    return [match.rstrip(".,;)") for match in re.findall(r"https?://\S+", text or "")]


def _build_research_seed(repo: str, monitor_text: str) -> str:
    """Prefetch the highest-value research evidence from the current monitor output."""
    urls = _extract_urls(monitor_text)
    file_urls = [url for url in urls if "/blob/" in url]
    ranked_file_urls = sorted(
        file_urls,
        key=lambda url: (
            0 if any(token in url.lower() for token in ("/auth/", "_client.py", "/client/")) else
            1 if any(token in url.lower() for token in ("changelog.md", "/releases")) else
            2 if "_version.py" in url.lower() else
            3
        ),
    )
    candidate_urls = [f"https://github.com/{repo}/releases"]
    if ranked_file_urls:
        candidate_urls.append(ranked_file_urls[0])

    evidence_chunks = []
    for url in candidate_urls[:2]:
        try:
            evidence_chunks.append(f"Source: {url}\n{deep_scrape_tool.run(url)}")
        except Exception:
            continue

    return "\n\n".join(evidence_chunks)[:4000] or "Current research evidence unavailable."


def _guess_package_name(repo: str) -> str:
    """Infer the likely PyPI package name from a repo slug."""
    package = repo.split("/")[-1] if "/" in repo else repo
    for suffix in ("-sdk-python", "-python", "_python"):
        if package.endswith(suffix):
            trimmed = package[: -len(suffix)]
            if trimmed:
                return trimmed
    return package


def _build_signal_seed(repo: str) -> str:
    """Prefetch ecosystem signals so the signal stage can focus on synthesis."""
    package_name = _guess_package_name(repo)
    evidence_chunks = [
        hackernews_signal_tool.run(repo.split("/")[-1] if "/" in repo else repo),
        pypi_stats_tool.run(package_name),
    ]
    return "\n".join(chunk for chunk in evidence_chunks if chunk)[:2000] or "Current signal evidence unavailable."


def _build_memory_seed(repo: str) -> str:
    """Prefetch validated historical memory so the analyst does not loop on tool calls."""
    try:
        from .memory import CognitiveMemory

        mem = CognitiveMemory()
        return mem.query_history(
            query=f"architecture changes in {repo}",
            repo=repo,
            n_results=2,
        )[:2000]
    except Exception:
        return "No validated historical data."


def _build_crew(context: dict, fast: bool = False) -> Crew:
    """Build the 6-agent sequential crew from context.

    Pipeline: Monitor → Signal → Researcher → Analyst → Red Team → Verifier

    Args:
        context: dict with repo, changes, scraped_content, correction_feedback
        fast: if True, increase max_rpm for faster demo execution
    """
    t_monitor = monitor_task(context)
    t_signal = signal_gathering_task(context, t_monitor)
    t_research = research_task(context, t_monitor, t_signal)
    t_analysis = analysis_task(context, t_research)
    t_red_team = red_team_task(context, t_analysis)
    t_verify = verification_task(context, t_analysis, t_red_team)

    return Crew(
        agents=[
            t_monitor.agent, t_signal.agent, t_research.agent,
            t_analysis.agent, t_red_team.agent, t_verify.agent,
        ],
        tasks=[t_monitor, t_signal, t_research, t_analysis, t_red_team, t_verify],
        process=Process.sequential,
        verbose=True,
        max_rpm=30 if fast else 10,
    )


def run_pipeline(
    mock: bool = False,
    fast_demo: bool = False,
    dashboard: bool = False,
    open_report: bool = False,
) -> None:
    """Execute the full intelligence pipeline.

    Args:
        mock: load fixture data (still uses live LLM + tools for reasoning)
        fast_demo: fixture-seeded fast path using the lighter model profile
        dashboard: enable Rich terminal dashboard for visual demo
        open_report: auto-open HTML report in browser after completion
    """
    start_time = time.time()

    # Determine mode label
    if fast_demo:
        mode = "fast-demo"
    elif mock:
        mode = "mock"
    else:
        mode = "live"

    # Load context
    if mock or fast_demo:
        with open(MOCK_FIXTURE, "r") as f:
            mock_data = json.load(f)
        context = {
            "repo": mock_data["repo"],
            "changes": mock_data["changed_files"],
            "scraped_content": mock_data["scraped_content"],
        }
    else:
        context = None
        for repo in TARGET_REPOS:
            result = check_for_changes(repo)
            if result.get("changed"):
                degraded = result.get("degraded", False)
                if degraded:
                    console.print("[yellow]Running with degraded perception (no GitHub token)[/yellow]")
                context = {
                    "repo": repo,
                    "changes": [f"SHA: {result['latest_sha']}"],
                    "scraped_content": "Deep research needed.",
                }
                break
        if context is None:
            console.print("No changes detected. Exiting.")
            return

    repo = context.get("repo", "unknown")

    try:
        raw_monitor_seed = github_monitor_tool.run(repo)
        context["monitor_seed"] = _compact_monitor_seed(raw_monitor_seed)
        context["research_seed"] = _build_research_seed(repo, raw_monitor_seed)
        context["signal_seed"] = _build_signal_seed(repo)
        context["memory_seed"] = _build_memory_seed(repo)
        os.environ["OVERWATCH_PREFETCH_MONITOR"] = "1"
        os.environ["OVERWATCH_PREFETCH_RESEARCH"] = "1"
        os.environ["OVERWATCH_PREFETCH_SIGNAL"] = "1"
        os.environ["OVERWATCH_PREFETCH_MEMORY"] = "1"
    except Exception as e:
        console.print(f"[yellow]Monitor seed generation failed: {e}[/yellow]")
        context["monitor_seed"] = "Current monitor evidence unavailable."
        context["research_seed"] = "Current research evidence unavailable."
        context["signal_seed"] = "Current signal evidence unavailable."
        context["memory_seed"] = "No validated historical data."
        os.environ["OVERWATCH_PREFETCH_MONITOR"] = "0"
        os.environ["OVERWATCH_PREFETCH_RESEARCH"] = "0"
        os.environ["OVERWATCH_PREFETCH_SIGNAL"] = "0"
        os.environ["OVERWATCH_PREFETCH_MEMORY"] = "0"

    # Use a lighter model profile for fast-demo reliability under free-tier limits.
    os.environ["OVERWATCH_MODEL_PROFILE"] = "fast" if fast_demo else "balanced"

    # Dashboard: show header and pipeline
    dashboard_cb = None
    if dashboard:
        from .demo_ui import (
            show_header, show_pipeline_diagram,
            show_attempt_start, show_attempt_result, show_evidence_preview,
        )
        from .key_manager import get_key_pool_status
        groq_status = get_key_pool_status("GROQ")
        fc_status = get_key_pool_status("FIRECRAWL")
        show_header(mode, repo, groq_status["total_keys"], fc_status["total_keys"])
        show_pipeline_diagram(include_red_team=True)
        show_evidence_preview(context)

        # Build callback dict for self-correction loop
        dashboard_cb = {
            "attempt_start": show_attempt_start,
            "attempt_result": lambda ok, conf, errs, rl=False: show_attempt_result(ok, conf, errs, rl),
            "attempt_history": [],
        }
    else:
        console.print(f"[yellow]Loading {mode} mode...[/yellow]")

    console.print("[blue]Starting crew with self-correction loop...[/blue]")

    # Build crew factory
    def crew_factory(ctx):
        return _build_crew(ctx, fast=fast_demo)

    # Track attempts for final report
    report = run_with_self_correction(crew_factory, context, dashboard_callback=dashboard_cb)
    attempts_used = dashboard_cb.get("attempts_used", 1) if dashboard_cb else 1

    elapsed = time.time() - start_time

    if report is not None:
        # Deliver via Slack (or fallback)
        delivery_result = slack_alert_tool.run(report.summary)

        # Store in memory
        memory_stored = False
        total_reports = 0
        try:
            report_is_valid = (
                not report.requires_retry
                and report.confidence_score >= CONFIDENCE_THRESHOLD
                and bool(report.cited_sources)
                and bool(report.architecture_changes)
            )
            if report_is_valid:
                from .memory import CognitiveMemory
                mem = CognitiveMemory()
                mem.store_report(report, repo)
                memory_stored = True
                total_reports = mem.get_report_count()
            else:
                console.print("[yellow]Skipping memory storage for non-validated report.[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Memory storage failed: {e}[/yellow]")

        # Dashboard: show final report
        if dashboard:
            from .demo_ui import show_final_report, show_delivery_status, show_memory_status
            show_final_report(
                report,
                elapsed,
                repo,
                mode,
                attempts_used=attempts_used,
                attempt_history=dashboard_cb.get("attempt_history", []),
            )
            slack_ok = "successfully" in delivery_result.lower()
            show_delivery_status(
                "Slack" if slack_ok else "Fallback File",
                slack_ok,
                delivery_result,
            )
            show_memory_status(memory_stored, total_reports)
        else:
            console.print("[green]Delivering report...[/green]")

        # HTML export (always when report succeeds)
        try:
            from .report_export import export_html_report
            html_path = export_html_report(report, repo, mode, elapsed)
            console.print(f"[green]HTML report exported: {html_path}[/green]")
            if open_report:
                import webbrowser
                webbrowser.open(str(html_path))
        except ImportError:
            pass  # Graceful skip if report export cannot be imported.
        except Exception as e:
            console.print(f"[yellow]HTML export failed: {e}[/yellow]")

    console.print(f"Completed in {elapsed:.1f}s")


def main() -> None:
    """CLI entry point with all mode flags."""
    parser = argparse.ArgumentParser(description="Project Overwatch — Autonomous Competitive Intelligence")
    parser.add_argument("--mock", action="store_true", help="Load fixture data (live LLM + tools still active)")
    parser.add_argument(
        "--fast-demo",
        action="store_true",
        help="Use fixture-seeded context plus the fast model profile",
    )
    parser.add_argument("--dashboard", action="store_true", help="Enable Rich terminal dashboard")
    parser.add_argument("--open-report", action="store_true", help="Auto-open HTML report in browser")
    parser.add_argument("--demo", action="store_true", help="Full demo mode: fast-demo + dashboard + export + open")
    args = parser.parse_args()

    # --demo implies all presentation features
    if args.demo:
        args.fast_demo = True
        args.dashboard = True
        args.open_report = True

    try:
        run_pipeline(
            mock=args.mock,
            fast_demo=args.fast_demo,
            dashboard=args.dashboard,
            open_report=args.open_report,
        )
    except KeyboardInterrupt:
        console.print("Interrupted by user.")
    except Exception as e:
        console.print(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
