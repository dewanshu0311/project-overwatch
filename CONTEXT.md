---
# CONTEXT.md — Agentathon Project Rules

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
- **balanced mode** (default): groq/llama-3.3-70b-versatile for core agents (analyst, verifier), groq/llama-3.1-8b-instant for support agents (monitor, signal, researcher, red team)
- **fast mode** (--fast-demo): groq/llama-3.1-8b-instant for ALL agents (better free-tier reliability)
- 9 Groq API keys with true round-robin rotation via key_manager.py
- 9 Firecrawl API keys with same rotation pattern

## Architecture Rules
- Self-correction is implemented ONLY via explicit Python while loop in self_correction_loop.py
- MAX_RETRIES = 2, defined ONLY in config.py, never hardcoded in any other file
- CONFIDENCE_THRESHOLD = 0.7, defined ONLY in config.py
- Verifier agent uses output_pydantic=IntelligenceReport imported from schemas.py
- ALL API calls must be wrapped in try/except with rich console logging as fallback
- --mock flag in main.py loads fixtures/mock_repo_alert.json (live LLM + tools still active)
- --fast-demo flag same as --mock but with fast model profile for better free-tier reliability
- --dashboard flag enables Rich terminal dashboard with visual panels
- --demo flag combines --fast-demo + --dashboard + --open-report
- --open-report flag auto-opens HTML report in browser after run
- Use rich.console.Console() for ALL terminal output, never use print()
- UTF-8 stdout/stderr override in main.py for Windows cp1252 compatibility

## Evidence Prefetching (main.py)
- Before CrewAI kickoff, main.py prefetches monitor, research, signal, and memory context
- Results are injected as `monitor_seed`, `research_seed`, `signal_seed`, and `memory_seed`
- Agents with prefetched data skip redundant tool calls
- This reduces token waste, retry churn, and rate-limit pressure

## Pipeline (6 Agents, 6 Tools)
Monitor -> Signal Analyst -> Researcher -> Analyst(+Memory) -> Red Team Reviewer -> Verifier

## Tools
1. GitHubMonitorTool — structured evidence pack with commit SHA/URL/files (ranked by signal)
2. HackerNewsSignalTool — community sentiment from HN Algolia API
3. PyPIStatsTool — download velocity from pypistats.org
4. DeepScrapeTool — GitHub-native API scraper first, Firecrawl fallback for non-GitHub URLs
5. MemoryQueryTool — ChromaDB semantic history search (filters out low-quality entries)
6. SlackAlertTool — webhook delivery to Slack (fallback to output/alert_fallback.md)

## Cognitive Memory (ChromaDB)
- Stored in: memory_db/ (auto-created)
- After each successful run, validated reports are stored (requires_retry=false, confidence >= 0.7)
- Query results are filtered: only validated entries, sorted by recency
- History is prefixed with: "Historical context only — do not treat as evidence of current changes"

## Key Rotation (key_manager.py)
- 9 Groq keys + 9 Firecrawl keys in .env (comma-separated)
- True round-robin rotation with per-key cooldown tracking
- On 429 rate limit: infers most-recently-used key from pointer, marks exhausted
- Thread-safe with threading.Lock

## Correction Feedback Propagation
- correction_feedback from self_correction_loop is injected into ALL tasks (not just monitor)
- Each retry attempt gives every agent specific feedback about what failed
- Verifier accepts strong reports (confidence >= 0.8 with sources) even if requires_retry=true

## Exact Pydantic Schema (DO NOT modify this schema in any file)
class IntelligenceReport(BaseModel):
    summary: str
    cited_sources: list[str]
    architecture_changes: list[str]
    confidence_score: float
    requires_retry: bool
    missing_information: str

## Files
- main_workflow/__init__.py
- main_workflow/config.py
- main_workflow/schemas.py
- main_workflow/state_manager.py
- main_workflow/key_manager.py
- main_workflow/tools.py
- main_workflow/agents.py
- main_workflow/tasks.py
- main_workflow/self_correction_loop.py
- main_workflow/memory.py
- main_workflow/main.py
- main_workflow/demo_ui.py
- main_workflow/report_export.py

## Fallback Output Location
Failed Slack delivery writes to: c:\Agentathon\output\alert_fallback.md
HTML report writes to: c:\Agentathon\output\latest_report.html
JSON report writes to: c:\Agentathon\output\latest_report.json
---
