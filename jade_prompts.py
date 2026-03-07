#!/usr/bin/env python3
"""
jade_prompts.py

Single source of truth for Jade system prompt assembly.
build_system_prompt() is the ONLY place prompts are assembled — never inline.

No API calls. No side effects. Pure file reads and string assembly.
"""

import sys
from pathlib import Path

JADE_DIR      = Path("/Users/spencerhatch/Jade")
SOUL_PATH     = JADE_DIR / "SOUL.md"
GOALS_PATH    = JADE_DIR / "memory" / "ACTIVE_GOALS.md"
STEERING_PATH = JADE_DIR / "AI_STEERING_RULES.md"


def _load(path: Path, required: bool = True) -> str:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required file missing: {path}")
        print(f"[jade_prompts] WARNING: optional file missing: {path}", file=sys.stderr)
        return ""
    return path.read_text(encoding="utf-8")


def build_system_prompt(context: dict | None = None) -> str:
    """
    Assemble the Jade system prompt.

    Args:
        context: Optional runtime data for the briefing:
            today (str), weather (str), calendar_events (list[str]),
            assignments (list[str])

    Returns:
        Complete system prompt string.

    Raises:
        FileNotFoundError: if SOUL.md or ACTIVE_GOALS.md are missing.
    """
    soul     = _load(SOUL_PATH, required=True)
    steering = _load(STEERING_PATH, required=False)
    goals    = _load(GOALS_PATH, required=True)

    sections = [soul]
    if steering:
        sections.append(steering)
    sections.append(goals)
    if context:
        sections.append(_format_context(context))

    return "\n\n---\n\n".join(sections)


def _format_context(ctx: dict) -> str:
    lines = ["## RUNTIME CONTEXT\n"]
    if "today" in ctx:
        lines.append(f"Today: {ctx['today']}")
    if "weather" in ctx:
        lines.append(f"Weather: {ctx['weather']}")
    if "calendar_events" in ctx:
        evts = ctx["calendar_events"]
        if evts:
            lines.append("\nCalendar events today:")
            lines.extend(f"  • {e}" for e in evts)
        else:
            lines.append("\nCalendar: No events today.")
    if "assignments" in ctx:
        asgn = ctx["assignments"]
        if asgn:
            lines.append("\nAssignments due (next 48h):")
            lines.extend(f"  • {a}" for a in asgn)
        else:
            lines.append("\nAssignments: None due in the next 48 hours.")
    if ctx.get("missed_nightly"):
        lines.append("\nNote: No check-in last night.")
    if ctx.get("priorities"):
        lines.append("\nStated priorities for today (from last night's check-in):")
        lines.extend(f"  • {p}" for p in ctx["priorities"])
    if ctx.get("stated_intentions"):
        lines.append("\nSpencer's stated intentions for today:")
        lines.extend(f"  • {i}" for i in ctx["stated_intentions"])
    return "\n".join(lines)


def build_nightly_system_prompt(context: dict) -> str:
    """
    Assemble system prompt for the nightly check-in session.
    Injects SOUL.md + ACTIVE_GOALS.md + nightly runtime context.
    """
    soul     = _load(SOUL_PATH, required=True)
    steering = _load(STEERING_PATH, required=False)
    goals    = _load(GOALS_PATH, required=True)

    sections = [soul]
    if steering:
        sections.append(steering)
    sections.append(goals)
    sections.append(_format_nightly_context(context))
    return "\n\n---\n\n".join(sections)


def _format_nightly_context(ctx: dict) -> str:
    lines = ["## NIGHTLY SESSION CONTEXT\n"]
    if "today" in ctx:
        lines.append(f"Today: {ctx['today']}")
    if "days_to_act" in ctx:
        lines.append(f"Days until ACT test (April 14): {ctx['days_to_act']}")
    if "calendar_events" in ctx:
        evts = ctx["calendar_events"]
        if evts:
            lines.append("\nToday's calendar events:")
            lines.extend(f"  • {e}" for e in evts)
        else:
            lines.append("\nCalendar: No events today.")
    if "domains" in ctx:
        lines.append(f"\nDomains to probe tonight: {', '.join(ctx['domains'])}")
    if ctx.get("recent_logs"):
        lines.append("\n## Recent Nightly Logs (last 3 nights — for continuity)\n")
        lines.append(ctx["recent_logs"])
    lines.append(
        "\n## Nightly Session Structure\n"
        "Run through phases A→B→C→D→E as instructed in each turn. "
        "Keep the total session under 12 minutes. "
        "Probe once on avoidance, then move on — do not badger. "
        "No motivational language. No fluff. Peer register throughout."
    )
    return "\n".join(lines)
