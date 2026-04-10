#!/usr/bin/env python3
"""
jade_prompts.py

Single source of truth for Jade system prompt assembly.
build_system_prompt() is the ONLY place prompts are assembled — never inline.

No API calls. No side effects. Pure file reads and string assembly.
"""

import sys
from datetime import datetime
from pathlib import Path

JADE_DIR      = Path("/Users/spencerhatch/Jade")
SOUL_PATH     = JADE_DIR / "SOUL.md"
GOALS_PATH    = JADE_DIR / "memory" / "ACTIVE_GOALS.md"
STEERING_PATH = JADE_DIR / "AI_STEERING_RULES.md"


_BRIEFING_TONE = """\
## BRIEFING TONE
Write like you're talking, not generating a report. Use natural transitions —
"looks like", "so", "heads up", "one thing worth knowing". Vary sentence
length. No bullet-point brain. Keep it conversational but not slow.

In the follow-up chat after the briefing: you drive toward closure. When the
conversation feels naturally complete, ask a closing question — "Is that all
for today?" or similar. Wait for Spencer's confirmation before ending."""


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
    sections.append(_BRIEFING_TONE)
    if context:
        sections.append(_format_context(context))

    return "\n\n---\n\n".join(sections)


_PRIORITY_LABEL = {
    "🔴 High":   "🔴 [High]",
    "🟡 Medium": "🟡 [Med] ",
    "🟢 Low":    "🟢 [Low] ",
}


def _format_task_line(task: dict) -> str:
    """Format a task dict as a single briefing line."""
    label    = _PRIORITY_LABEL.get(task.get("priority") or "", "   [?]  ")
    name     = task.get("name") or "Untitled"
    parts    = [f"{label} {name}"]

    duration = task.get("duration")
    if duration:
        parts.append(f"{duration} mins")

    energy = task.get("energy") or ""
    # Strip leading emoji from "🔵 Deep Work" → "Deep Work"
    energy_clean = energy.split(" ", 1)[-1] if energy else ""
    if energy_clean:
        parts.append(f"({energy_clean})")

    due = task.get("due") or ""
    if "T" in due:
        try:
            # ISO datetime with offset — parse and format as "due H:MMam/pm"
            dt = datetime.fromisoformat(due)
            parts.append(f"due {dt.strftime('%-I:%M%p').lower()}")
        except ValueError:
            pass
    else:
        parts.append("anytime")

    return " — ".join(parts)


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
    if "tasks_today" in ctx:
        tasks = ctx["tasks_today"]
        if tasks:
            lines.append("\nToday's tasks:")
            lines.extend(f"  {_format_task_line(t)}" for t in tasks)
        else:
            lines.append("\nToday's tasks: none scheduled.")
    if ctx.get("tasks_overdue"):
        lines.append("\nOverdue (not yet done):")
        for t in ctx["tasks_overdue"]:
            lines.append(f"  ⚠️  {t['name']} — was due {t['due']}")
    if ctx.get("missed_nightly"):
        lines.append("\nNote: No check-in last night.")
    if ctx.get("priorities"):
        lines.append("\nStated priorities for today (from last night's check-in):")
        lines.extend(f"  • {p}" for p in ctx["priorities"])
    if ctx.get("stated_intentions"):
        lines.append("\nSpencer's stated intentions for today:")
        lines.extend(f"  • {i}" for i in ctx["stated_intentions"])
    return "\n".join(lines)


_TIMEBLOCK_INSTRUCTIONS = """\
## TIMEBLOCK INSTRUCTIONS
Build a time-blocked schedule using ONLY the free windows provided.
Do not schedule into hard constraints (existing calendar events).
ACT Math and Science prep: 30 min/day (from stated commitment in ACTIVE_GOALS.md).
No deep work (math, essay, coding) in the 30 minutes immediately after lacrosse or practice ends.
Leave at least one 20-minute unblocked window per evening.
If tasks exceed available time, list the conflict in "conflicts" and ask which drops.
Represent open/unscheduled time in the "unscheduled_windows" field only, not as blocks.
Any block with "Unscheduled" in the title will be ignored by the write step.
Label meal blocks by time of day: "Breakfast" before 10am, "Lunch" between 11am–2pm,
"Afternoon break" between 2–5pm, "Dinner" after 5pm. Never label a block outside these
windows with a meal name that doesn't match the time.

Per block, include:
  - title: task name
  - start_iso / end_iso: ISO 8601 datetimes from the free window details provided
  - duration_min: integer minutes
  - basis: "from stated commitment" OR "estimated: [brief reason]"
  - rationale: one-line explanation

Return ONLY valid JSON. No prose. No code fences. Schema exactly:
{"blocks": [{"title": "string", "start_iso": "string", "end_iso": "string", \
"duration_min": 0, "basis": "string", "rationale": "string"}], \
"unscheduled_windows": [{"start_iso": "string", "end_iso": "string", "duration_min": 0}], \
"conflicts": ["string"]}

CRITICAL: Respond with valid JSON only. No prose. No explanation. No markdown fences. \
No text before or after the JSON object. First character must be {. Last character must be }. \
Any text outside the JSON object will break the system."""


