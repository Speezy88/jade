#!/usr/bin/env python3
"""
jade_nightly.py

Nightly check-in — interactive terminal conversation with Jade.
Launched via osascript from launchd at 9:15pm (weekdays) / 8:45pm (weekends).

Usage:
  python3 jade_nightly.py        # normal run; exits if already ran today
  python3 jade_nightly.py --now  # bypass dedup, run immediately
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path("/Users/spencerhatch/Jade/.env"))
sys.path.insert(0, "/Users/spencerhatch/Jade")

import anthropic
from integrations.gcal import get_today_events
from jade_prompts import build_nightly_system_prompt

_JADE_DIR     = Path("/Users/spencerhatch/Jade")
_NIGHTLY_DIR  = _JADE_DIR / "memory" / "logs" / "nightly"
_CONTEXT_PATH = _JADE_DIR / "memory" / "cache" / "tomorrow_context.json"
_MODEL        = "claude-haiku-4-5-20251001"
_MAX_TOKENS   = 1000

_EXTRACTION_SYSTEM = (
    "You are a structured data extractor. "
    "Return ONLY valid JSON. No prose. No code fences. No explanation. "
    "Schema (all fields required):\n"
    '{"day_summary": "string — 2-sentence synthesis of the day", '
    '"domain_checkins": {"domain_name": "Spencer response summary"}, '
    '"struggles": ["string"], '
    '"priorities": ["string", "string", "string"], '
    '"stated_intentions": ["string"], '
    '"open_loops": ["string"]}'
)


def already_ran_today() -> bool:
    if not _CONTEXT_PATH.exists():
        return False
    try:
        data = json.loads(_CONTEXT_PATH.read_text())
        return data.get("date") == date.today().isoformat()
    except Exception:
        return False


def select_domains(events: list[str]) -> list[str]:
    days_to_act = (date(2026, 4, 14) - date.today()).days
    is_weekend  = date.today().weekday() >= 5
    has_lacrosse = any("lacrosse" in e.lower() or "practice" in e.lower() for e in events)
    has_wtt      = any("think tank" in e.lower() or "wellbeing" in e.lower() for e in events)
    has_college  = any("college" in e.lower() for e in events)

    domains = []
    if days_to_act <= 30:
        domains.append("ACT prep")
    if has_wtt:
        domains.append("Wellbeing Think Tank")
    if has_lacrosse:
        domains.append("lacrosse")
    if has_college or is_weekend:
        domains.append("college app")
    if not domains:
        domains.append("ACT prep")
    return domains[:3]


def load_recent_logs(n: int = 3) -> str:
    """Read last n nightly logs for continuity context."""
    _NIGHTLY_DIR.mkdir(parents=True, exist_ok=True)
    logs = sorted(_NIGHTLY_DIR.glob("*.md"), reverse=True)[:n]
    if not logs:
        return ""
    return "\n\n---\n\n".join(p.read_text() for p in logs)


def chat(client: anthropic.Anthropic, system: str,
         history: list[dict], user_content: str) -> str:
    history.append({"role": "user", "content": user_content})
    response = client.messages.create(
        model=_MODEL, max_tokens=_MAX_TOKENS,
        system=system, messages=history,
    )
    text = response.content[0].text
    history.append({"role": "assistant", "content": text})
    return text


def jade(text: str) -> None:
    print(f"\nJade: {text}\n")


def ask() -> str:
    try:
        return input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[session interrupted]")
        return "__EXIT__"


def extract_structured(client: anthropic.Anthropic, history: list[dict]) -> tuple[dict, str]:
    """Single structured Haiku call — returns (parsed dict, raw string)."""
    transcript = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history
    )
    response = client.messages.create(
        model=_MODEL,
        max_tokens=800,
        system=_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": transcript}],
    )
    raw = response.content[0].text.strip()

    # Strip markdown fences Haiku sometimes adds despite instructions
    if raw.startswith("```"):
        raw = "\n".join(
            l for l in raw.splitlines()
            if not l.strip().startswith("```")
        ).strip()

    return json.loads(raw), raw


def _write_transcript_fallback(history: list[dict], today: date) -> None:
    """Write raw conversation transcript when structured extraction fails."""
    _NIGHTLY_DIR.mkdir(parents=True, exist_ok=True)
    path = _NIGHTLY_DIR / f"{today.isoformat()}.md"
    transcript = "\n\n".join(
        f"**{m['role'].upper()}:** {m['content']}" for m in history
        if not m["content"].startswith("[PHASE")
    )
    path.write_text(
        f"# Nightly Log — {today.isoformat()} (raw transcript — extraction failed)\n\n{transcript}\n"
    )
    print(f"[jade_nightly] Fallback transcript written: {path}", file=sys.stderr)


def write_nightly_log(data: dict) -> None:
    _NIGHTLY_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    path  = _NIGHTLY_DIR / f"{today}.md"

    def fmt_list(items: list) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "(none)"

    def fmt_dict(d: dict) -> str:
        return "\n".join(f"**{k}:** {v}" for k, v in d.items()) if d else "(none)"

    path.write_text(f"""# Nightly Log — {today}

## Day Summary
{data.get("day_summary", "(not captured)")}

