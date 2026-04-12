"""
HTML Report Exporter — generates a polished intelligence report for browser viewing.

Uses Python's built-in string.Template (no Jinja2 dependency).
Outputs to output/latest_report.html.
"""

import json
from html import escape
from datetime import datetime
from pathlib import Path
from string import Template

from .schemas import IntelligenceReport

OUTPUT_DIR = Path("output")


def _html_text(value: str) -> str:
    """Escape text for safe HTML rendering while preserving newlines."""
    return escape(value).replace("\n", "<br>")


def _build_html(report: IntelligenceReport, repo: str, mode: str, elapsed: float) -> str:
    """Build the HTML string from a validated IntelligenceReport."""
    # Architecture changes rows
    changes_rows = ""
    for i, change in enumerate(report.architecture_changes, 1):
        changes_rows += f"<tr><td>{i}</td><td>{_html_text(change)}</td></tr>\n"

    # Sources rows
    sources_rows = ""
    for i, source in enumerate(report.cited_sources, 1):
        sources_rows += f"<tr><td>{i}</td><td>{_html_text(source)}</td></tr>\n"

    # Confidence bar color
    conf = report.confidence_score
    if conf >= 0.8:
        conf_color = "#22c55e"
        conf_label = "HIGH"
    elif conf >= 0.7:
        conf_color = "#eab308"
        conf_label = "MEDIUM"
    else:
        conf_color = "#ef4444"
        conf_label = "LOW"

    conf_pct = int(conf * 100)

    template = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Overwatch — Intelligence Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', -apple-system, system-ui, sans-serif;
            background: #0a0a0f;
            color: #e2e8f0;
            min-height: 100vh;
        }
        .container { max-width: 900px; margin: 0 auto; padding: 40px 24px; }

        /* Header */
        .header {
            text-align: center;
            padding: 48px 0 32px;
            border-bottom: 1px solid #1e293b;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 2.4rem;
            font-weight: 700;
            background: linear-gradient(135deg, #06b6d4, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .header .subtitle {
            color: #64748b;
            font-size: 1rem;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        /* Meta badges */
        .meta {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            justify-content: center;
            margin: 24px 0 40px;
        }
        .badge {
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .badge-repo { background: #1e3a5f; color: #38bdf8; }
        .badge-mode { background: #3b2f1e; color: #facc15; }
        .badge-time { background: #1a2e1a; color: #4ade80; }

        /* Sections */
        .section {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 28px;
            margin-bottom: 24px;
        }
        .section h2 {
            font-size: 1.1rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #1e293b;
        }
        .section p { line-height: 1.7; color: #cbd5e1; }

        /* Confidence bar */
        .confidence-container {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-top: 8px;
        }
        .confidence-bar {
            flex: 1;
            height: 12px;
            background: #1e293b;
            border-radius: 6px;
            overflow: hidden;
        }
        .confidence-fill {
            height: 100%;
            border-radius: 6px;
            transition: width 0.5s ease;
        }
        .confidence-label {
            font-size: 1.5rem;
            font-weight: 700;
        }
        .confidence-status {
            font-size: 0.85rem;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 12px;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            padding: 10px 12px;
            background: #0f172a;
            color: #94a3b8;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #1e293b;
            color: #e2e8f0;
        }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: #0f172a; }

        /* Footer */
        .footer {
            text-align: center;
            padding: 32px 0;
            color: #475569;
            font-size: 0.85rem;
            border-top: 1px solid #1e293b;
            margin-top: 40px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Project Overwatch</h1>
            <div class="subtitle">Autonomous Competitive Intelligence Report</div>
        </div>

        <div class="meta">
            <span class="badge badge-repo">$repo</span>
            <span class="badge badge-mode">Mode: $mode</span>
            <span class="badge badge-time">Completed in ${elapsed}s</span>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <p>$summary</p>
        </div>

        <div class="section">
            <h2>Confidence Score</h2>
            <div class="confidence-container">
                <span class="confidence-label" style="color: $conf_color">$conf_pct%</span>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: $conf_pct%; background: $conf_color;"></div>
                </div>
                <span class="confidence-status" style="background: ${conf_color}22; color: $conf_color">$conf_label</span>
            </div>
        </div>

        <div class="section">
            <h2>Architecture Changes Detected</h2>
            <table>
                <thead><tr><th>#</th><th>Change</th></tr></thead>
                <tbody>$changes_rows</tbody>
            </table>
        </div>

        <div class="section">
            <h2>Cited Sources</h2>
            <table>
                <thead><tr><th>#</th><th>Source</th></tr></thead>
                <tbody>$sources_rows</tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated by Project Overwatch &mdash; $timestamp</p>
            <p>Monolith Dynamics &bull; Agentathon 2026</p>
        </div>
    </div>
</body>
</html>""")

    return template.substitute(
        repo=_html_text(repo),
        mode=_html_text(mode),
        elapsed=f"{elapsed:.1f}",
        summary=_html_text(report.summary),
        conf_color=conf_color,
        conf_pct=str(conf_pct),
        conf_label=conf_label,
        changes_rows=changes_rows,
        sources_rows=sources_rows,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def export_html_report(
    report: IntelligenceReport,
    repo: str,
    mode: str,
    elapsed: float,
) -> Path:
    """Export the intelligence report as a polished HTML file.

    Returns the path to the generated HTML file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html = _build_html(report, repo, mode, elapsed)
    output_path = OUTPUT_DIR / "latest_report.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Also export JSON for programmatic access
    json_path = OUTPUT_DIR / "latest_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)

    return output_path
