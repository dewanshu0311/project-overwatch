---
# CONTEXT.md - Agentathon Project Rules

## Stack
- crewai==0.152.0
- chromadb==1.5.7
- firecrawl-py==1.15.0
- pydantic==2.10.6
- python-dotenv==1.0.1
- rich==13.7.1
- requests==2.32.3
- langchain-groq==0.3.2

## LLM Models (Tiered via OVERWATCH_MODEL_PROFILE)
- **balanced mode** (default): `groq/llama-3.3-70b-versatile` for core agents (analyst, verifier), `groq/llama-3.1-8b-instant` for support agents (monitor, signal, researcher, red team)
- **fast mode** (`--fast-demo`): `groq/llama-3.1-8b-instant` for all agents to improve free-tier reliability
- 9 Groq API keys with true round-robin rotation via `key_manager.py`
- 9 Firecrawl API keys with the same rotation pattern

## Architecture Rules
- Self-correction is implemented only via the explicit Python while loop in `self_correction_loop.py`
- `MAX_RETRIES = 2`, defined only in `config.py`
- `CONFIDENCE_THRESHOLD = 0.7`, defined only in `config.py`
- The verifier task uses `output_pydantic=IntelligenceReport` imported from `schemas.py`
- API calls should fail gracefully and fall back to Rich console logging where possible
- `--mock` loads `fixtures/mock_repo_alert.json` but still uses live LLM calls and live tools
- `--fast-demo` uses fixture-seeded context plus the fast model profile for better reliability
- `--dashboard` enables the Rich terminal dashboard
- `--demo` combines `--fast-demo + --dashboard + --open-report`
- `--open-report` opens the generated HTML report in the browser after a run
- Windows UTF-8 stdout/stderr override in `main.py` avoids cp1252 display issues

## Evidence Prefetching (main.py)
- Before CrewAI kickoff, `main.py` prefetches monitor, research, signal, and memory context
- Results are injected as `monitor_seed`, `research_seed`, `signal_seed`, and `memory_seed`
- Agents with prefetched data skip redundant tool calls
- This reduces token waste, retry churn, and rate-limit pressure

## Pipeline (6 Agents, 6 Tools)
Monitor -> Signal Analyst -> Researcher -> Analyst -> Red Team Reviewer -> Verifier

## Tools
1. GitHubMonitorTool - structured evidence pack with commit SHA, commit URL, and ranked changed-file URLs
2. HackerNewsSignalTool - community discussion from the HN Algolia API
3. PyPIStatsTool - download velocity from pypistats.org with repo-to-package fallback
4. DeepScrapeTool - GitHub-native API scraping first, Firecrawl fallback for non-GitHub URLs
5. MemoryQueryTool - ChromaDB semantic history search filtered to validated entries
6. SlackAlertTool - webhook delivery to Slack with fallback to `output/alert_fallback.md`

## Cognitive Memory (ChromaDB)
- Stored in `memory_db/` at runtime
- Only validated reports are stored: `requires_retry == false`, confidence >= 0.7, and non-empty sources and architecture changes
- Query results are filtered and treated as historical context only
- Historical memory is background context, not proof of current changes

## Key Rotation (key_manager.py)
- Supports comma-separated Groq and Firecrawl key pools from `.env`
- Uses true round-robin selection with per-key cooldown tracking
- On rate limits, infers the most recently used key from the pointer and marks it exhausted
- Rotation is thread-safe

## Correction Feedback Propagation
- `correction_feedback` from `self_correction_loop.py` is injected into all tasks
- Each retry gives every agent specific feedback about what failed
- Strong reports can still pass with caveats if the core grounded claims are solid enough

## Exact Pydantic Schema
```python
class IntelligenceReport(BaseModel):
    summary: str
    cited_sources: list[str]
    architecture_changes: list[str]
    confidence_score: float
    requires_retry: bool
    missing_information: str
```

## Files
- `main_workflow/__init__.py`
- `main_workflow/config.py`
- `main_workflow/schemas.py`
- `main_workflow/state_manager.py`
- `main_workflow/key_manager.py`
- `main_workflow/tools.py`
- `main_workflow/agents.py`
- `main_workflow/tasks.py`
- `main_workflow/self_correction_loop.py`
- `main_workflow/memory.py`
- `main_workflow/main.py`
- `main_workflow/demo_ui.py`
- `main_workflow/report_export.py`

## Fallback Output Locations
- Failed Slack delivery: `c:\Agentathon\output\alert_fallback.md`
- HTML report: `c:\Agentathon\output\latest_report.html`
- JSON report: `c:\Agentathon\output\latest_report.json`
---
