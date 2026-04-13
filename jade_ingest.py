#!/usr/bin/env python3
"""
jade_ingest.py  v2

Paste raw text → Haiku classifies into 5 destination types → preview → confirm → write.

Destination types:
  task     → Tasks DB
  project  → Projects DB
  research → Research Vault DB
  practice → Practice Log DB
  note     → Appended to existing project page body (verbatim)

Usage:
  python3 jade_ingest.py
"""

import json
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path("/Users/spencerhatch/Jade/.env"))
sys.path.insert(0, "/Users/spencerhatch/Jade")

import anthropic
from integrations.jade_notion import (
    get_active_projects,
    create_task,
    create_project,
    create_research_job,
    create_practice_entry,
    append_page_content,
)

_MODEL      = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1500

_PRIORITY_MAP = {
    "High":   "🔴 High",
    "Medium": "🟡 Medium",
    "Low":    "🟢 Low",
}

_TASK_FIELDS     = ("name", "area", "priority", "due_date", "duration_mins", "linked_project")
_PROJECT_FIELDS  = ("name", "goal", "area", "why")
_RESEARCH_FIELDS = ("query", "area", "linked_project")
_PRACTICE_FIELDS = ("skill", "duration_mins", "date", "notes")
_NOTE_FIELDS     = ("content", "linked_project")

_TYPE_FIELDS = {
    "task":     _TASK_FIELDS,
    "project":  _PROJECT_FIELDS,
    "research": _RESEARCH_FIELDS,
    "practice": _PRACTICE_FIELDS,
    "note":     _NOTE_FIELDS,
}


# ── Classification prompt ─────────────────────────────────────────────────────

def _build_classify_prompt(today: str, project_names: list[str]) -> str:
    project_list = ", ".join(project_names) if project_names else "(none)"
    return (
        "You are a structured data extractor for a personal productivity system.\n\n"
        f"Today's date: {today}\n"
        f"Active projects: {project_list}\n\n"
        "Extract ALL items from the user's input as records. Return ONLY valid JSON.\n\n"

        "RECORD TYPES:\n"
        "- task       — action item, to-do, thing to accomplish\n"
        "- project    — named initiative with a goal and multiple steps\n"
        "- research   — question, 'look into', 'find out', 'understand X', 'research'\n"
        "- practice   — skill practice with an explicit duration ('did X min of Y', 'practiced Z for N hours')\n"
        "- note       — freeform idea or observation tied to a specific project\n"
        "- Ambiguous items → task\n\n"

        "AREA MAPPING — use EXACT strings:\n"
        "- \"School/ACT/College Apps\": ACT, SAT, math, science, english, khan, test prep, college, application, essay, common app\n"
        "- \"Wellbeing Think Tank\": WTT, think tank, wellbeing, CRM, pitch, nonprofit\n"
        "- \"Personal Goals\": lacrosse, practice, game, field, coach, cleats, stick, and everything else\n"
        "- \"Side Projects/Business\": startup, business, entre club, side project, revenue, client, sales\n"
        "- \"Reading/Learning\": book, reading, chapter, author, fiction, nonfiction\n"
        "- \"Manatee Aquatic\": manatee, aquatic, swim, pool, lifeguard\n\n"

        f"DUE DATE RESOLUTION (today = {today}):\n"
        "- 'today' → today's date\n"
        "- 'tomorrow' → today + 1 day\n"
        "- 'this Friday' / 'by Friday' / 'end of week' → the coming Friday\n"
        "- 'next week' → Monday of next week\n"
        "- 'end of month' → last day of current month\n"
        "- Vague ('soon', 'before the game', 'eventually') → null\n"
        "- Not mentioned → null\n\n"

        "PROJECT LINKING:\n"
        "- linked_project must be an exact name from the active projects list above, or null\n"
        "- Match by name similarity — if unclear, use null\n\n"

        "NOTE RULES:\n"
        "- content must be verbatim — never summarize or shorten\n"
        "- linked_project is required for notes — use the closest matching project name\n"
        "- If no project match, still return type:note with linked_project: null\n\n"

        "PRIORITY: High / Medium / Low (default Medium if not stated)\n\n"

        "Return this JSON structure. Include ALL records found:\n"
        "{\n"
        '  "records": [\n'
        "    {\n"
        '      "type": "task",\n'
        '      "name": "concise task title",\n'
        '      "priority": "High | Medium | Low",\n'
        '      "area": "exact area string",\n'
        '      "due_date": "YYYY-MM-DD or null",\n'
        '      "duration_mins": null,\n'
        '      "linked_project": "exact project name or null"\n'
        "    },\n"
        "    {\n"
        '      "type": "project",\n'
        '      "name": "project title",\n'
        '      "goal": "one sentence: what does done look like",\n'
        '      "area": "exact area string",\n'
        '      "why": "motivation or null"\n'
        "    },\n"
        "    {\n"
        '      "type": "research",\n'
        '      "query": "the question or topic",\n'
        '      "area": "exact area string",\n'
        '      "linked_project": "exact project name or null"\n'
        "    },\n"
        "    {\n"
        '      "type": "practice",\n'
        '      "skill": "skill name",\n'
        '      "duration_mins": 45,\n'
        f'      "date": "{today}",\n'
        '      "notes": "additional context or null"\n'
        "    },\n"
        "    {\n"
        '      "type": "note",\n'
        '      "content": "verbatim full text of the note — never shortened",\n'
        '      "linked_project": "exact project name from list — required"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Return ONLY valid JSON. No prose. No code fences. First character must be {."
    )