## Domain Check-ins
{fmt_dict(data.get("domain_checkins", {}))}

## Struggles / Blockers
{fmt_list(data.get("struggles", []))}

## Tomorrow's Priorities
{fmt_list(data.get("priorities", []))}

## Spencer's Stated Intentions
{fmt_list(data.get("stated_intentions", []))}

## Open Loops
{fmt_list(data.get("open_loops", []))}
""")


def write_tomorrow_context(data: dict) -> None:
    _CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONTEXT_PATH.write_text(json.dumps({
        "date":                date.today().isoformat(),
        "priorities":          data.get("priorities", []),
        "stated_intentions":   data.get("stated_intentions", []),
        "open_loops":          data.get("open_loops", []),
        "struggles_yesterday": data.get("struggles", []),
    }, indent=2))


def run(force: bool = False) -> None:
    if not force and already_ran_today():
        print("[jade_nightly] Already ran today — skipping. Use --now to override.")
        return

    today       = date.today()
    events      = get_today_events()
    domains     = select_domains(events)
    recent_logs = load_recent_logs(3)

    context = {
        "today":           today.strftime("%A, %B %-d"),
        "calendar_events": events,
        "domains":         domains,
        "recent_logs":     recent_logs,
        "days_to_act":     (date(2026, 4, 14) - today).days,
    }

    system  = build_nightly_system_prompt(context)
    client  = anthropic.Anthropic()
    history: list[dict] = []

    print("\n" + "━" * 50)
    print("  Jade — Nightly Check-In")
    print("━" * 50 + "\n")

    # ── Phase A: Day debrief ──────────────────────────────────────────
    opening = chat(client, system, history,
        "[PHASE A] Open the nightly check-in. Greet Spencer briefly, "
        "reference something specific from today's calendar, then ask "
        "how his highest-priority thing went today.")
    jade(opening)

    r1 = ask()
    if r1 == "__EXIT__": return

    follow_up = chat(client, system, history, r1 +
        "\n[PHASE A continued] Ask what got in the way today, if anything.")
    jade(follow_up)

    r2 = ask()
    if r2 == "__EXIT__": return

    # ── Phase B: Domain check-ins ─────────────────────────────────────
    for domain in domains:
        q = chat(client, system, history, r2 +
            f"\n[PHASE B - DOMAIN: {domain}] Ask 1-2 focused questions about "
            f"Spencer's progress on {domain}. Be specific, not generic.")
        jade(q)
        r2 = ask()
        if r2 == "__EXIT__": return

    # ── Phase C: Tomorrow planning ────────────────────────────────────
    priorities_turn = chat(client, system, history, r2 +
        "\n[PHASE C] Synthesize what you heard. Propose tomorrow's top 3 "
        "priorities, ranked. Ask Spencer to confirm, reject, or modify.")
    jade(priorities_turn)

    r_priorities = ask()
    if r_priorities == "__EXIT__": return

    intentions_turn = chat(client, system, history, r_priorities +
        "\n[PHASE C continued] Ask: 'Anything specific you want to make "
        "sure happens tomorrow?'")
    jade(intentions_turn)

    r_intentions = ask()
    if r_intentions == "__EXIT__": return

    # Write partial context now — ensures ISC-4 even if session is interrupted
    write_tomorrow_context({
        "priorities":        [],
        "stated_intentions": [r_intentions] if r_intentions else [],
        "open_loops":        [],
        "struggles":         [],
    })

    # ── Phase D: Open loops ───────────────────────────────────────────
    loops_turn = chat(client, system, history, r_intentions +
        "\n[PHASE D] Ask if there's anything unresolved Spencer wants to "
        "close before tomorrow, or if we're good. Keep it brief.")
    jade(loops_turn)

    r_loops = ask()
    if r_loops == "__EXIT__": return

    # ── Phase E: Close ────────────────────────────────────────────────
    closing = chat(client, system, history, r_loops +
        "\n[PHASE E] Give a 1-2 sentence honest send-off. If it was a good "
        "day, say so plainly. If Spencer avoided something notable, name it "
        "briefly and close. No motivational fluff.")
    jade(closing)

    print("\n" + "━" * 50 + "\n")

    # ── Post-session: extract + write files ───────────────────────────
    raw_response = None
    try:
        structured, raw_response = extract_structured(client, history)
        write_nightly_log(structured)
        write_tomorrow_context(structured)
        print(f"[jade_nightly] Log written: memory/logs/nightly/{today.isoformat()}.md")
    except Exception as exc:
        print(f"[jade_nightly] WARNING: extraction failed ({exc})", file=sys.stderr)
        if raw_response is not None:
            print(f"[jade_nightly] Raw extraction response: {raw_response!r}", file=sys.stderr)
        _write_transcript_fallback(history, today)

    # ── Post-nightly: offer to block tomorrow ─────────────────────────
    print("\nWant me to block tomorrow? [yes / skip]")
    try:
        answer = input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""
    if answer in {"yes", "y", "yep", "yeah", "sure", "do it"}:
        import subprocess
        subprocess.run(
            ["python3", "/Users/spencerhatch/Jade/jade_timeblock.py"],
            check=False,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true",
                        help="Run immediately, bypass dedup check")
    args = parser.parse_args()
    run(force=args.now)
