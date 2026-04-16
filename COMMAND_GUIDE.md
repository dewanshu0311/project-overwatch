# Project Overwatch Command Guide

This file is the practical version of the README. Use it when you want to run the project quickly without thinking about every flag.

On Windows, always use the project virtual environment Python:

```powershell
c:\Agentathon\venv\Scripts\python.exe
```

## 1. Fast Demo Commands

These are the safest commands for short presentations.

### One-click demo

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo
```

Use this when:
- you want the fastest clean demo
- you want the dashboard
- you want the HTML report to open automatically

What it uses:
- fixture-seeded context
- fast model profile

### Fast demo without opening the browser

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --fast-demo --dashboard
```

Use this when:
- you want to test the dashboard
- you want a quick internal check

## 2. Live Repo Commands

These commands are for proving the system works on a real repository.

Important:
- the repo goes at the end of the command so you can replace it quickly
- you can use either `owner/name`
- or a full GitHub URL like `https://github.com/openclaw/openclaw`

### Full power live repo command

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --open-report --force-analysis --repo https://github.com/openclaw/openclaw
```

Use this when:
- you want the balanced high-quality model path
- you want a real custom GitHub repo
- you want the dashboard during the run
- you want the HTML report to open automatically at the end

What this gives you:
- real live repo input
- balanced profile for stronger synthesis
- visual dashboard
- browser report at the end
- no risk of the run stopping just because there were no new commits today

This is the strongest all-in-one command to show at the end when you want quality plus credibility.

### Live repo check with normal change detection

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --repo https://github.com/openclaw/openclaw
```

Use this when:
- you want honest live behavior
- you only want the pipeline to run if a new SHA difference is detected

What happens if nothing changed:
- the app does not fake a result
- it stops and tells you no changes were detected

This is the better command when you want to show strict live monitoring behavior.

### Live repo check with forced analysis

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --force-analysis --repo https://github.com/openclaw/openclaw
```

Use this when:
- you want to inspect a real repo even if there were no new commits today
- you want the dashboard but do not want the browser to open automatically

What happens here:
- the app still checks the repo normally first
- if there is no new SHA difference, it shows that forced analysis is being used
- then it analyzes the current snapshot anyway

This is useful for live judging when you need the system to continue instead of stopping.

### Recommended live judging command

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --live-demo --repo https://github.com/openclaw/openclaw
```

What this does:
- turns on the dashboard
- opens the HTML report automatically
- forces analysis if there was no new SHA difference

Best use:
- live judging
- someone gives you a repo on the spot
- you want the strongest mix of credibility and presentation
- you want the shorter shortcut version of the full-power live command

## 3. Quality Check Commands

### Mock quality run

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --mock --dashboard
```

Use this when:
- you want the balanced profile
- you want to inspect reasoning quality
- you do not want repo volatility to affect the run

### Live configured-target run

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard
```

Use this when:
- you want the project to check the repos already listed in `main_workflow/config.py`
- you are running the normal multi-repo workflow

## 4. Headless Commands

### Standard headless run

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main
```

Use this when:
- you do not need the dashboard
- you just want the normal terminal output

### Headless custom repo run with forced analysis

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --force-analysis --repo openclaw/openclaw
```

Use this when:
- you want a one-off repo check
- you do not care about the dashboard

## 5. Open Reports Manually

### HTML report

```powershell
start c:\Agentathon\output\latest_report.html
```

### JSON report

```powershell
notepad c:\Agentathon\output\latest_report.json
```

## 6. Quick Flag Meaning

| Flag | Meaning |
| :--- | :--- |
| `--dashboard` | Show the Rich dashboard. |
| `--open-report` | Open the HTML report automatically after success. |
| `--repo` | Target a specific GitHub repo. Accepts `owner/name` or full GitHub URL. |
| `--force-analysis` | Continue even if no new SHA difference was detected. |
| `--live-demo` | Shortcut for live presentation mode: dashboard + open report + force analysis. |
| `--demo` | Shortcut for fast fixture demo: fast-demo + dashboard + open report. |
| `--mock` | Use fixture data with live LLM/tool reasoning. |
| `--fast-demo` | Use fixture-seeded context and the fast model profile. |

## 7. Best Commands To Remember

Fast safe demo:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --demo
```

Strict live repo demo:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --repo https://github.com/openclaw/openclaw
```

Live repo demo that will not stop on "no changes detected":

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --live-demo --repo https://github.com/openclaw/openclaw
```

Full power live repo demo:

```powershell
c:\Agentathon\venv\Scripts\python.exe -m main_workflow.main --dashboard --open-report --force-analysis --repo https://github.com/openclaw/openclaw
```
