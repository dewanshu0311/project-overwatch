# Project Overwatch Command Guide

Project Overwatch supports both fixture-seeded presentation runs and real live analysis against user-supplied GitHub repositories.

Use the project virtual environment Python on Windows:

```powershell
c:\Agentathon\venv\Scripts\python.exe
```

## 1. Fast Demo Commands

### One-click judge demo

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo
```

What it does:
- uses the fixture-seeded fast path
- enables the dashboard
- opens the generated HTML report automatically
- best for short presentations where you want a fast, stable run

### Fast demo without auto-open

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --fast-demo --dashboard
```

What it does:
- uses fixture data and the fast model profile
- shows the dashboard
- keeps the browser closed
- best for quick internal checks

## 2. Live Custom Repo Commands

### Recommended live judging command

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --repo https://github.com/openclaw/openclaw --live-demo
```

What it does:
- accepts a full GitHub URL or `owner/name`
- enables the dashboard
- opens the HTML report automatically
- forces analysis even if no new commit was detected that day
- best for proving the system works on a real repo chosen at presentation time

### Live custom repo without browser pop-up

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --repo openclaw/openclaw --dashboard --force-analysis
```

What it does:
- analyzes the exact repo you provide
- shows the dashboard
- does not auto-open the report
- still proceeds even when no SHA change is detected

### Live custom repo with normal change detection

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --repo openclaw/openclaw --dashboard
```

What it does:
- analyzes the repo only if a new SHA difference is detected
- best when you want strict live detection behavior

## 3. Full Quality Commands

### Mock quality check

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --mock --dashboard
```

What it does:
- uses fixture data with the balanced profile
- keeps the stronger synthesis path for higher-quality reasoning
- useful when you want to inspect logic without depending on live repo volatility

### Live mode using configured target repos

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard
```

What it does:
- checks the repos listed in `main_workflow/config.py`
- runs live monitoring and live research
- useful for the normal multi-repo workflow

## 4. Utility Commands

### Headless live run

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main
```

### Open the latest HTML report

```powershell
start c:\Agentathon\output\latest_report.html
```

### Open the latest JSON report

```powershell
notepad c:\Agentathon\output\latest_report.json
```

## 5. Key Flags

| Flag | Purpose |
| :--- | :--- |
| `--dashboard` | Show the Rich terminal dashboard. |
| `--mock` | Use fixture data with live LLM/tool reasoning. |
| `--fast-demo` | Use the fast model profile and fixture-seeded context. |
| `--demo` | Shortcut for `--fast-demo --dashboard --open-report`. |
| `--repo` | Target a specific GitHub repo via `owner/name` or full GitHub URL. |
| `--force-analysis` | Analyze the repo even when no new SHA difference is detected. |
| `--live-demo` | Shortcut for `--dashboard --open-report --force-analysis`. |
| `--open-report` | Open the HTML report automatically after success. |

## 6. Best Practice For Judges

Use one of these two commands:

Fixture-seeded stability:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo
```

Real live credibility:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --repo owner/name --live-demo
```
