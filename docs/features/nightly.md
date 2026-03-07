# Nightly Check-In
*Phase 1.5 | jade_nightly.py*

---

## What It Does

An interactive terminal session where Jade runs Spencer through a structured end-of-day
debrief. Five phases, under 12 minutes. Post-session, a second Haiku call extracts
structured data written to disk and passed to the next morning's briefing.

---

## Session Phases

| Phase | Label | What Happens |
|-------|-------|-------------|
| A | Day debrief | Greet, reference calendar, ask how highest-priority thing went, ask what got in the way |
| B | Domain check-ins | 1–2 focused questions per domain (ACT prep, lacrosse, WTT, college app) |
| C | Tomorrow planning | Propose top 3 priorities, ask Spencer to confirm/modify; ask for stated intentions |
| D | Open loops | Ask if anything unresolved needs closing before tomorrow |
| E | Close | 1–2 sentence honest send-off — no fluff |

Domain selection is calendar-aware (`select_domains(events)`):
- ACT prep: always included if ≤30 days to exam (April 14, 2026)
- WTT / lacrosse / college app: added when relevant calendar events exist
- Weekend: college app added automatically
- Max 3 domains per session

---

## Files Written

### `memory/logs/nightly/YYYY-MM-DD.md`
Structured session log extracted by a dedicated Haiku call:
- Day summary (2 sentences)
- Domain check-ins (dict of domain → Spencer's response summary)
- Struggles / blockers
- Tomorrow's priorities (top 3, ranked)
- Spencer's stated intentions
- Open loops

### `memory/cache/tomorrow_context.json`
Schema:
```json
{
  "date": "2026-03-07",
  "priorities": ["string", "string", "string"],
  "stated_intentions": ["string"],
  "open_loops": ["string"],
  "struggles_yesterday": ["string"]
}
```
Written at Phase C completion (partial) and overwritten with full data post-session.
The morning briefing reads this file via `_load_nightly_context()`.

---

## Extraction Robustness

Post-session extraction uses a separate Haiku call with `_EXTRACTION_SYSTEM` instructing
JSON-only output. Three failure defenses:

1. **Fence stripping** — Haiku wraps JSON in ` ```json ``` ` despite instructions. These
   are stripped before `json.loads()`.
2. **Raw logging** — If parsing fails, the raw response is printed to stderr for debugging.
3. **Transcript fallback** — If extraction fails entirely, `_write_transcript_fallback()`
   writes the raw conversation as a markdown log (filtering out `[PHASE...]` control turns).

---

## launchd Scheduling

Plist: `launchd/com.jade.nightly.plist`

- Weekdays (Mon–Fri): 9:15 PM
- Weekends (Sat–Sun): 8:45 PM

launchd cannot spawn interactive terminals directly. Uses `osascript` to open a new
Terminal.app window running `jade_nightly.py`.

**Load command:**
```bash
cp ~/Jade/launchd/com.jade.nightly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jade.nightly.plist
```

**Manual run (bypasses dedup):**
```bash
python3 ~/Jade/jade_nightly.py --now
```

---

## Dedup Guard

`already_ran_today()` checks `tomorrow_context.json` — if it has today's date, the script
exits immediately. Use `--now` to override (useful for testing or re-running after a crash).

---

## Continuity Loop

```
Nightly check-in (Phase E complete)
    │
    ▼
tomorrow_context.json  ←── written with priorities, intentions, open_loops
    │
    ▼ (next morning)
jade_briefing.py reads it via _load_nightly_context()
    │
    ▼
Morning briefing includes:
  "Stated priorities for today (from last night's check-in): ..."
  "Spencer's stated intentions for today: ..."
```

If `tomorrow_context.json` is missing or dated yesterday, briefing notes "No check-in last night."
