"""
State Manager — GitHub SHA-diffing for change detection.

Uses the GitHub API to compare the latest commit SHA against
a locally stored previous SHA. Falls back to a 24-hour timestamp
trigger if the API is unreachable.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import requests
from dotenv import load_dotenv
from rich.console import Console

from .config import STATE_FILE
load_dotenv()

console = Console()


def _load_state() -> Dict[str, Any]:
    """Load persisted SHA state from disk."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[yellow]Warning: state file corrupted, resetting: {e}[/yellow]")
    return {}


def _save_state(state: Dict[str, Any]) -> None:
    """Persist SHA state to disk."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def check_for_changes(repo: str) -> dict:
    """Check a GitHub repo for new commits since last check.

    Returns a dict with 'changed' bool, previous/latest SHA, and any error.
    If no GitHub token is set, returns changed=True with a clear 'degraded' flag
    so the caller knows this is not true live perception.
    """
    state_data = _load_state()
    repo_state = state_data.get(repo, {})
    previous_sha = repo_state.get("latest_sha")

    token = os.getenv("GITHUB_TOKEN")
    if not token or token.startswith("your_"):
        console.print("[yellow]No GitHub token — running in degraded demo mode[/yellow]")
        return {
            "changed": True,
            "previous_sha": "none",
            "latest_sha": "demo_no_token",
            "degraded": True,
            "error": "No GitHub token configured",
        }

    headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {token}"}

    # FIX Issue 1: /commits/{branch} returns a SINGLE object, not a list.
    # Use resp.json()["sha"], not resp.json()[0]["sha"].
    url = f"https://api.github.com/repos/{repo}/commits/main"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 404:
            url = f"https://api.github.com/repos/{repo}/commits/master"
            resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        latest_sha = resp.json()["sha"]
    except Exception as e:
        console.print(f"[yellow]GitHub API error: {e}[/yellow]")
        last_check_str = repo_state.get("last_check")
        if last_check_str:
            last_check = datetime.fromisoformat(last_check_str)
            if datetime.now(timezone.utc) - last_check > timedelta(hours=24):
                return {"changed": True, "previous_sha": previous_sha, "latest_sha": "fallback_timestamp_trigger"}
        return {"changed": False, "error": str(e)}

    state_data[repo] = {"latest_sha": latest_sha, "last_check": datetime.now(timezone.utc).isoformat()}
    _save_state(state_data)

    if not previous_sha or latest_sha != previous_sha:
        return {"changed": True, "previous_sha": previous_sha or "none", "latest_sha": latest_sha}

    return {"changed": False, "previous_sha": previous_sha, "latest_sha": latest_sha}
