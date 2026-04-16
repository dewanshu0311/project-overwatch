# Project Overwatch

Project Overwatch is an autonomous competitive-intelligence agent built for Agentathon 2026. It monitors GitHub repository changes, gathers ecosystem signals, researches supporting evidence, red-teams its own findings, verifies the final report, and exports the result as both HTML and JSON.

Instead of asking a single LLM to "summarize a repo," Overwatch behaves like a small analyst team. It first detects what changed, then gathers supporting context, researches the strongest evidence, writes an intelligence brief, attacks its own claims, validates the final report, and finally delivers a polished artifact a human team can actually use.

The result is a more judge-friendly and real-world-ready agent workflow centered on perception, reasoning, tool use, self-correction, and action.

Primary use case: Project Overwatch helps developers, startups, platform teams, and security-minded engineering teams track critical changes in fast-moving AI and developer-tool ecosystems automatically.

## Why This Matters

Modern engineering teams cannot manually keep up with every meaningful change across fast-moving repos, releases, SDKs, and ecosystem chatter. Project Overwatch turns that noisy stream into a structured, evidence-grounded intelligence brief.

In practice, it is designed to help teams answer questions like:

- What changed in an important dependency or competitor repo?
- Which changes are actually architecturally meaningful?
- Is the ecosystem reacting to those changes?
- Can we trust the report enough to act on it?

## What It Does

- Monitors target repositories for meaningful code and release changes
- Collects ecosystem context from GitHub, Hacker News, and PyPI
- Synthesizes a structured intelligence report through a 6-agent pipeline
- Challenges weak claims with a dedicated red-team review stage
- Verifies report quality before export or delivery
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
- Slack delivery with local fallback when webhook delivery fails

## System Flow

```text
GitHub / Releases / Files / HN / PyPI
                |
                v
      Prefetch and evidence compression
                |
                v
Monitor -> Signal -> Researcher -> Analyst -> Red Team -> Verifier
                |
                v
        Validated IntelligenceReport
                |
                v
      HTML / JSON / Slack / Memory
```

## Why Multi-Agent Instead Of One Prompt

This project deliberately avoids a single-shot "summarize the repo" approach.

Each stage has a different job:

- `Monitor`: detect current repo changes
- `Signal Analyst`: add ecosystem context
- `Researcher`: gather direct supporting evidence
- `Analyst`: synthesize the intelligence brief
- `Red Team Reviewer`: challenge weak or hallucinated claims
- `Verifier`: decide whether the result is good enough to ship

That separation is what makes the system feel like an analyst workflow rather than a chatbot.

## Real-World Use Cases

- Competitor monitoring for AI/devtool startups
- Dependency intelligence for platform or developer-experience teams
- Release tracking for SDKs and API ecosystems
- Product and engineering research for fast-moving open-source tooling
- Early-warning monitoring for important architectural shifts in external repos

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
COMMAND_GUIDE.md
CONTEXT.md
JUDGING_MAP.md
PRESENTATION_GUIDE.md
```

## Setup

1. Create and activate a Python 3.10 virtual environment.
2. Install dependencies:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m pip install -r requirements.txt
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
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --fast-demo --dashboard
```

Full judge-facing demo:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo
```

Live judge-facing demo on a custom repo:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --live-demo --repo https://github.com/openclaw/openclaw
```

Live analysis on a custom repo with normal change detection:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --repo openclaw/openclaw
```

Live analysis on a custom repo without stopping on "no changes detected":

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --force-analysis --repo openclaw/openclaw
```

Mock mode:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --mock --dashboard
```

Live mode:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard
```

## Outputs

Successful runs generate:

- `output/latest_report.html`
- `output/latest_report.json`
- `output/alert_fallback.md` when Slack delivery fails

These outputs are runtime artifacts and are not tracked in Git.

## Example Output Snapshot

Representative result from a recent run against `openai/openai-python`:

- Summary: The system detected support for short-lived tokens in the client layer, a `_version.py` update, and accompanying release-note changes.
- Confidence: `0.90`
- Requires retry: `false`
- Strong evidence:
  - commit URL for the short-lived token change
  - commit URL for the `_version.py` update
  - changelog URL tied to the same release window

A checked-in example summary is available in [EXAMPLE_REPORT.md](/C:/Agentathon/EXAMPLE_REPORT.md).

## What Makes It Reliable

The project is designed to reduce blind trust in LLM output:

- prefetched evidence reduces noisy tool loops
- current URLs are preferred over generic summaries
- red-team review challenges unsupported claims
- the verifier checks confidence, source quality, and claim distinctness
- self-correction retries weak outputs with targeted feedback
- only validated reports are stored in memory
- API key rotation handles rate limits more gracefully

## Why It's Agentic

Project Overwatch goes beyond a single prompt by separating:

- perception of repository changes
- ecosystem signal gathering
- evidence research
- synthesis
- adversarial review
- verification

This gives the system a more reliable reasoning chain and a visible self-correction story for demos and judging.

## Demo Notes

For a short live demo:

1. Run `c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo`
2. Show the dashboard header and evidence preview
3. Point out the 6-agent pipeline
4. Highlight the self-correction trace
5. Open the generated HTML report
6. For a live credibility demo, switch to `--repo owner/name --live-demo` and show a real repo that is not hardcoded in the fixture file

## How To Demo In 2 Minutes

If you only get a very short judging window, use this sequence:

1. Start with `c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo`
2. While the dashboard is running, say: "This system watches a software repo, gathers proof, researches changes, red-teams itself, and only then ships a final report."
3. Point to the evidence preview and explain that the pipeline is grounded in current repo evidence, not just generic model memory.
4. Point to the 6-agent pipeline and say each agent has a different job: detect, contextualize, research, analyze, challenge, verify.
5. When the run completes, show the self-correction trace and final confidence score.
6. Open `output/latest_report.html` and frame it as the deliverable artifact for a real team.

Best one-line summary for a demo:

"Project Overwatch is an autonomous AI analyst team that turns raw repository changes into a verified competitive-intelligence report."

## Known Limitations

- The system is still probabilistic because it relies on live LLM calls, so exact phrasing and confidence can vary between runs.
- External APIs can affect runtime and quality, especially under rate limits or when source systems are noisy.
- Ecosystem signals such as Hacker News and PyPI are treated as supporting context, not proof of architectural change.
- Mock and fast-demo modes use fixture-seeded context, but they still rely on live model/tool execution unless those services are unavailable.
- The strongest reports come from repos with clear current commit, release, or changelog evidence; weaker public evidence can lead to more conservative outputs.

## How It Differs From ChatGPT

ChatGPT can explain a repository if you paste enough context into a prompt.

Project Overwatch is different because it is built as a repeatable agent system:

- it gathers current evidence itself
- it uses tools instead of only relying on static prompt context
- it separates research, synthesis, critique, and verification into different stages
- it retries when quality is weak
- it produces a structured deliverable artifact instead of only a chat response

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
