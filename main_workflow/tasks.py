"""
CrewAI Tasks — six sequential tasks forming the intelligence pipeline.

Each task explicitly consumes the detected evidence (changed files, SHA,
scraped content) from the context dict, so agents reason over real data
rather than drifting into generic analysis.
"""
from crewai import Task
from .agents import (
    monitor_agent,
    signal_analyst_agent,
    researcher_agent,
    analyst_agent,
    red_team_agent,
    verifier_agent,
)
from .schemas import IntelligenceReport


def monitor_task(context: dict) -> Task:
    """Task: fetch latest commits from the target repo."""
    repo = context.get("repo", "unknown")
    changes = context.get("changes", [])
    monitor_seed = context.get("monitor_seed", "Current monitor evidence unavailable.")
    feedback = context.get("correction_feedback", "None")
    has_prefetched_seed = monitor_seed != "Current monitor evidence unavailable."
    evidence_instruction = (
        f"Use this prefetched current monitor evidence pack as the source of truth:\n{monitor_seed}\n"
        "Do not call GitHubMonitorTool again unless the prefetched evidence is unavailable.\n"
        if has_prefetched_seed else
        "Use GitHubMonitorTool exactly once.\n"
    )
    return Task(
        description=(
            f"Monitor the {repo} repository for architectural changes.\n"
            f"Known changed files/SHAs: {changes}\n"
            f"Correction feedback: {feedback}\n"
            f"{evidence_instruction}"
            "After the first tool response, immediately write the final evidence handoff.\n"
            "Return a concise evidence handoff, not a large JSON blob.\n"
            "List the 2-3 strongest current changes, each with one commit URL and up to 2 file URLs.\n"
            "Do not repeat low-signal metadata or retry the same repo input."
        ),
        expected_output="A concise bullet evidence handoff of the strongest current changes with specific source URLs.",
        agent=monitor_agent(),
    )


def signal_gathering_task(context: dict, monitor: Task) -> Task:
    """Task: gather ecosystem signals from HN and PyPI."""
    repo = context.get("repo", "unknown")
    pkg = repo.split("/")[-1] if "/" in repo else repo
    changes = context.get("changes", [])
    scraped = context.get("scraped_content", "No pre-scraped content available.")
    signal_seed = context.get("signal_seed", "Current signal evidence unavailable.")
    feedback = context.get("correction_feedback", "None")
    has_prefetched_signal = signal_seed != "Current signal evidence unavailable."
    signal_instruction = (
        f"Use this prefetched signal evidence pack as the source of truth:\n{signal_seed}\n"
        "Do not call HackerNewsSignalTool or PyPIStatsTool again unless the prefetched signal evidence is unavailable.\n"
        if has_prefetched_signal else
        f"Use HackerNewsSignalTool to search for '{pkg}'.\n"
        f"Use PyPIStatsTool to fetch download stats for '{pkg}'.\n"
    )
    return Task(
        description=(
            f"Gather ecosystem intelligence for '{pkg}' (from repo {repo}).\n"
            f"Detected changes to keep the signals relevant: {changes}\n"
            f"Pre-scraped evidence for context: {scraped}\n"
            f"Correction feedback from prior attempts: {feedback}\n"
            f"{signal_instruction}"
            "Use at most 2 tool calls unless a prior attempt's correction feedback requires a targeted retry.\n"
            "Run each tool at most once and do not repeat the same tool input.\n"
            "Treat Hacker News items older than 30 days as noise, not evidence.\n"
            "Keep your signal summary tied to the same release window and evidence context.\n"
            "If the pre-scraped context conflicts with fresh tool results, prefer the fresh tool results.\n"
            "Return at most 4 short bullets."
        ),
        expected_output="At most 4 concise bullets describing adoption velocity and community sentiment.",
        agent=signal_analyst_agent(),
        context=[monitor],
    )


