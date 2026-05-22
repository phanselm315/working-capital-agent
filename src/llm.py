"""LLM access layer with an automatic, no-key demo mode.

Live mode  -- calls the Anthropic API (requires ANTHROPIC_API_KEY).
Demo mode  -- returns pre-generated Claude responses from demo_cache/.
              Activates automatically when no API key is present, so the
              repo runs end-to-end for anyone, with no key and no network.
"""
from __future__ import annotations

import json

import config

_cache = None


def _load_cache() -> dict:
    global _cache
    if _cache is None:
        if config.DEMO_CACHE_FILE.exists():
            _cache = json.loads(config.DEMO_CACHE_FILE.read_text(encoding="utf-8"))
        else:
            _cache = {}
    return _cache


def is_demo_mode() -> bool:
    return config.DEMO_MODE


def generate(cache_key: str, system: str, user: str, max_tokens: int = 900) -> str:
    """Return model text for a prompt.

    `cache_key` is a stable identifier used to look up the pre-generated
    response in demo mode. In live mode it is ignored.
    """
    if config.DEMO_MODE:
        cache = _load_cache()
        if cache_key in cache:
            return cache[cache_key]
        return (f"[demo mode] No cached response for '{cache_key}'. "
                f"Add an ANTHROPIC_API_KEY to .env to generate this live.")

    # Imported here so demo mode needs no extra dependency installed.
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
