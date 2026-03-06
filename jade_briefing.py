#!/usr/bin/env python3
"""
jade_briefing.py

Morning briefing — called by launchd at 7am.
Fetches live data, assembles context, calls Haiku, prints briefing, sends notification.

stdout → logs/briefing.log       (via launchd StandardOutPath)
stderr → logs/briefing_error.log (via launchd StandardErrorPath)
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

# load_dotenv before any import that reads env vars
from dotenv import load_dotenv
load_dotenv(Path("/Users/spencerhatch/Jade/.env"))

# Ensure Jade root is on path for launchd context (minimal shell PATH)
sys.path.insert(0, "/Users/spencerhatch/Jade")

import anthropic
from integrations.gcal import get_today_events
from integrations.schoology import get_upcoming_assignments
from integrations.weather import get_weather
from jade_prompts import build_system_prompt

_NOTIFIER   = "/opt/homebrew/bin/terminal-notifier"
_MODEL      = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 500


def notify(title: str, message: str) -> None:
    """Send macOS notification. Never raises — notification failure cannot crash briefing."""
    try:
        subprocess.run(
            [_NOTIFIER, "-title", title, "-message", message,
             "-sound", "default", "-group", "jade-briefing"],
            timeout=5,
            capture_output=True,
        )
    except Exception:
        pass


def run() -> None:
    # 1. Gather live data
    today       = date.today().strftime("%A, %B %-d")  # "Friday, March 6"
    weather     = get_weather()
    events      = get_today_events()
    assignments = get_upcoming_assignments()

    # 2. Assemble system prompt with runtime context
    context = {
        "today":           today,
        "weather":         weather,
        "calendar_events": events,
        "assignments":     assignments,
    }
    system_prompt = build_system_prompt(context=context)

    # 3. Call Haiku
    client   = anthropic.Anthropic()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=system_prompt,
        messages=[
            {"role": "user", "content": "Generate my morning briefing now. Follow the briefing format exactly."}
        ],
    )
    briefing = response.content[0].text

    # 4. Print full briefing (captured to briefing.log by launchd)
    print(briefing)

    # 5. Notify with first 2 non-empty lines
    lines   = [l for l in briefing.splitlines() if l.strip()]
    preview = "\n".join(lines[:2])
    notify("Jade — Morning Briefing", preview)


if __name__ == "__main__":
    try:
        run()
        sys.exit(0)
    except Exception as exc:
        print(f"[jade_briefing] FATAL: {exc}", file=sys.stderr)
        notify("Jade — Briefing Error", "Check logs/briefing_error.log")
        sys.exit(1)
