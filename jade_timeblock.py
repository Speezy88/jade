#!/usr/bin/env python3
"""
jade_timeblock.py

Calendar time-blocking — generates a Haiku-proposed schedule from live GCal data
and nightly context, presents for approval, then writes confirmed blocks to GCal.

Called by:
  - /timeblock slash command (on-demand)
  - jade_nightly.py post-Phase-E prompt (post-nightly, for tomorrow)

Usage:
  python3 jade_timeblock.py          # block tomorrow (default)
  python3 jade_timeblock.py --today  # block today
"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
load_dotenv(Path("/Users/spencerhatch/Jade/.env"))

sys.path.insert(0, "/Users/spencerhatch/Jade")

import anthropic
from integrations.gcal import create_event, delete_jade_events_for_date, get_events_for_date
from integrations.schoology import get_upcoming_assignments
from jade_prompts import build_timeblock_system_prompt

_MODEL             = "claude-haiku-4-5-20251001"
_MAX_TOKENS        = 4096
_CHAT_MAX_TOKENS   = 2048
_TZ                = ZoneInfo("America/Los_Angeles")
_LOG_DIR           = Path("/Users/spencerhatch/Jade/memory/logs/timeblock")
_SIGNALS_PATH      = Path("/Users/spencerhatch/Jade/memory/logs/duration_signals.jsonl")
_TOMORROW_CTX      = Path("/Users/spencerhatch/Jade/memory/cache/tomorrow_context.json")
_MORNING_CTX       = Path("/Users/spencerhatch/Jade/memory/cache/morning_context.json")
_MAX_ADJUST_ROUNDS = 3
_CONFIRM_WORDS     = {
    "", "yes", "y", "yep", "yeah", "yup", "ok", "okay",
    "looks good", "good", "confirmed", "confirm", "done", "all good", "all set",
}


# ── Context loaders ────────────────────────────────────────────────────────────

def _load_nightly_context(target_date: date) -> dict:
    """Load tomorrow_context.json if dated appropriately for target_date."""
    if not _TOMORROW_CTX.exists():
        return {"missed_nightly": True}
    try:
        data      = json.loads(_TOMORROW_CTX.read_text())
        ctx_date  = date.fromisoformat(data.get("date", ""))
        yesterday = target_date - timedelta(days=1)
        if ctx_date in (yesterday, target_date):
            return {
                "missed_nightly":    False,
                "priorities":        data.get("priorities", []),
                "stated_intentions": data.get("stated_intentions", []),
                "open_loops":        data.get("open_loops", []),
                "task_durations":    data.get("task_durations", {}),
            }
    except Exception:
        pass
    return {"missed_nightly": True}


def _load_morning_context() -> dict:
    """Load morning_context.json if dated today."""
    if not _MORNING_CTX.exists():
        return {}
    try:
        data = json.loads(_MORNING_CTX.read_text())
        if data.get("date") == date.today().isoformat():
            return {
                "schedule_additions": data.get("schedule_additions", []),
                "adjustments":        data.get("adjustments", []),
                "focus":              data.get("focus", ""),
            }
    except Exception:
        pass
    return {}


# ── Schedule computation ───────────────────────────────────────────────────────

def _compute_free_windows(events: list[dict], target_date: date) -> list[dict]:
    """
    Compute available time windows ≥25 min on target_date.

    - Applies 15-min buffer on either side of any event ≥60 min
    - Adds 30-min post-event buffer for lacrosse/practice events
    - Hard-blocks school hours 8:15am–3:00pm on weekdays if no school event present
    - Excludes before 7:00am and after 10:30pm
    Returns list of {start_dt, end_dt, duration_min} sorted by start.
    """
    day_start = datetime(target_date.year, target_date.month, target_date.day,
                         7, 0, tzinfo=_TZ)
    day_end   = datetime(target_date.year, target_date.month, target_date.day,
                         22, 30, tzinfo=_TZ)

    # Implicit school block on weekdays
    if target_date.weekday() < 5:
        school_s = datetime(target_date.year, target_date.month, target_date.day,
                            8, 15, tzinfo=_TZ)
        school_e = datetime(target_date.year, target_date.month, target_date.day,
                            15, 0, tzinfo=_TZ)
        has_school = any(
            not e.get("all_day")
            and e.get("start_dt") is not None
            and e["start_dt"] <= school_s
            and e.get("end_dt") is not None
            and e["end_dt"] >= school_e
            for e in events
        )
        if not has_school:
            events = events + [{
                "id": "_school_implicit", "summary": "School",
                "start_dt": school_s, "end_dt": school_e, "all_day": False,
            }]

    # Build list of (blocked_start, blocked_end) pairs
    blocked: list[tuple[datetime, datetime]] = []
    for e in events:
        if e.get("all_day"):
            continue
        s   = e.get("start_dt")
        end = e.get("end_dt")
        if not s or not end:
            continue
        duration_min = (end - s).total_seconds() / 60
        if duration_min >= 60:
            s   = s   - timedelta(minutes=15)
            end = end + timedelta(minutes=15)
        title = (e.get("summary") or "").lower()
        if "lacrosse" in title or "practice" in title:
            end = end + timedelta(minutes=30)
        blocked.append((max(s, day_start), min(end, day_end)))

    # Sort and merge overlapping blocks
    blocked.sort(key=lambda x: x[0])
    merged: list[tuple[datetime, datetime]] = []
    for s, e in blocked:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    # Walk gaps to find free windows
    windows: list[dict] = []
    cursor = day_start
    for s, e in merged:
        if s > cursor:
            gap_min = int((s - cursor).total_seconds() / 60)
            if gap_min >= 25:
                windows.append({"start_dt": cursor, "end_dt": s, "duration_min": gap_min})
        cursor = max(cursor, e)
    if cursor < day_end:
        gap_min = int((day_end - cursor).total_seconds() / 60)
        if gap_min >= 25:
            windows.append({"start_dt": cursor, "end_dt": day_end, "duration_min": gap_min})

    return windows


def _format_events(events: list[dict]) -> list[str]:
    out = []
    for e in events:
        title = e.get("summary", "(no title)")
        if e.get("all_day"):
            out.append(f"All day — {title}")
        elif e.get("start_dt"):
            t     = e["start_dt"].strftime("%-I:%M %p")
            end_t = e["end_dt"].strftime("%-I:%M %p") if e.get("end_dt") else ""
            out.append(f"{t}–{end_t} — {title}" if end_t else f"{t} — {title}")
    return out


def _format_windows(windows: list[dict]) -> list[str]:
    return [
        f"{w['start_dt'].strftime('%-I:%M %p')}–{w['end_dt'].strftime('%-I:%M %p')} "
        f"({w['duration_min']} min)"
        for w in windows
    ]


# ── Haiku helpers ──────────────────────────────────────────────────────────────

def _strip_fences(raw: str) -> str:
    if raw.startswith("```"):
        raw = "\n".join(
            line for line in raw.splitlines()
            if not line.strip().startswith("```")
        ).strip()
    return raw


def _call_haiku(client: anthropic.Anthropic, system_prompt: str,
                user_content: str, max_tokens: int) -> str:
    response = client.messages.create(
        model=_MODEL, max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text.strip()


# ── Display ────────────────────────────────────────────────────────────────────

def _print_proposal(proposal: dict) -> None:
    blocks      = proposal.get("blocks", [])
    unscheduled = proposal.get("unscheduled_windows", [])
    conflicts   = proposal.get("conflicts", [])

    print()
    if blocks:
        print("Scheduled blocks:")
        for b in blocks:
            try:
                start = datetime.fromisoformat(b["start_iso"]).astimezone(_TZ).strftime("%-I:%M %p")
                end   = datetime.fromisoformat(b["end_iso"]).astimezone(_TZ).strftime("%-I:%M %p")
            except Exception:
                start = b.get("start_iso", "?")
                end   = b.get("end_iso", "?")
            print(f"  {start} – {end}  {b['title']} ({b.get('duration_min', '?')} min)")
            print(f"               {b.get('basis', '')}")
            if b.get("rationale"):
                print(f"               {b['rationale']}")
    else:
        print("  No blocks could be scheduled.")

    if unscheduled:
        print("\nOpen windows:")
        for w in unscheduled:
            try:
                start = datetime.fromisoformat(w["start_iso"]).astimezone(_TZ).strftime("%-I:%M %p")
                end   = datetime.fromisoformat(w["end_iso"]).astimezone(_TZ).strftime("%-I:%M %p")
            except Exception:
                start = w.get("start_iso", "?")
                end   = w.get("end_iso", "?")
            print(f"  {start} – {end}  ({w.get('duration_min', '?')} min open)")

    if conflicts:
        print("\nConflicts:")
        for c in conflicts:
            print(f"  ⚠ {c}")
    print()


# ── Logging ────────────────────────────────────────────────────────────────────

def _log_overrides(original: dict, updated: dict, target_date: date) -> None:
    """Append one line per changed duration to duration_signals.jsonl."""
    _SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    orig_by_title = {b["title"]: b.get("duration_min") for b in original.get("blocks", [])}
    today_iso     = target_date.isoformat()
    with _SIGNALS_PATH.open("a") as f:
        for b in updated.get("blocks", []):
            orig_dur = orig_by_title.get(b["title"])
            if orig_dur and orig_dur != b.get("duration_min"):
                f.write(json.dumps({
                    "date":          today_iso,
                    "task":          b["title"],
                    "estimated_min": orig_dur,
                    "actual_min":    b.get("duration_min"),
                    "source":        "timeblock_override",
                }) + "\n")


def _write_timeblock_log(target_date: date, proposed: dict,
                         written_ids: list[str], overrides_count: int) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = _LOG_DIR / f"{target_date.isoformat()}.json"
    path.write_text(json.dumps({
        "date":            target_date.isoformat(),
        "proposed_blocks": proposed.get("blocks", []),
        "written_count":   len(written_ids),
        "written_ids":     written_ids,
        "overrides_count": overrides_count,
        "conflicts":       proposed.get("conflicts", []),
    }, indent=2))


# ── Main ───────────────────────────────────────────────────────────────────────

def run(target_date: date | None = None) -> None:
    if target_date is None:
        target_date = date.today() + timedelta(days=1)

    # Dedup check
    log_path = _LOG_DIR / f"{target_date.isoformat()}.json"
    if log_path.exists():
        print(f"Already blocked {target_date.strftime('%A, %B %-d')} — revise? [yes / no]")
        try:
            answer = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if answer not in {"yes", "y", "yep", "yeah"}:
            print("Keeping existing blocks.")
            return
        n = delete_jade_events_for_date(target_date)
        if n:
            print(f"Removed {n} previous Jade block(s).")

    client = anthropic.Anthropic()

    # Load inputs
    events      = get_events_for_date(target_date)
    nightly_ctx = _load_nightly_context(target_date)
    morning_ctx = _load_morning_context()
    assignments = get_upcoming_assignments()
    windows     = _compute_free_windows(events, target_date)

    if not windows:
        print(f"\n{target_date.strftime('%A, %B %-d')} is fully booked — "
              "no room to add blocks without moving something.")
        return

    # Build prompt context
    context = {
        "target_date":      target_date.strftime("%A, %B %-d"),
        "hard_constraints": _format_events([e for e in events if not e.get("all_day")]),
        "all_day_events":   _format_events([e for e in events if e.get("all_day")]),
        "free_windows":     _format_windows(windows),
        "free_windows_raw": [
            {
                "start_iso":    w["start_dt"].isoformat(),
                "end_iso":      w["end_dt"].isoformat(),
                "duration_min": w["duration_min"],
            }
            for w in windows
        ],
        "assignments": assignments,
        **nightly_ctx,
        **morning_ctx,
    }
    system_prompt = build_timeblock_system_prompt(context)

    print("\n" + "━" * 50)
    print(f"  Jade — Time Blocks for {target_date.strftime('%A, %B %-d')}")
    print("━" * 50)
    print("\nBuilding schedule...")

    # Initial Haiku call
    raw = _call_haiku(
        client, system_prompt,
        f"Build the time-blocked schedule for {target_date.strftime('%A, %B %-d')}. "
        "Respond with the JSON object only. First character must be {. Last character must be }.",
        _MAX_TOKENS,
    )
    raw = _strip_fences(raw)
    if not raw.strip().endswith("}"):
        print("\n[jade_timeblock] WARNING: schedule response truncated "
              "(cut off before closing brace). Try again.")
        return
    try:
        proposal = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"\n[jade_timeblock] WARNING: schedule parse failed ({exc}).\nRaw:\n{raw}")
        return

    _print_proposal(proposal)

    # Adjustment loop
    overrides_count = 0
    for round_num in range(_MAX_ADJUST_ROUNDS):
        print("Hit enter to confirm, or type changes:")
        try:
            edit = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if edit.lower() in _CONFIRM_WORDS:
            break

        # Adjust via Haiku
        adjust_prompt = (
            "Current schedule (JSON):\n" + json.dumps(proposal) +
            "\n\nEdit request: " + edit +
            "\n\nReturn ONLY the updated schedule JSON with the same schema. Apply the edit precisely. "
            "Respond with the JSON object only. First character must be {. Last character must be }."
        )
        raw_updated = _call_haiku(client, system_prompt, adjust_prompt, _CHAT_MAX_TOKENS)
        raw_updated = _strip_fences(raw_updated)
        if not raw_updated.strip().endswith("}"):
            print("Couldn't parse update — response truncated. Keeping current schedule.")
            continue
        try:
            updated = json.loads(raw_updated)
            _log_overrides(proposal, updated, target_date)
            overrides_count += 1
            proposal = updated
            _print_proposal(proposal)
        except json.JSONDecodeError:
            print(f"Couldn't parse update — keeping current schedule.")

        if round_num == _MAX_ADJUST_ROUNDS - 1:
            print("(Max adjustments reached — writing schedule as-is.)")

    # Write to GCal
    blocks = proposal.get("blocks", [])
    if not blocks:
        print("No blocks to write.")
        _write_timeblock_log(target_date, proposal, [], overrides_count)
        return

    print(f"\nWriting {len(blocks)} block(s) to Google Calendar...")
    written_ids: list[str] = []
    for b in blocks:
        if "unscheduled" in b.get("title", "").lower():
            print(f"  — {b['title']} (skipped — display only)")
            continue
        try:
            start_dt = datetime.fromisoformat(b["start_iso"]).astimezone(_TZ)
            end_dt   = datetime.fromisoformat(b["end_iso"]).astimezone(_TZ)
            desc     = (f"jade: scheduled | est: {b.get('duration_min', '?')}min | "
                        f"source: {b.get('basis', 'jade')}")
            eid = create_event(b["title"], start_dt, end_dt, description=desc)
            if eid:
                written_ids.append(eid)
                print(f"  ✓ {b['title']}")
            else:
                print(f"  ✗ {b['title']} — write failed (check logs)")
        except Exception as exc:
            print(f"  ✗ {b.get('title', '?')} — {exc}", file=sys.stderr)

    print(f"\n{len(written_ids)}/{len(blocks)} blocks written.")
    _write_timeblock_log(target_date, proposal, written_ids, overrides_count)
    print(f"[jade_timeblock] Log: memory/logs/timeblock/{target_date.isoformat()}.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", action="store_true",
                        help="Block today instead of tomorrow")
    args = parser.parse_args()
    target = date.today() if args.today else date.today() + timedelta(days=1)
    try:
        run(target)
        sys.exit(0)
    except Exception as exc:
        print(f"[jade_timeblock] FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