def research_task(context: dict, monitor: Task, signal: Task) -> Task:
    """Task: deep-scrape documentation and release notes."""
    repo = context.get("repo", "unknown")
    scraped = context.get("scraped_content", "No pre-scraped content available.")
    research_seed = context.get("research_seed", "Current research evidence unavailable.")
    feedback = context.get("correction_feedback", "None")
    has_prefetched_research = research_seed != "Current research evidence unavailable."
    research_instruction = (
        f"Use this prefetched research evidence pack as the source of truth:\n{research_seed}\n"
        "Do not call DeepScrapeTool again unless the prefetched research evidence is unavailable.\n"
        if has_prefetched_research else
        "Use DeepScrapeTool to scrape the repo's release page and PyPI page.\n"
    )
    return Task(
        description=(
            f"Deep dive on changes detected in {repo}.\n"
            f"Pre-scraped context: {scraped}\n"
            f"Correction feedback from prior attempts: {feedback}\n"
            f"{research_instruction}"
            "Use at most 2 DeepScrapeTool calls: one release/changelog source and one strongest current code or file source.\n"
            "Use the monitor evidence pack to prioritize specific current commit, release, CHANGELOG, and file URLs.\n"
            "Do not use generic README or homepage content as proof unless that exact file is part of the current monitor evidence.\n"
            "If the pre-scraped context conflicts with fresh tool evidence, trust the fresh evidence and note the mismatch.\n"
            "After the necessary scrapes, stop and summarize. Do not broaden the search into older repo history.\n"
            "Return at most 6 short bullets. Each bullet should follow: claim | evidence | URL."
        ),
        expected_output="At most 6 concise evidence bullets in the format claim | evidence | URL.",
        agent=researcher_agent(),
        context=[monitor, signal],
    )


def analysis_task(context: dict, research: Task) -> Task:
    """Task: synthesize research into a structured intelligence briefing."""
    repo = context.get("repo", "unknown")
    changes = context.get("changes", [])
    scraped = context.get("scraped_content", "No pre-scraped content available.")
    monitor_seed = context.get("monitor_seed", "Current monitor evidence unavailable.")
    memory_seed = context.get("memory_seed", "No validated historical data.")
    feedback = context.get("correction_feedback", "None")
    has_prefetched_memory = memory_seed != "No validated historical data."
    memory_instruction = (
        f"Use this prefetched historical memory as background only:\n{memory_seed}\n"
        "Do not call MemoryQueryTool again unless the prefetched memory is unavailable.\n"
        if has_prefetched_memory else
        f"Use MemoryQueryTool to query '{repo}' for historical context.\n"
    )
    return Task(
        description=(
            f"Write an intelligence briefing for {repo}.\n"
            f"Detected changes to ground your analysis: {changes}\n"
            f"Pre-scraped evidence to consider: {scraped}\n"
            f"Current monitor evidence pack: {monitor_seed}\n"
            f"Correction feedback from prior attempts: {feedback}\n"
            f"{memory_instruction}"
            "Use MemoryQueryTool at most once per attempt.\n"
            f"Your report MUST reference the specific changes detected, not generic analysis.\n"
            f"Only include architecture changes that are directly supported by the monitor/research evidence or by cited URLs.\n"
            f"If evidence is incomplete or uncertain, say so explicitly instead of inventing details.\n"
            f"If pre-scraped context conflicts with fresh tool outputs, prefer the fresh tool outputs and mention the conflict.\n"
            "Treat memory results and ecosystem signals as historical/adoption background only, not proof of current architecture changes.\n"
            "Do not promote adoption velocity, community sentiment, or generic product momentum into architecture changes.\n"
            "Each architecture change must trace back to at least one URL from the current monitor evidence pack or to a direct DeepScrape result derived from that pack.\n"
            "Do not list overlapping paraphrases of the same change; each architecture change must be materially distinct.\n"
            "Use specific URLs for cited_sources. Generic repo or API homepages are not sufficient when a more precise source exists.\n"
            "Cited sources should stay within the current monitor evidence pack or the prefetched research evidence derived from it.\n"
            "Output EXACTLY 2 or 3 architecture changes when the evidence supports that many; if only one claim is defensible, output one and lower confidence.\n"
            "Draft each change as: what changed | why it matters | strongest supporting URL.\n"
            "Keep the executive summary clean and reviewer-ready. Do not copy critique labels, tool logs, or JSON fragments into prose."
        ),
        expected_output=(
            "A concise intelligence briefing draft with a clean executive summary, exactly 2-3 strong architecture "
            "changes, and precise evidence URLs for each claim."
        ),
        agent=analyst_agent(),
        context=[research],
    )