# ── Startup ───────────────────────────────────────────────────────────────────

def _load_projects() -> dict[str, str]:
    """Returns {project_name: page_id} for all active projects. ISC-I16: called once."""
    try:
        projects = get_active_projects()
        return {p["name"]: p["id"] for p in projects}
    except Exception as exc:
        print(f"[jade_ingest] Could not load projects: {exc}", file=sys.stderr)
        return {}


# ── Input collection ──────────────────────────────────────────────────────────

def collect_input() -> str:
    print("\n" + "━" * 50)
    print("  Jade — Ingest  v2")
    print("━" * 50)
    print("\nPaste tasks, projects, notes, research, or practice. Blank line when done.\n")
    lines = []
    try:
        while True:
            line = input()
            if not line.strip():
                break
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        pass
    return "\n".join(lines).strip()


# ── Classification ────────────────────────────────────────────────────────────

def classify(client: anthropic.Anthropic, raw: str, today: str, project_map: dict) -> dict:
    prompt = _build_classify_prompt(today, list(project_map.keys()))
    resp = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=prompt,
        messages=[{"role": "user", "content": raw}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = "\n".join(
            line for line in text.splitlines()
            if not line.strip().startswith("```")
        ).strip()
    return json.loads(text)


# ── Preview ───────────────────────────────────────────────────────────────────

def _fmt_task(r: dict, n: int) -> str:
    priority = _PRIORITY_MAP.get(r.get("priority", "Medium"), r.get("priority", ""))
    due      = f"  due {r['due_date']}" if r.get("due_date") else ""
    linked   = f"  → {r['linked_project']}" if r.get("linked_project") else ""
    return f"  {n}.  {priority}  {r['name']}  [{r.get('area', '?')}]{due}{linked}"


def _fmt_project(r: dict, n: int) -> str:
    goal = f"  \"{r['goal']}\"" if r.get("goal") else ""
    return f"  {n}.  ○  {r['name']}  [{r.get('area', '?')}]{goal}"


def _fmt_research(r: dict, n: int) -> str:
    linked = f"  → {r['linked_project']}" if r.get("linked_project") else ""
    return f"  {n}.  🔬  {r['query'][:70]}  [{r.get('area', '?')}]{linked}"


def _fmt_practice(r: dict, n: int) -> str:
    return f"  {n}.  💪  {r.get('skill', '?')} — {r.get('duration_mins', '?')} min  [{r.get('date', '?')}]"


def _fmt_note(r: dict, n: int) -> str:
    snippet  = r.get("content", "")[:60]
    ellipsis = "…" if len(r.get("content", "")) > 60 else ""
    project  = r.get("linked_project") or "⚠ no project"
    return f"  {n}.  📝  → {project}: \"{snippet}{ellipsis}\""


_FORMATTERS = {
    "task":     _fmt_task,
    "project":  _fmt_project,
    "research": _fmt_research,
    "practice": _fmt_practice,
    "note":     _fmt_note,
}

_TYPE_LABEL = {
    "task": "Tasks", "project": "Projects", "research": "Research",
    "practice": "Practice", "note": "Notes",
}


def preview(data: dict) -> int:
    """Print numbered summary grouped by type. Returns total record count."""
    records = data.get("records", [])
    if not records:
        print("\nNothing to ingest.")
        return 0

    print(f"\n{'─' * 54}")

    # Group while preserving flat numbering
    by_type: dict[str, list[tuple[int, dict]]] = {}
    for i, rec in enumerate(records, 1):
        t = rec.get("type", "task")
        by_type.setdefault(t, []).append((i, rec))

    unlinked_notes = []
    for type_key in ("task", "project", "research", "practice", "note"):
        group = by_type.get(type_key, [])
        if not group:
            continue
        print(f"{_TYPE_LABEL[type_key]} ({len(group)}):")
        for n, rec in group:
            print(_FORMATTERS[type_key](rec, n))
            if type_key == "note" and not rec.get("linked_project"):
                unlinked_notes.append(n)

    if unlinked_notes:
        nums = ", ".join(f"#{n}" for n in unlinked_notes)
        print(f"\n⚠  Note {nums}: no matching project — will prompt before writing.")

    print(f"{'─' * 54}")
    return len(records)


# ── Confirm + edit loop ───────────────────────────────────────────────────────

def confirm_and_edit(data: dict, project_map: dict) -> dict:
    """Show preview, ask [y]es / [c]hange in a loop. Returns confirmed data."""
    while True:
        total = preview(data)
        if total == 0:
            sys.exit(0)

        try:
            answer = input("\nWrite to Notion? [y / c]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)

        if answer == "y":
            return data

        if answer != "c":
            continue

        # ── Change flow ──────────────────────────────────────────────
        records = data.get("records", [])
        try:
            raw_n = input(f"Which item? (1–{total}): ").strip()
            idx   = int(raw_n) - 1
            if not (0 <= idx < total):
                raise ValueError
        except (ValueError, EOFError, KeyboardInterrupt):
            print("Invalid selection.")
            continue

        rec    = records[idx]
        fields = _TYPE_FIELDS.get(rec.get("type", "task"), _TASK_FIELDS)

        print(f"Fields: {' / '.join(fields)}")
        try:
            field = input("Field to change: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            continue

        if field not in fields:
            print(f"Unknown field '{field}'. Valid: {', '.join(fields)}")
            continue

        current = rec.get(field)
        prompt  = f"New {field}" + (f" (current: {current})" if current else "") + ": "
        try:
            new_val = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            continue

        if new_val:
            # duration_mins and date fields need type coercion
            if field == "duration_mins":
                try:
                    new_val = int(new_val)
                except ValueError:
                    print("duration_mins must be an integer.")
                    continue
            rec[field] = new_val
            print(f"  ✓ {field} updated.")


# ── Write functions ───────────────────────────────────────────────────────────

def _write_task(rec: dict, project_map: dict) -> bool:
    project_id = project_map.get(rec.get("linked_project") or "")
    due = None
    if rec.get("due_date"):
        try:
            due = date.fromisoformat(rec["due_date"])
        except ValueError:
            pass
    priority = _PRIORITY_MAP.get(rec.get("priority", "Medium"), "🟡 Medium")
    page_id = create_task(
        name       = rec["name"],
        area       = rec.get("area", "Personal Goals"),
        priority   = priority,
        due_date   = due,
        duration   = rec.get("duration_mins"),
        project_id = project_id,
    )
    return bool(page_id)


def _write_project(rec: dict) -> bool:
    goal = rec.get("goal") or rec["name"]
    try:
        page_id = create_project(
            name = rec["name"],
            goal = goal,
            area = rec.get("area", "Personal Goals"),
            why  = rec.get("why"),
        )
    except ValueError as exc:
        print(f"    ({exc})", file=sys.stderr)
        return False
    return bool(page_id)


def _write_research(rec: dict, project_map: dict) -> bool:
    project_id = project_map.get(rec.get("linked_project") or "")
    page_id = create_research_job(
        query      = rec["query"],
        area       = rec.get("area", "Personal Goals"),
        project_id = project_id,
    )
    return bool(page_id)


def _write_practice(rec: dict) -> bool:
    entry_date = date.today()
    if rec.get("date"):
        try:
            entry_date = date.fromisoformat(rec["date"])
        except ValueError:
            pass
    duration = rec.get("duration_mins")
    if not isinstance(duration, int):
        try:
            duration = int(duration)
        except (TypeError, ValueError):
            duration = 0
    page_id = create_practice_entry(
        skill        = rec.get("skill", "Unknown"),
        duration_mins = duration,
        entry_date   = entry_date,
        notes        = rec.get("notes"),
    )
    return bool(page_id)


def _write_note(rec: dict, project_map: dict) -> bool:
    linked = rec.get("linked_project")
    page_id = project_map.get(linked or "")

    if not page_id:
        print(f"    ⚠  No matching project for note{f' ({linked!r})' if linked else ''}.")
        try:
            ans = input("    Create as task instead? [y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = "n"
        if ans in {"y", "yes"}:
            fallback_id = create_task(
                name     = rec["content"][:100],
                area     = "Personal Goals",
                priority = "🟡 Medium",
            )
            return bool(fallback_id)
        return False

    return append_page_content(page_id, rec["content"])


_WRITERS = {
    "task":     lambda r, pm: _write_task(r, pm),
    "project":  lambda r, pm: _write_project(r),
    "research": lambda r, pm: _write_research(r, pm),
    "practice": lambda r, pm: _write_practice(r),
    "note":     lambda r, pm: _write_note(r, pm),
}


# ── Run ───────────────────────────────────────────────────────────────────────

def run() -> None:
    # ISC-I16: project_map fetched once at startup
    project_map = _load_projects()
    today       = date.today().isoformat()

    raw = collect_input()
    if not raw:
        print("Nothing entered. Exiting.")
        sys.exit(0)

    client = anthropic.Anthropic()
    try:
        data = classify(client, raw, today, project_map)
    except Exception as exc:
        print(f"\n[jade_ingest] Classification failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if not data.get("records"):
        print("\nNothing to ingest.")
        sys.exit(0)

    data = confirm_and_edit(data, project_map)

    print("\nWriting...")
    counts: dict[str, int] = {}
    failed = 0
    for rec in data.get("records", []):
        rtype  = rec.get("type", "task")
        writer = _WRITERS.get(rtype, _WRITERS["task"])
        label  = rec.get("name") or rec.get("query") or rec.get("skill") or rec.get("content", "")[:50]
        ok     = writer(rec, project_map)
        if ok:
            print(f"  ✓  [{rtype}] {label}")
            counts[rtype] = counts.get(rtype, 0) + 1
        else:
            if rtype != "note":  # note already prints its own failure context
                print(f"  ✗  [{rtype}] {label} (failed — check stderr)")
            failed += 1

    parts = [f"{n} {t}(s)" for t, n in counts.items()]
    if failed:
        parts.append(f"{failed} failed")
    print(f"\n{', '.join(parts) or 'Nothing written'}.")


if __name__ == "__main__":
    try:
        run()
        sys.exit(0)
    except Exception as exc:
        print(f"[jade_ingest] FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
