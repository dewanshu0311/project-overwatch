# Demo Runbook

## Suggested Flow

1. Introduce yourself and the problem.
2. Show the first two slides.
3. Run the opening demo command.
4. Return to the slides and explain the pipeline.
5. Run the full live repo command.
6. End with impact and reliability.

## Main Commands

Opening demo:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo
```

Terminal-only demo:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --fast-demo --dashboard
```

Full live repo run:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --open-report --force-analysis --repo https://github.com/openclaw/openclaw
```

## Talking Points

1. Project Overwatch is an autonomous AI analyst team for GitHub repositories.
2. It follows a 6-stage workflow: Monitor, Signal Analyst, Researcher, Analyst, Red Team Reviewer, and Verifier.
3. It uses live evidence from GitHub, release pages, Hacker News, and PyPI instead of relying only on model memory.
4. It improves trust through validation, retries, red-team review, and verified memory storage.
5. It produces a real deliverable: dashboard view, verified report, HTML export, JSON export, and Slack or fallback delivery.
