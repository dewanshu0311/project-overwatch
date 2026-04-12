# Judging Map — Project Overwatch (Monolith Dynamics)

## Criterion 1: Perception (Multi-Signal)
- Files: main_workflow/state_manager.py + main_workflow/tools.py + main_workflow/main.py
- Evidence:
  - GitHub SHA-diffing via check_for_changes() with 24h timestamp fallback
  - Degraded mode detection when no GitHub token (returns `degraded: True`)
  - GitHubMonitorTool produces structured evidence packs: commit SHA, URL, message, ranked changed files
  - DeepScrapeTool uses GitHub API natively for commits/blobs/releases (Firecrawl fallback for non-GitHub)
  - Evidence prefetching in main.py — monitor and research data are scraped BEFORE crew kickoff
  - HackerNewsSignalTool — free HN Algolia API for community sentiment
  - PyPIStatsTool — free pypistats.org API for adoption velocity

## Criterion 2: Reasoning / Multi-Step Decision Making
- Files: main_workflow/agents.py + tasks.py + memory.py
- Evidence:
  - Six-agent sequential crew: Monitor -> Signal Analyst -> Researcher -> Analyst -> Red Team Reviewer -> Verifier
  - Tiered model profiles: 70B for synthesis agents, 8B for support agents (resource-efficient reasoning)
  - Analyst queries ChromaDB cognitive memory for historical trends (filtered: only validated entries)
  - Red Team Reviewer adversarially challenges every claim against ground truth evidence
  - Correction feedback propagated to ALL agents on retry (not just monitor)
  - LLM: groq/llama-3.3-70b-versatile (core) + groq/llama-3.1-8b-instant (support)

## Criterion 3: Tool Use
- File: main_workflow/tools.py
- Evidence:
  - 6 tools: GitHubMonitorTool, DeepScrapeTool, SlackAlertTool, HackerNewsSignalTool, PyPIStatsTool, MemoryQueryTool
  - Smart GitHub-native scraping bypasses Firecrawl for GitHub URLs (structured API data vs raw HTML)
  - Per-agent tool limits (max_iter, max_execution_time) prevent tool-loop churn
  - Prefetched agents skip redundant tool calls entirely
  - Repo-to-package fallback in PyPIStatsTool maps repos like `openai-python` to the correct package `openai`

## Criterion 4: Self-Correction
- File: main_workflow/self_correction_loop.py
- Evidence:
  - Explicit while loop with Pydantic validation gate and correction_feedback injection
  - Multi-dimensional validation: confidence, source quality scoring, evidence-pack alignment, critique leakage detection, distinct-claim checks
  - Smart retry acceptance: reports with confidence >= 0.8 AND multiple grounded claims can pass even if caveats remain
  - 10s retry delay between attempts
  - Per-key cooldown/rotation managed by key_manager.py for rate-limit resilience
  - Correction feedback reaches ALL pipeline stages on retry

## Criterion 5: Action / Real-World Output
- Files: main_workflow/tools.py + main_workflow/report_export.py
- Evidence:
  - HTTP POST to Slack webhook
  - Fallback write to `output/alert_fallback.md` if webhook fails
  - HTML report export to `output/latest_report.html` (XSS-safe, dark-mode design)
  - JSON report export to `output/latest_report.json`
  - Auto-open browser via `--open-report` flag

## Criterion 6: Impact
- Files: main_workflow/main.py + main_workflow/demo_ui.py
- Evidence:
  - Rich terminal dashboard (--dashboard) with ASCII branding, pipeline diagram, evidence preview, attempt tracking, self-correction trace, and final report panels
  - CLI reports total runtime on completion
  - One-command demo mode (--demo) for judge-facing presentations
  - Automates a task that would take ~45 minutes manually

## Criterion 7: Long-Term Memory (Bonus)
- File: main_workflow/memory.py
- Evidence:
  - ChromaDB PersistentClient stores validated reports with temporal metadata
  - Only stores reports that pass quality gate (confidence >= 0.7, requires_retry=false)
  - Query results filtered for quality and sorted by recency
  - Historical data explicitly labeled as background context (not proof of current changes)
  - 10+ reports stored across runs, similarity-based retrieval working

## Criterion 8: Adversarial Review (Bonus)
- Files: main_workflow/agents.py + tasks.py
- Evidence:
  - Red Team Reviewer challenges each architecture claim against 4 criteria
  - Checks: commit data support? documentation? specific? hallucinated?
  - Rejects overlapping paraphrases and generic citations
  - Accepts when core claims are grounded even if secondary details are open
  - Structured output: ACCEPTED_CLAIMS / CHALLENGED_CLAIMS / MISSING_EVIDENCE / VERDICT

## Demo Commands
python -m main_workflow.main --demo          # Full demo: dashboard + HTML + browser open
python -m main_workflow.main --fast-demo     # Fixture-seeded fast demo
python -m main_workflow.main --mock          # Fixture data + live tools
python -m main_workflow.main                 # Fully live mode
python -m main_workflow.main --dashboard     # Any mode + visual dashboard
python -m main_workflow.main --open-report   # Any mode + auto-open HTML report
