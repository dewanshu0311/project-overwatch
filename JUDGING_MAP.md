# Judging Map - Project Overwatch (Monolith Dynamics)

## Criterion 1: Perception (Multi-Signal)
- Files: `main_workflow/state_manager.py`, `main_workflow/tools.py`, `main_workflow/main.py`
- Evidence:
  - GitHub SHA-diffing via `check_for_changes()` with a timestamp fallback path
  - Degraded mode detection when no GitHub token is available
  - `GitHubMonitorTool` produces structured evidence packs with commit SHA, commit URL, message, and ranked changed files
  - `DeepScrapeTool` uses GitHub API access natively for commits, blobs, and releases, with Firecrawl fallback for non-GitHub sources
  - `main.py` prefetches monitor, research, signal, and memory evidence before crew kickoff
  - `HackerNewsSignalTool` adds recent community discussion context
  - `PyPIStatsTool` adds adoption velocity context

## Criterion 2: Reasoning / Multi-Step Decision Making
- Files: `main_workflow/agents.py`, `main_workflow/tasks.py`, `main_workflow/memory.py`
- Evidence:
  - Six-agent sequential crew: Monitor -> Signal Analyst -> Researcher -> Analyst -> Red Team Reviewer -> Verifier
  - Tiered model profiles: stronger model for synthesis agents, lighter model for support agents
  - Analyst stage can use validated ChromaDB memory as historical background
  - Red Team Reviewer adversarially challenges every claim against the evidence chain
  - Correction feedback is propagated to all agents on retry

## Criterion 3: Tool Use
- File: `main_workflow/tools.py`
- Evidence:
  - 6 tools: `GitHubMonitorTool`, `DeepScrapeTool`, `SlackAlertTool`, `HackerNewsSignalTool`, `PyPIStatsTool`, `MemoryQueryTool`
  - Smart GitHub-native scraping bypasses Firecrawl for GitHub URLs
  - Per-agent limits reduce tool-loop churn
  - Prefetched evidence lets several stages skip redundant tool calls entirely
  - Repo-to-package fallback in `PyPIStatsTool` maps repos like `openai-python` to the package `openai`

## Criterion 4: Self-Correction
- File: `main_workflow/self_correction_loop.py`
- Evidence:
  - Explicit while loop with Pydantic validation and correction feedback injection
  - Multi-dimensional validation: confidence, source quality scoring, evidence-pack alignment, critique leakage detection, and distinct-claim checks
  - Retry delay between attempts
  - Per-key cooldown and rotation managed by `key_manager.py`
  - Correction feedback reaches all pipeline stages on retry

## Criterion 5: Action / Real-World Output
- Files: `main_workflow/tools.py`, `main_workflow/report_export.py`
- Evidence:
  - HTTP POST to Slack webhook
  - Fallback write to `output/alert_fallback.md` if webhook delivery fails
  - HTML report export to `output/latest_report.html`
  - JSON report export to `output/latest_report.json`
  - Auto-open browser support via `--open-report`

## Criterion 6: Impact
- Files: `main_workflow/main.py`, `main_workflow/demo_ui.py`
- Evidence:
  - Rich terminal dashboard with branding, pipeline diagram, evidence preview, attempt tracking, self-correction trace, and final report panels
  - CLI reports total runtime on completion
  - One-command demo mode via `--demo`
  - Automates a workflow that would otherwise take substantial manual repo analysis time

## Criterion 7: Long-Term Memory (Bonus)
- File: `main_workflow/memory.py`
- Evidence:
  - ChromaDB `PersistentClient` stores validated reports with metadata
  - Only quality-approved reports are stored
  - Query results are filtered for quality and sorted by recency
  - Historical data is labeled as background context rather than proof of current changes

## Criterion 8: Adversarial Review (Bonus)
- Files: `main_workflow/agents.py`, `main_workflow/tasks.py`
- Evidence:
  - Red Team Reviewer challenges each architecture claim against evidence quality rules
  - Checks whether claims are supported, specific, and possibly hallucinated
  - Rejects overlapping paraphrases and generic citations
  - Structured critique output: `ACCEPTED_CLAIMS`, `CHALLENGED_CLAIMS`, `MISSING_EVIDENCE`, `VERDICT`

## Demo Commands
```powershell
python -m main_workflow.main --demo
python -m main_workflow.main --fast-demo
python -m main_workflow.main --mock
python -m main_workflow.main
python -m main_workflow.main --dashboard
python -m main_workflow.main --open-report
```