def verification_task(context: dict, analysis: Task, red_team: Task) -> Task:
    """Task: validate the final report against quality schemas."""
    repo = context.get("repo", "unknown")
    changes = context.get("changes", [])
    scraped = context.get("scraped_content", "No pre-scraped content available.")
    monitor_seed = context.get("monitor_seed", "Current monitor evidence unavailable.")
    feedback = context.get("correction_feedback", "None")
    return Task(
        description=(
            f"Verify the analysis report for {repo} meets quality standards:\n"
            f"Detected changes: {changes}\n"
            f"Pre-scraped evidence: {scraped}\n"
            f"Current monitor evidence pack: {monitor_seed}\n"
            f"Correction feedback from prior attempts: {feedback}\n"
            "- confidence_score >= 0.7\n"
            "- cited_sources must not be empty\n"
            "- cited_sources should include specific commit, release, changelog, README, or file URLs when available\n"
            "- architecture_changes must list specific changes and should contain only the strongest 2-3 items\n"
            "- every architecture change must be grounded in the detected changes, research context, or cited sources\n"
            "- at least one cited source must come from the current monitor evidence pack or from a direct DeepScrape result of it\n"
            "- architecture_changes must be materially distinct; reject duplicate or overlapping paraphrases\n"
            "- reject generic or unsupported claims not traceable to evidence\n"
            "- if pre-scraped context conflicts with live tool evidence, prefer the live tool evidence\n"
            "- historical memory and HN/PyPI signals cannot be the sole proof for an architecture change\n"
            "- do not require retry only because adoption metrics, sentiment, or broader ecosystem context are sparse when the core code/changelog claims are already grounded\n"
            "- set requires_retry=true only when missing information materially weakens one of the listed architecture_changes\n"
            "- if the core claims are well-supported but some secondary details remain open, keep requires_retry=false and describe the caveat in missing_information\n"
            "- the final summary must be 1-2 polished sentences and must not include critique headings, tool chatter, or prompt artifacts\n"
            "- include only the strongest 2-4 precise URLs in cited_sources; prefer commit, release, changelog, README, PR, or file URLs\n"
            "- cited_sources should remain within the current monitor evidence pack or the prefetched research evidence derived from it\n"
            "- missing_information must be an empty string when requires_retry=false\n"
            "- set requires_retry=true if quality is insufficient"
        ),
        expected_output=(
            "Final IntelligenceReport JSON with a polished 1-2 sentence summary, 2-3 grounded architecture "
            "changes, 2-4 precise cited sources, and no critique leakage."
        ),
        agent=verifier_agent(),
        context=[analysis, red_team],
        output_pydantic=IntelligenceReport,
    )


def red_team_task(context: dict, analysis: Task) -> Task:
    """Task: adversarial review of the intelligence report.

    The Red Team reviewer challenges every claim and forces evidence grounding.
    Its structured critique is passed into the verifier's context.
    """
    repo = context.get("repo", "unknown")
    changes = context.get("changes", [])
    scraped = context.get("scraped_content", "No pre-scraped content available.")
    monitor_seed = context.get("monitor_seed", "Current monitor evidence unavailable.")
    feedback = context.get("correction_feedback", "None")
    return Task(
        description=(
            f"You are the Red Team adversarial reviewer for the {repo} intelligence report.\n\n"
            f"GROUND TRUTH EVIDENCE:\n"
            f"- Detected changes/SHAs: {changes}\n"
            f"- Pre-scraped content: {scraped}\n\n"
            f"- Current monitor evidence pack: {monitor_seed}\n\n"
            f"Correction feedback from prior attempts: {feedback}\n\n"
            "YOUR MISSION: Challenge every claim in the analysis report.\n\n"
            "If pre-scraped content conflicts with fresh tool evidence, treat the fresh tool evidence as authoritative.\n\n"
            "Historical memory and ecosystem signals are background only; they cannot be the sole basis for a current architecture claim.\n\n"
            "Challenge weak citations. Generic homepages should not be accepted when a precise commit, release, changelog, README, or file URL should exist.\n\n"
            "Reject any claim that cannot be tied back to the current monitor evidence pack or to a direct DeepScrape result derived from it.\n\n"
            "Reject overlapping paraphrases that try to count one change multiple times.\n\n"
            "Approve the report when the core architecture claims are grounded, even if a few secondary details remain uncertain.\n\n"
            "For EACH architecture change claimed, answer:\n"
            "1. Is this claim supported by the monitor's commit data? YES/NO\n"
            "2. Is this claim supported by scraped documentation? YES/NO\n"
            "3. Is this claim specific (not generic filler)? YES/NO\n"
            "4. Could this claim be hallucinated? YES/NO\n\n"
            "OUTPUT FORMAT:\n"
            "- ACCEPTED_CLAIMS: list of claims that pass all 4 checks\n"
            "- CHALLENGED_CLAIMS: list of claims that fail any check, with explanation\n"
            "- MISSING_EVIDENCE: what additional evidence would strengthen the report\n"
            "- VERDICT: APPROVE / NEEDS_REVISION\n\n"
            "Be ruthless. The goal is to eliminate hallucinated or unsupported architecture claims."
        ),
        expected_output=(
            "Structured adversarial critique with ACCEPTED_CLAIMS, CHALLENGED_CLAIMS, "
            "MISSING_EVIDENCE, and a verdict of APPROVE or NEEDS_REVISION."
        ),
        agent=red_team_agent(),
        context=[analysis],
    )
