# Project Overwatch

Project Overwatch is an autonomous competitive-intelligence agent built for Agentathon 2026. It monitors live GitHub repository changes, gathers ecosystem signals, researches supporting evidence, red-teams its own findings, verifies the final report, and exports the result as both HTML and JSON.

## What It Does

- Monitors target repositories for meaningful code and release changes
- Collects ecosystem context from GitHub, Hacker News, and PyPI
- Synthesizes a structured intelligence report through a 6-agent pipeline
- Challenges weak claims with a red-team review stage
- Verifies report quality before export
- Exports polished HTML and machine-readable JSON outputs
- Delivers a summary to Slack or falls back to a local markdown alert

## Core Architecture

Sequential 6-agent CrewAI pipeline:

1. Monitor
2. Signal Analyst
3. Researcher
4. Analyst
5. Red Team Reviewer
6. Verifier

Key runtime features:

- Explicit self-correction loop with retry feedback
- Groq and Firecrawl API key rotation with per-key cooldown tracking
- ChromaDB memory for validated historical reports
- Rich terminal dashboard for demo mode
- HTML report export after successful runs

## Tech Stack

- Python 3.10
- CrewAI 0.152.0
- ChromaDB 1.5.7
- Firecrawl 1.15.0
- Pydantic 2.10.6
- Rich 13.7.1
- LangChain-Groq 0.3.2

LLM profiles:

- `balanced`: stronger synthesis for core agents, lighter models for support agents
- `fast`: lighter model path for all agents to improve demo reliability

## Project Layout

```text
main_workflow/
  agents.py
  config.py
  demo_ui.py
  key_manager.py
  main.py
  memory.py
  report_export.py
  schemas.py
  self_correction_loop.py
  state_manager.py
  tasks.py
  tools.py
fixtures/
  mock_repo_alert.json
requirements.txt
.env.example
README.md
```

## Setup

1. Create and activate a Python 3.10 virtual environment.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Create a local `.env` from `.env.example` and fill in your keys:

- `GROQ_API_KEYS`
- `FIRECRAWL_API_KEYS`
- `GITHUB_TOKEN`
- `WEBHOOK_URL`

The real `.env` file is intentionally excluded from Git.

## Running The Project

Fast demo with dashboard:

```powershell
python -m main_workflow.main --fast-demo --dashboard
```

Full judge-facing demo:

```powershell
python -m main_workflow.main --demo
```

Mock mode:

```powershell
python -m main_workflow.main --mock --dashboard
```

Live mode:

```powershell
python -m main_workflow.main --dashboard
```

## Outputs

Successful runs generate:

- `output/latest_report.html`
- `output/latest_report.json`
- `output/alert_fallback.md` when Slack delivery fails

These outputs are runtime artifacts and are not tracked in Git.

## Why It’s Agentic

Project Overwatch goes beyond a single prompt by separating:

- perception of changes
- ecosystem signal gathering
- evidence research
- synthesis
- adversarial review
- verification

This gives the system a more reliable reasoning chain and a visible self-correction story for demos and judging.

## Demo Notes

For a short live demo:

1. Run `python -m main_workflow.main --demo`
2. Show the dashboard header and evidence preview
3. Point out the 6-agent pipeline
4. Highlight the self-correction trace
5. Open the generated HTML report

## Security Notes

- Never commit `.env`
- API keys are loaded from environment variables only
- Slack failures fall back to a local file instead of breaking the run

## Submission Summary

Project Overwatch is designed to demonstrate:

- Perception through live repo monitoring and supporting signals
- Reasoning through a role-based multi-agent workflow
- Action through report generation and delivery
- Self-correction through retries, validation, and red-team critique

