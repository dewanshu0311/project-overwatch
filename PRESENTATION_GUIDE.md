# Project Overwatch Presentation Guide

## One-Sentence Explanation

Project Overwatch is an autonomous AI analyst team that watches GitHub repositories, gathers supporting signals, challenges its own claims, and produces a verified competitive-intelligence report.

## 1-Minute Pitch

Project Overwatch is a multi-agent competitive-intelligence system built for Agentathon 2026. Instead of asking one LLM to summarize a repo, it runs a six-stage workflow: it detects current changes, gathers ecosystem context, researches supporting evidence, writes an intelligence brief, red-teams that brief, and then verifies the final report before shipping it. We also added self-correction, API key rotation, validated memory, a live dashboard, and HTML report export. The result is an agent system that does not just talk about software changes, it investigates them, challenges them, and produces a deliverable artifact a team could actually use.

## 3-Minute Demo Story

1. Start with the problem:
   Teams cannot manually track every important change across fast-moving SDKs, repos, and ecosystems.

2. Introduce the solution:
   Project Overwatch acts like a small AI analyst team rather than a single chatbot.

3. Show the flow:
   Monitor -> Signal Analyst -> Researcher -> Analyst -> Red Team Reviewer -> Verifier

4. Explain why this matters:
   Each stage reduces a different failure mode:
   - monitor finds current changes
   - signal adds market context
   - research gathers proof
   - analyst synthesizes meaning
   - red team attacks weak claims
   - verifier decides whether the result is trustworthy

5. Show the dashboard:
   Point out evidence preview, attempt tracking, self-correction trace, and final report.

6. Show the output:
   Open `output/latest_report.html` and describe it as the final intelligence artifact.

## Judge-Friendly Framing

Use this framing repeatedly:

- Perception: it detects current repo and release changes
- Reasoning: it uses a role-based multi-agent workflow
- Tool Use: it calls GitHub, scraping, signal, memory, and delivery tools
- Self-Correction: it retries weak outputs with correction feedback
- Action: it exports and delivers a final report
- Impact: it compresses manual repo analysis into an automated workflow

## Likely Judge Questions

### Why multi-agent instead of one model call?

Because detection, research, synthesis, adversarial review, and verification are different jobs. Splitting them gives better control, traceability, and reliability than a single prompt.

### Why do you need a red team and verifier?

Because raw LLM outputs can sound convincing even when they are weakly grounded. The red team attacks claims, and the verifier decides whether the final report is good enough to ship or needs retry.

### Why memory?

Memory provides validated historical context so the system can notice patterns across runs, but it is intentionally treated as background context, not proof of current changes.

### What makes this more than a chatbot?

It uses tools, structured tasks, retries, validation, delivery, and memory. It is a repeatable workflow that produces a usable artifact, not just a conversation.

### What is the main limitation?

It is still a live LLM system, so output quality can vary and external APIs can affect runtime. That is why the project emphasizes grounding, retries, and validation.

## Strong Closing Line

Project Overwatch does not just summarize repository activity. It investigates, critiques, verifies, and delivers a report that is much closer to what a real analyst workflow would produce.
