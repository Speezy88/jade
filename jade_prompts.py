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
    return "\n".join(lines)
