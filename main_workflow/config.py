from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent

MAX_RETRIES = 2
CONFIDENCE_THRESHOLD = 0.7
TARGET_REPOS = ["openai/openai-python", "anthropics/anthropic-sdk-python"]
STATE_FILE = str(_PROJECT_ROOT / "last_checked.json")
MOCK_FIXTURE = _PROJECT_ROOT / "fixtures" / "mock_repo_alert.json"
