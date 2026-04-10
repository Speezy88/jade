#!/usr/bin/env python3
"""
jade_briefing.py

Morning briefing — called by launchd at 7am.
Fetches live data, assembles context, calls Haiku, prints briefing, sends notification.

stdout → logs/briefing.log       (via launchd StandardOutPath)
stderr → logs/briefing_error.log (via launchd StandardErrorPath)
"""

import json
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
from integrations.jade_notion import get_overdue_tasks, get_todays_tasks
from integrations.schoology import get_upcoming_assignments
from integrations.weather import get_weather
from jade_prompts import build_system_prompt

_NOTIFIER             = "/opt/homebrew/bin/terminal-notifier"
_MODEL                = "claude-haiku-4-5-20251001"
_MAX_TOKENS           = 500
_CHAT_MAX_TOKENS      = 300
_CONTEXT_PATH         = Path("/Users/spencerhatch/Jade/memory/cache/tomorrow_context.json")
_MORNING_CONTEXT_PATH = Path("/Users/spencerhatch/Jade/memory/cache/morning_context.json")
_EXTRACTION_SYSTEM = (
    "Extract structured data from this morning briefing conversation. "
    "Return ONLY valid JSON matching this schema exactly:\n"
    '{"date": "YYYY-MM-DD", "schedule_additions": [], "adjustments": [], '
    '"focus": "", "notes": ""}\n'
    "schedule_additions: things Spencer wants added to the day. "
    "adjustments: changes to existing plans or priorities. "
    "focus: single most important thing if it surfaced, else empty string. "
    "notes: anything else worth carrying to Phase 2. "
    "Return ONLY valid JSON. No prose. No code fences."
)


def extract_morning_context(client: anthropic.Anthropic, history: list, today: str) -> tuple[dict, str]:
    """Single Haiku call to extract structured morning context from chat history."""
    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_EXTRACTION_SYSTEM,
        messages=history,
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = "\n".join(
            line for line in raw.splitlines()
            if not line.strip().startswith("```")
        ).strip()
    data = json.loads(raw)
    data["date"] = today
    return data, raw


def _write_morning_transcript_fallback(history: list, today: str) -> None:
    """Write raw transcript to memory/logs/morning/ when extraction fails."""
    log_dir = Path("/Users/spencerhatch/Jade/memory/logs/morning")
    log_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# Morning Chat — {today} (raw transcript — extraction failed)\n"]
    # Skip the first assistant turn (the full briefing — too long); keep the rest
    for msg in history[1:]:
        role = "Spencer" if msg["role"] == "user" else "Jade"
        lines.append(f"**{role}:** {msg['content']}\n")
    (log_dir / f"{today}.md").write_text("\n".join(lines))


def _load_nightly_context() -> dict:
    """Load last night's check-in context. Returns missed_nightly=True if absent/stale."""
    if not _CONTEXT_PATH.exists():
        return {"missed_nightly": True}
    try:
        data = json.loads(_CONTEXT_PATH.read_text())
        if data.get("date") == date.today().isoformat():
            return {
                "missed_nightly":    False,
                "priorities":        data.get("priorities", []),
                "stated_intentions": data.get("stated_intentions", []),
                "open_loops":        data.get("open_loops", []),
            }
    except Exception:
        pass
    return {"missed_nightly": True}


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
    tasks_today = get_todays_tasks()
    tasks_overdue = get_overdue_tasks()

    # 2. Assemble system prompt with runtime context
    context = {
        "today":           today,
        "weather":         weather,
        "calendar_events": events,
        "assignments":     assignments,
        "tasks_today":     tasks_today,
        "tasks_overdue":   tasks_overdue,
        **_load_nightly_context(),
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

    # 5. Chat tail
    _AFFIRMATIVES = {
        "yes", "yep", "yeah", "yup", "that's it", "all good",
        "good", "nope", "nah", "nothing", "done", "all set",
    }
    history = [{"role": "assistant", "content": briefing}]
    print("\nAnything you want to work through before the day starts?")

    for _ in range(10):
        try:
            user_input = input("> ").strip()
        except EOFError:
            break
        if not user_input:
            break
        # Jade asked a closing question and Spencer confirmed — wrap up
        last_jade = history[-1]["content"] if history[-1]["role"] == "assistant" else ""
        if len(history) >= 3 and last_jade.strip().endswith("?") and user_input.lower() in _AFFIRMATIVES:
            break
        history.append({"role": "user", "content": user_input})
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=_CHAT_MAX_TOKENS,
            system=system_prompt,
            messages=history,
        )
        reply = resp.content[0].text
        print(reply)
        history.append({"role": "assistant", "content": reply})

    # 6. Extract if Spencer said anything
    if any(m["role"] == "user" for m in history):
        today_iso = date.today().isoformat()
        raw = None
        try:
            structured, raw = extract_morning_context(client, history, today_iso)
            _MORNING_CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
            _MORNING_CONTEXT_PATH.write_text(json.dumps(structured, indent=2))
        except Exception as exc:
            print(f"[jade_briefing] WARNING: extraction failed ({exc})", file=sys.stderr)
            if raw is not None:
                print(f"[jade_briefing] Raw: {raw!r}", file=sys.stderr)
            _write_morning_transcript_fallback(history, date.today().isoformat())

    # 7. Notify after chat completes
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
