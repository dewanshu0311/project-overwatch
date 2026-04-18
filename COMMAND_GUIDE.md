# Project Overwatch Command Guide

This guide keeps only the commands you are most likely to use during a demo or live presentation.

Use this Python path on Windows:

```powershell
c:\Agentathon\venv\Scripts\python.exe
```

## 1. Starter Demo

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo
```

What it uses:
- Model: `Fast profile`
- Dashboard: `Yes`
- Auto-open report: `Yes`
- Custom GitHub repo: `No`
- Data source: `Fixture-seeded`

Use this when:
- you want a clean opening demo
- you want to show the dashboard quickly
- you want the report to open automatically at the end

## 2. Terminal-Only Demo

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --fast-demo --dashboard
```

What it uses:
- Model: `Fast profile`
- Dashboard: `Yes`
- Auto-open report: `No`
- Custom GitHub repo: `No`
- Data source: `Fixture-seeded`

Use this when:
- you want to show the run in the terminal without switching to the browser immediately
- you want a quick test before presenting

## 3. Live Repo Check

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --repo https://github.com/openclaw/openclaw
```

What it uses:
- Model: `Balanced profile`
- Dashboard: `Yes`
- Auto-open report: `No`
- Custom GitHub repo: `Yes`
- Data source: `Live repo`
- Force analysis: `No`

Use this when:
- you want to show honest live monitoring behavior
- you only want the run to continue if a new SHA difference is detected

If nothing changed:
- the app tells you no changes were detected
- it does not invent a result

## 4. Full Power Live Run

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --open-report --force-analysis --repo https://github.com/openclaw/openclaw
```

What it uses:
- Model: `Balanced profile`
- Dashboard: `Yes`
- Auto-open report: `Yes`
- Custom GitHub repo: `Yes`
- Data source: `Live repo`
- Force analysis: `Yes`

Use this when:
- you want the strongest live presentation command
- you want a real repo chosen on the spot
- you want high-quality reasoning
- you do not want the run to stop just because there were no new commits that day

This is the best command to use at the end of your presentation.

## 5. Open Reports Manually

HTML report:

```powershell
start c:\Agentathon\output\latest_report.html
```

JSON report:

```powershell
notepad c:\Agentathon\output\latest_report.json
```

## Quick Summary

| Command | Model | Dashboard | Custom Repo | Best Use |
| :--- | :--- | :--- | :--- | :--- |
| `--demo` | Fast | Yes | No | opening demo |
| `--fast-demo --dashboard` | Fast | Yes | No | terminal-only demo |
| `--dashboard --repo ...` | Balanced | Yes | Yes | strict live check |
| `--dashboard --open-report --force-analysis --repo ...` | Balanced | Yes | Yes | strongest final live run |
