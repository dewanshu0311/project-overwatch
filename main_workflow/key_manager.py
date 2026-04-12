"""
Key Rotation Manager — True round-robin API key cycling with cooldown tracking.

Rate Limit Reference (Free Tier, per key):
  Groq llama-3.3-70b-versatile:
    - 30 RPM, 131,072 TPM, 1,000 RPD
  Firecrawl Free:
    - 500 credits/month, ~2 concurrent browsers

With 9 Groq keys: ~1.18M TPM effective capacity.
With 9 Firecrawl keys: ~4,500 credits/month.
"""

import os
import time
import threading
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()

# Per-key cooldown tracking: {service: {key_index: cooldown_expiry_timestamp}}
_cooldowns: dict[str, dict[int, float]] = {}
# Round-robin pointer: {service: next_index_to_try}
_pointers: dict[str, int] = {}
_lock = threading.Lock()


def _load_keys(service: str) -> list[str]:
    """Load all keys for a service from environment variables.

    Supports both plural (GROQ_API_KEYS) and singular (GROQ_API_KEY) env vars.
    Keys can be comma-separated with optional spaces.
    """
    keys_str = os.getenv(f"{service}_API_KEYS") or os.getenv(f"{service}_API_KEY")
    if not keys_str:
        return []
    return [k.strip() for k in keys_str.split(",") if k.strip()]


def _get_all_keys(service: str) -> list[str]:
    """Cache-friendly key loader (reads env once per service)."""
    if not hasattr(_get_all_keys, "_cache"):
        _get_all_keys._cache = {}
    if service not in _get_all_keys._cache:
        _get_all_keys._cache[service] = _load_keys(service)
    return _get_all_keys._cache[service]


def get_next_key(service: str) -> str:
    """Get the next available API key using true round-robin rotation.

    Advances the pointer each call so load is distributed evenly.
    Skips keys that are currently in cooldown.
    If all keys are cooling down, returns the one that expires soonest.
    """
    keys = _get_all_keys(service)
    if not keys:
        return "dummy"

    now = time.time()

    with _lock:
        if service not in _cooldowns:
            _cooldowns[service] = {}
        if service not in _pointers:
            _pointers[service] = 0

        # Try each key starting from the current pointer position
        n = len(keys)
        start = _pointers[service] % n

        for offset in range(n):
            idx = (start + offset) % n
            expiry = _cooldowns[service].get(idx, 0)
            if now >= expiry:
                # Advance pointer PAST this key for next call
                _pointers[service] = idx + 1
                return keys[idx]

        # All keys are cooling down — pick the one that expires soonest
        soonest_idx = min(_cooldowns[service], key=lambda i: _cooldowns[service][i])
        wait_time = _cooldowns[service][soonest_idx] - now
        _pointers[service] = soonest_idx + 1
        console.print(f"[yellow]All {service} keys cooling down. Shortest wait: {wait_time:.1f}s[/yellow]")
        return keys[soonest_idx]


def mark_key_exhausted(service: str, key: str, cooldown_seconds: float = 62.0) -> None:
    """Mark a key as rate-limited so it gets skipped for cooldown_seconds.

    Called by tools/agents when they detect a 429 rate limit error.
    Default cooldown is 62s (just over 1 minute, matching Groq's TPM window).
    """
    keys = _get_all_keys(service)
    if not keys:
        return
    if key not in keys:
        # FIX Issue 3: If exact key unknown, mark the most recently used key
        # (the one just before the current pointer).
        with _lock:
            ptr = _pointers.get(service, 0)
            idx = (ptr - 1) % len(keys)
            _cooldowns.setdefault(service, {})[idx] = time.time() + cooldown_seconds
            console.print(
                f"[dim]Key #{idx + 1}/{len(keys)} for {service} marked exhausted "
                f"(inferred from pointer). Cooling {cooldown_seconds:.0f}s.[/dim]"
            )
        return

    idx = keys.index(key)
    with _lock:
        _cooldowns.setdefault(service, {})[idx] = time.time() + cooldown_seconds

    remaining = sum(1 for i in range(len(keys))
                    if time.time() >= _cooldowns.get(service, {}).get(i, 0))
    console.print(
        f"[dim]Key #{idx + 1}/{len(keys)} for {service} exhausted. "
        f"Cooling {cooldown_seconds:.0f}s. {remaining} keys still available.[/dim]"
    )


def get_key_pool_status(service: str) -> dict:
    """Return status of all keys for monitoring/debugging."""
    keys = _get_all_keys(service)
    now = time.time()
    status = []
    for i, key in enumerate(keys):
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        expiry = _cooldowns.get(service, {}).get(i, 0)
        status.append({
            "index": i,
            "key": masked,
            "available": now >= expiry,
            "cooldown_remaining": max(0, expiry - now),
        })
    return {
        "service": service,
        "total_keys": len(keys),
        "available_keys": sum(1 for s in status if s["available"]),
        "pointer": _pointers.get(service, 0) % max(len(keys), 1),
        "keys": status,
    }
