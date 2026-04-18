"""
Main entry point - CLI interface for the intelligence pipeline.

Modes:
  --mock        : Loads fixture data but still uses live LLM + tools.
  --fast-demo   : Fixture-seeded fast path using the lighter model profile.
  --dashboard   : Enables the Rich terminal dashboard for visual demo.
  --demo        : Combines --fast-demo + --dashboard + --open-report.
  --repo        : Targets a specific GitHub repository or full GitHub URL.
  --force-analysis: Runs analysis even when no new SHA difference is detected.
  --live-demo   : Combines --dashboard + --open-report + --force-analysis.
  --open-report : Auto-opens the HTML report in the browser after completion.
  (no flags)    : Fully live mode using the repos listed in config.py.
"""
import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

from crewai import Crew, Process
from rich.console import Console

from .config import CONFIDENCE_THRESHOLD, MOCK_FIXTURE, TARGET_REPOS
from .self_correction_loop import run_with_self_correction
from .state_manager import check_for_changes
from .tasks import (
    analysis_task,
    monitor_task,
    red_team_task,
    research_task,
    signal_gathering_task,
    verification_task,
)
from .tools import (
    deep_scrape_tool,
    github_monitor_tool,
    hackernews_signal_tool,
    pypi_stats_tool,
    slack_alert_tool,
)

# Force UTF-8 output to prevent CrewAI's internal emojis from crashing on Windows cp1252
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console()


def _normalize_repo_input(repo_input: str) -> str:
    """Accept owner/name or full GitHub URLs and normalize to owner/name."""
    raw = (repo_input or "").strip()
    if not raw:
        raise ValueError("Repository input cannot be empty.")

    if raw.startswith("git@github.com:"):
        raw = raw.replace("git@github.com:", "", 1)
    if raw.lower().endswith(".git"):
        raw = raw[:-4]

    if re.match(r"^https?://", raw, flags=re.IGNORECASE):
        parsed = urlparse(raw)
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise ValueError("Only GitHub repository URLs are supported.")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise ValueError("GitHub URL must include both owner and repository name.")
        return f"{parts[0]}/{parts[1]}"

    parts = [part for part in raw.strip("/").split("/") if part]
    if len(parts) != 2:
        raise ValueError("Repository must look like owner/name or https://github.com/owner/name")
    return f"{parts[0]}/{parts[1]}"


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


def _context_from_change_result(repo: str, result: dict, force_analysis: bool) -> dict | None:
    """Turn change-detection output into pipeline context."""
    degraded = result.get("degraded", False)
    if degraded:
        console.print("[yellow]Running with degraded perception (no GitHub token)[/yellow]")

    if result.get("changed"):
        latest_sha = result.get("latest_sha", "unknown")
        return {
            "repo": repo,
            "changes": [f"SHA: {latest_sha}"],
            "scraped_content": "Deep research needed.",
        }

    if not force_analysis:
        return None

    latest_sha = result.get("latest_sha") or "current_snapshot"
    reason = result.get("error") or "No new SHA difference detected."
    console.print(
        f"[yellow]Force analysis enabled for {repo}. "
        f"Proceeding with the current repo snapshot despite detection status: {reason}[/yellow]"
    )
    return {
        "repo": repo,
        "changes": [f"SHA: {latest_sha}", "Forced analysis of the current repo snapshot"],
        "scraped_content": "Forced live analysis requested.",
    }