def build_timeblock_system_prompt(context: dict) -> str:
    """
    Assemble system prompt for the timeblocking session.
    Stack: SOUL + STEERING + GOALS + BRIEFING_TONE + timeblock context + instructions.
    """
    soul     = _load(SOUL_PATH, required=True)
    steering = _load(STEERING_PATH, required=False)
    goals    = _load(GOALS_PATH, required=True)

    sections = [soul]
    if steering:
        sections.append(steering)
    sections.append(goals)
    sections.append(_BRIEFING_TONE)
    sections.append(_format_timeblock_context(context))
    sections.append(_TIMEBLOCK_INSTRUCTIONS)
    return "\n\n---\n\n".join(sections)


def _format_timeblock_context(ctx: dict) -> str:
    lines = ["## TIMEBLOCK CONTEXT\n"]
    if "target_date" in ctx:
        lines.append(f"Target date: {ctx['target_date']}")

    if ctx.get("hard_constraints"):
        lines.append("\nExisting calendar events (hard constraints — do not schedule over):")
        lines.extend(f"  • {e}" for e in ctx["hard_constraints"])
    else:
        lines.append("\nNo existing timed events.")

    if ctx.get("all_day_events"):
        lines.append("\nAll-day events (informational):")
        lines.extend(f"  • {e}" for e in ctx["all_day_events"])

    if ctx.get("free_windows"):
        lines.append("\nAvailable time windows (use ONLY these):")
        lines.extend(f"  • {w}" for w in ctx["free_windows"])
    else:
        lines.append("\nNo free windows available.")

    if ctx.get("free_windows_raw"):
        lines.append("\nFree window ISO details (use these for start_iso / end_iso in JSON):")
        for w in ctx["free_windows_raw"]:
            lines.append(f"  • start: {w['start_iso']}  end: {w['end_iso']}  ({w['duration_min']} min)")

    if ctx.get("missed_nightly"):
        lines.append("\nNote: No nightly check-in data. Use ACTIVE_GOALS.md commitments only.")
    else:
        if ctx.get("priorities"):
            lines.append("\nTomorrow's priorities (from nightly check-in):")
            lines.extend(f"  • {p}" for p in ctx["priorities"])
        if ctx.get("stated_intentions"):
            lines.append("\nStated intentions for tomorrow:")
            lines.extend(f"  • {i}" for i in ctx["stated_intentions"])
        if ctx.get("task_durations"):
            lines.append("\nExplicit durations stated during nightly:")
            for task, mins in ctx["task_durations"].items():
                lines.append(f"  • {task}: {mins} min")

    if ctx.get("schedule_additions"):
        lines.append("\nSchedule additions from morning chat:")
        lines.extend(f"  • {a}" for a in ctx["schedule_additions"])
    if ctx.get("focus"):
        lines.append(f"\nFocus for today: {ctx['focus']}")

    if ctx.get("assignments"):
        lines.append("\nSchoology assignments due (next 48h):")
        lines.extend(f"  • {a}" for a in ctx["assignments"])

    return "\n".join(lines)


_NIGHTLY_CLOSE_PROTOCOL = """\
## NIGHTLY CLOSE PROTOCOL
After you deliver Phase E (the send-off), append [SESSION_COMPLETE] on its own line
at the very end of your message. This token is machine-readable and will be stripped
before display. Do not explain or reference it.

Exit intent detection: if Spencer's input at any point AFTER Phase E is any of —
"stop", "done", "bye", "exit", "quit", "ok", "k", "great", "good night", "night",
"thanks", "thank you" — respond ONLY with [SESSION_COMPLETE], nothing else."""


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
    sections.append(_NIGHTLY_CLOSE_PROTOCOL)
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
    if "tasks_today" in ctx:
        tasks = ctx["tasks_today"]
        if tasks:
            lines.append("\nToday's tasks (reference these by name when asking about Spencer's work):")
            lines.extend(f"  {_format_task_line(t)}" for t in tasks)
    if ctx.get("tasks_overdue"):
        lines.append("\nOverdue tasks to follow up on:")
        lines.extend(f"  ⚠️  {t['name']} — was due {t['due']}" for t in ctx["tasks_overdue"])
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
