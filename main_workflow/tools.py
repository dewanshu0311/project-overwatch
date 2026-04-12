"""
CrewAI Tools — six tools the agents call to interact with the outside world.

Each tool follows the tool-design skill principles:
  - Clear description answering what/when/returns
  - Actionable error messages for agent recovery
  - Automatic key rotation via key_manager on rate limit errors
"""
import os
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

import requests
from crewai.tools import tool
from rich.console import Console
from .key_manager import get_next_key, mark_key_exhausted

console = Console()


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token and not token.startswith("your_"):
        headers["Authorization"] = f"token {token}"
    return headers


def _scrape_github_url(url: str) -> str | None:
    """Return concise GitHub evidence without noisy HTML chrome."""
    parsed = urlparse(url)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None

    owner, repo = parts[0], parts[1]
    headers = _github_headers()

    if len(parts) >= 4 and parts[2] == "commit":
        sha = parts[3]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
        resp = requests.get(api_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        lines = [
            f"Commit: {data.get('sha', '')[:12]}",
            f"URL: {data.get('html_url')}",
            f"Message: {data.get('commit', {}).get('message', '').splitlines()[0]}",
            "Changed files:",
        ]
        ranked_files = sorted(
            data.get("files", []),
            key=lambda changed_file: (
                0 if str(changed_file.get("filename", "")).startswith("src/") else
                1 if str(changed_file.get("filename", "")) in {"README.md", "CHANGELOG.md", "api.md"} else
                2,
                -int(changed_file.get("changes", 0)),
            ),
        )
        for changed_file in ranked_files[:3]:
            lines.append(
                f"- {changed_file.get('filename')} | {changed_file.get('status')} | "
                f"{changed_file.get('changes')} changes | "
                f"{changed_file.get('blob_url') or changed_file.get('raw_url')}"
            )
        return "\n".join(lines)

    if len(parts) >= 5 and parts[2] == "blob":
        ref = parts[3]
        file_path = unquote("/".join(parts[4:]))
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{file_path}"
        resp = requests.get(raw_url, headers=headers, timeout=10)
        resp.raise_for_status()
        preview = "\n".join(resp.text.splitlines()[:80])[:2200]
        return (
            f"File: {file_path}\n"
            f"Source: {url}\n"
            "Content preview:\n"
            f"{preview}"
        )

    if len(parts) >= 3 and parts[2] == "releases":
        if len(parts) >= 5 and parts[3] == "tag":
            tag = parts[4]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
        else:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=1"
        resp = requests.get(api_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        release = data[0] if isinstance(data, list) and data else data
        if not release:
            return f"No release data found for {url}"
        body = (release.get("body") or "").strip()
        body_preview = "\n".join(body.splitlines()[:80])[:2200] if body else "No release notes body."
        return (
            f"Release: {release.get('name') or release.get('tag_name')}\n"
            f"URL: {release.get('html_url')}\n"
            "Notes preview:\n"
            f"{body_preview}"
        )

    return None


@tool("GitHubMonitorTool")
def github_monitor_tool(repo: str) -> str:
    """Fetch the latest commits from a GitHub repository.

    Use when: monitoring a repo for new architectural changes.
    Args: repo — format 'owner/name' (e.g. 'openai/openai-python')
    Returns: a structured evidence pack with commit URLs and touched files.
    """
    headers = _github_headers()
    try:
        url = f"https://api.github.com/repos/{repo}/commits"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        commits = resp.json()[:2]
        evidence_pack = []
        for commit in commits:
            detail_url = commit.get("url")
            detail = {}
            if detail_url:
                try:
                    detail_resp = requests.get(detail_url, headers=headers, timeout=10)
                    detail_resp.raise_for_status()
                    detail = detail_resp.json()
                except Exception as detail_error:
                    detail = {"detail_error": str(detail_error)}

            files = []
            changed_files = detail.get("files", [])
            ranked_files = sorted(
                changed_files,
                key=lambda changed_file: (
                    0 if str(changed_file.get("filename", "")).startswith("src/") else
                    1 if str(changed_file.get("filename", "")) in {"README.md", "CHANGELOG.md", "api.md"} else
                    2,
                    -int(changed_file.get("changes", 0)),
                ),
            )
            for changed_file in ranked_files[:2]:
                files.append(
                    f"- {changed_file.get('filename')} | {changed_file.get('status')} | "
                    f"{changed_file.get('changes')} changes | "
                    f"{changed_file.get('blob_url') or changed_file.get('raw_url')}"
                )

            evidence_pack.append({
                "sha": str(commit.get("sha", ""))[:12],
                "commit_url": commit.get("html_url"),
                "message": commit.get("commit", {}).get("message", "").splitlines()[0],
                "files": files,
            })

        lines = [f"Repository: {repo}", "Recent commit evidence:"]
        for item in evidence_pack:
            lines.append(
                f"- {item['sha']} | {item['message']} | {item['commit_url']}"
            )
            lines.extend([f"  {file_line}" for file_line in item["files"]])
        return "\n".join(lines)
    except Exception as e:
        return f"GitHub fetch failed for {repo}: {e}"


@tool("DeepScrapeTool")
def deep_scrape_tool(url: str) -> str:
    """Scrape a website's content for deep research using Firecrawl.

    Use when: need to read documentation, release notes, or PR discussions.
    Args: url — full URL to scrape
    Returns: markdown content (max 2000 chars) or error string.
    """
    try:
        github_result = _scrape_github_url(url)
        if github_result is not None:
            return github_result[:3000]
    except Exception as e:
        return f"GitHub scrape failed for {url}: {e}"

    api_key = get_next_key("FIRECRAWL")
    if api_key == "dummy" or api_key.startswith("your_"):
        return f"Simulated scrape for {url}: found key architectural changes in the latest release."
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=api_key)
        res = app.scrape_url(url)
        return res.get("markdown", "No content found.")[:2000]
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "rate" in err_str or "limit" in err_str:
            mark_key_exhausted("FIRECRAWL", api_key, cooldown_seconds=120)
        return f"Scrape failed (will retry with next key): {e}"


@tool("SlackAlertTool")
def slack_alert_tool(message: str) -> str:
    """Deliver a competitive intelligence alert to the team via Slack webhook.

    Use when: the final verified report is ready for delivery.
    Args: message — the alert text to post
    Returns: confirmation string or error.
    Falls back to writing output/alert_fallback.md if delivery fails.
    """
    webhook = os.getenv("WEBHOOK_URL")
    if not webhook or webhook.startswith("your_"):
        return _write_fallback(message, reason="No webhook configured")
    try:
        resp = requests.post(webhook, json={"text": message}, timeout=10)
        resp.raise_for_status()
        return "Delivered to Slack successfully."
    except Exception as e:
        return _write_fallback(message, reason=str(e))


def _write_fallback(message: str, reason: str) -> str:
    """Write alert to fallback file when Slack delivery fails."""
    from pathlib import Path
    fallback_path = Path("output/alert_fallback.md")
    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    with open(fallback_path, "w", encoding="utf-8") as f:
        f.write(f"# Intelligence Alert (Fallback)\n\n")
        f.write(f"**Reason for fallback:** {reason}\n\n")
        f.write(f"---\n\n{message}\n")
    console.print(f"[yellow]Slack failed ({reason}). Wrote fallback to {fallback_path}[/yellow]")
    return f"Slack unavailable. Report saved to {fallback_path}"


@tool("HackerNewsSignalTool")
def hackernews_signal_tool(query: str) -> str:
    """Fetch recent HackerNews discussions about a library or technology.

    Use when: gathering community sentiment and adoption signals.
    Args: query — search term (e.g. 'openai-python', 'anthropic sdk')
    Returns: top 3 HN discussion titles or 'no discussions found'.
    """
    try:
        url = (
            f"http://hn.algolia.com/api/v1/search"
            f"?query={query}&restrictSearchableAttributes=url,title&hitsPerPage=3"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        if not hits:
            return "No recent HN discussions found."

        now_ts = datetime.now(timezone.utc).timestamp()
        fresh_hits = []
        for hit in hits:
            created_at_ts = hit.get("created_at_i")
            if not created_at_ts:
                continue
            age_days = int((now_ts - float(created_at_ts)) // 86400)
            if age_days <= 30:
                fresh_hits.append((hit, age_days))

        if not fresh_hits:
            return "No relevant Hacker News discussions found in the last 30 days."

        return "HN Signals (last 30 days):\n" + "\n".join(
            [f"- {hit['title']} ({age_days}d ago)" for hit, age_days in fresh_hits[:3]]
        )
    except Exception as e:
        return f"HN fetch failed: {e}"


@tool("PyPIStatsTool")
def pypi_stats_tool(package_name: str) -> str:
    """Fetch PyPI download statistics for a Python package.

    Use when: measuring adoption velocity and community traction.
    Args: package_name — the PyPI package name (e.g. 'openai')
    Returns: recent download count or error string.
    """
    aliases = [package_name]
    if package_name.endswith("-python"):
        aliases.append(package_name[:-7])
    if package_name.endswith("-sdk-python"):
        aliases.append(package_name[:-11])
    if package_name.endswith("_python"):
        aliases.append(package_name[:-7])

    try:
        last_error = None
        for candidate in aliases:
            url = f"https://pypistats.org/api/packages/{candidate}/recent"
            resp = requests.get(url, timeout=10)
            if resp.ok:
                data = resp.json().get("data", {})
                alias_note = "" if candidate == package_name else f" (mapped from {package_name})"
                return (
                    f"PyPI Stats for {candidate}{alias_note}: "
                    f"{data.get('last_day', 0):,} downloads yesterday, "
                    f"{data.get('last_week', 0):,} last week."
                )
            last_error = f"{resp.status_code} {resp.reason}"
        return f"PyPI stats fetch failed for '{package_name}': {last_error}"
    except Exception as e:
        return f"PyPI stats fetch failed for '{package_name}': {e}"


@tool("MemoryQueryTool")
def memory_query_tool(query: str, repo: str) -> str:
    """Search cognitive memory for historical intelligence about a repository.

    Use when: looking for past architectural shifts, trend patterns, or prior reports.
    Args: query — natural language search, repo — 'owner/name' format
    Returns: historical report summaries or 'no historical data'.
    """
    try:
        from .memory import CognitiveMemory
        mem = CognitiveMemory()
        return mem.query_history(query=query, repo=repo, n_results=3)
    except Exception as e:
        return f"Memory query failed: {e}"