def _build_live_context(repo_override: str | None = None, force_analysis: bool = False) -> dict | None:
    """Build live context from either a specific repo or the configured target list."""
    repos_to_check = [repo_override] if repo_override else TARGET_REPOS
    fallback_candidate: tuple[str, dict] | None = None

    for index, repo in enumerate(repos_to_check):
        result = check_for_changes(repo)
        if index == 0:
            fallback_candidate = (repo, result)

        context = _context_from_change_result(repo, result, force_analysis=False)
        if context is not None:
            return context

    if force_analysis and fallback_candidate is not None:
        repo, result = fallback_candidate
        return _context_from_change_result(repo, result, force_analysis=True)

    if repo_override:
        console.print(
            f"[yellow]No changes detected for {repo_override}. "
            "Re-run with --force-analysis or --live-demo to analyze the current repo snapshot anyway.[/yellow]"
        )
    else:
        console.print(
            "[yellow]No changes detected in configured target repos. "
            "Use --force-analysis, --live-demo, or --repo owner/name to inspect a repo anyway.[/yellow]"
        )
    return None


def _build_crew(context: dict, fast: bool = False) -> Crew:
    """Build the 6-agent sequential crew from context.

    Pipeline: Monitor -> Signal -> Researcher -> Analyst -> Red Team -> Verifier

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
            t_monitor.agent,
            t_signal.agent,
            t_research.agent,
            t_analysis.agent,
            t_red_team.agent,
            t_verify.agent,
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
    repo_override: str | None = None,
    force_analysis: bool = False,
    live_demo: bool = False,
) -> None:
    """Execute the full intelligence pipeline.

    Args:
        mock: load fixture data (still uses live LLM + tools for reasoning)
        fast_demo: fixture-seeded fast path using the lighter model profile
        dashboard: enable Rich terminal dashboard for visual demo
        open_report: auto-open HTML report in browser after completion
        repo_override: optional owner/name or GitHub URL to inspect in live mode
        force_analysis: continue with the current repo snapshot even if no new SHA is detected
        live_demo: judge-friendly live mode shortcut with dashboard + auto-open + force analysis
    """
    start_time = time.time()

    if fast_demo:
        mode = "fast-demo"
    elif mock:
        mode = "mock"
    elif live_demo:
        mode = "live-demo"
    elif repo_override:
        mode = "live-custom"
    else:
        mode = "live"

    if mock or fast_demo:
        with open(MOCK_FIXTURE, "r", encoding="utf-8") as f:
            mock_data = json.load(f)
        context = {
            "repo": mock_data["repo"],
            "changes": mock_data["changed_files"],
            "scraped_content": mock_data["scraped_content"],
        }
    else:
        context = _build_live_context(repo_override=repo_override, force_analysis=force_analysis)
        if context is None:
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

    os.environ["OVERWATCH_MODEL_PROFILE"] = "fast" if fast_demo else "balanced"

    dashboard_cb = None
    if dashboard:
        from .demo_ui import (
            show_attempt_result,
            show_attempt_start,
            show_evidence_preview,
            show_header,
            show_pipeline_diagram,
        )
        from .key_manager import get_key_pool_status

        groq_status = get_key_pool_status("GROQ")
        fc_status = get_key_pool_status("FIRECRAWL")
        show_header(mode, repo, groq_status["total_keys"], fc_status["total_keys"])
        show_pipeline_diagram(include_red_team=True)
        show_evidence_preview(context)
        dashboard_cb = {
            "attempt_start": show_attempt_start,
            "attempt_result": lambda ok, conf, errs, rl=False: show_attempt_result(ok, conf, errs, rl),
            "attempt_history": [],
        }
    else:
        console.print(f"[yellow]Loading {mode} mode...[/yellow]")

    console.print("[blue]Starting crew with self-correction loop...[/blue]")

    def crew_factory(ctx):
        return _build_crew(ctx, fast=fast_demo)

    outcome = run_with_self_correction(crew_factory, context, dashboard_callback=dashboard_cb)
    report = outcome.report
    attempts_used = outcome.attempts_used

    elapsed = time.time() - start_time

    if report is not None and outcome.verified:
        delivery_result = slack_alert_tool.run(report.summary)

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

        if dashboard:
            from .demo_ui import show_delivery_status, show_final_report, show_memory_status

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

        try:
            from .report_export import export_html_report

            html_path = export_html_report(report, repo, mode, elapsed)
            console.print(f"[green]HTML report exported: {html_path}[/green]")
            if open_report:
                import webbrowser

                webbrowser.open(str(html_path))
        except ImportError:
            pass
        except Exception as e:
            console.print(f"[yellow]HTML export failed: {e}[/yellow]")
    elif report is not None:
        if dashboard:
            from .demo_ui import show_run_failure

            show_run_failure(
                outcome.last_errors,
                elapsed,
                repo,
                mode,
                attempts_used=attempts_used,
                attempt_history=dashboard_cb.get("attempt_history", []) if dashboard_cb else [],
                report=report,
            )
        else:
            console.print("[bold red]Run failed validation after all retries.[/bold red]")
            for error in outcome.last_errors:
                console.print(f"[red]- {error}[/red]")
            console.print("[yellow]Best-effort draft was not delivered, exported, or stored.[/yellow]")
    else:
        if dashboard:
            from .demo_ui import show_run_failure

            show_run_failure(
                outcome.last_errors,
                elapsed,
                repo,
                mode,
                attempts_used=attempts_used,
                attempt_history=dashboard_cb.get("attempt_history", []) if dashboard_cb else [],
                report=None,
            )
        else:
            console.print("[bold red]Run failed before producing a usable report.[/bold red]")
            for error in outcome.last_errors:
                console.print(f"[red]- {error}[/red]")

    console.print(f"Completed in {elapsed:.1f}s")


def main() -> None:
    """CLI entry point with all mode flags."""
    parser = argparse.ArgumentParser(description="Project Overwatch - Autonomous Competitive Intelligence")
    parser.add_argument("--mock", action="store_true", help="Load fixture data (live LLM + tools still active)")
    parser.add_argument(
        "--fast-demo",
        action="store_true",
        help="Use fixture-seeded context plus the fast model profile",
    )
    parser.add_argument("--dashboard", action="store_true", help="Enable Rich terminal dashboard")
    parser.add_argument("--open-report", action="store_true", help="Auto-open HTML report in browser")
    parser.add_argument("--demo", action="store_true", help="Full demo mode: fast-demo + dashboard + open-report")
    parser.add_argument(
        "--repo",
        type=str,
        help="Analyze a specific GitHub repo using owner/name or a full GitHub URL",
    )
    parser.add_argument(
        "--force-analysis",
        action="store_true",
        help="Run analysis even when no new SHA difference is detected",
    )
    parser.add_argument(
        "--live-demo",
        action="store_true",
        help="Live presentation mode: dashboard + open-report + force-analysis",
    )
    args = parser.parse_args()

    if args.repo:
        try:
            args.repo = _normalize_repo_input(args.repo)
        except ValueError as exc:
            parser.error(str(exc))

    if args.repo and (args.mock or args.fast_demo or args.demo):
        parser.error("--repo cannot be combined with --mock, --fast-demo, or --demo. Use live mode or --live-demo instead.")

    if args.force_analysis and (args.mock or args.fast_demo or args.demo):
        parser.error("--force-analysis is only available in live mode or with --live-demo.")

    if args.live_demo and (args.mock or args.fast_demo or args.demo):
        parser.error("--live-demo cannot be combined with --mock, --fast-demo, or --demo.")

    if args.demo:
        args.fast_demo = True
        args.dashboard = True
        args.open_report = True

    if args.live_demo:
        args.dashboard = True
        args.open_report = True
        args.force_analysis = True

    try:
        run_pipeline(
            mock=args.mock,
            fast_demo=args.fast_demo,
            dashboard=args.dashboard,
            open_report=args.open_report,
            repo_override=args.repo,
            force_analysis=args.force_analysis,
            live_demo=args.live_demo,
        )
    except KeyboardInterrupt:
        console.print("Interrupted by user.")
    except Exception as e:
        console.print(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
