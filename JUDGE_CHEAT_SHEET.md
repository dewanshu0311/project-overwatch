# Judge Cheat Sheet

## 5 Commands

1. Fast safe demo

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo
```

2. Real live repo demo

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --live-demo --repo https://github.com/openclaw/openclaw
```

3. Full power live repo demo

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --open-report --force-analysis --repo https://github.com/openclaw/openclaw
```

4. Strict live repo check

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --repo https://github.com/openclaw/openclaw
```

5. Open HTML report

```powershell
start c:\Agentathon\output\latest_report.html
```

## 5 Talking Points

1. Project Overwatch is an autonomous AI analyst team for GitHub repositories, not a single chatbot prompt.

2. It follows a 6-stage workflow: Monitor, Signal Analyst, Researcher, Analyst, Red Team Reviewer, and Verifier.

3. It uses real tools and current evidence from GitHub, release pages, Hacker News, and PyPI instead of relying only on model memory.

4. It does not blindly trust LLM output: it validates, retries, challenges weak claims, and only stores validated reports in memory.

5. The final result is a real deliverable artifact: dashboard view, verified report, HTML export, JSON export, and Slack or fallback delivery.
