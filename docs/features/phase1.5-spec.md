# Phase 1.5 Spec — Nightly Check-In
*File: docs/features/phase1.5-spec.md*
*Status: DRAFT — Pending Spencer approval before Plan Mode*

---

## 1. What / Why

A nightly interactive terminal session where Jade debriefs Spencer's day,
captures structured data about what happened vs. what was planned, and builds
tomorrow's context. This closes the feedback loop the morning briefing opens.

Without this, Jade is broadcasting at Spencer but learning nothing. With it,
the morning briefing becomes increasingly personalized and the system starts
functioning as a real COO — not just an alarm clock.

---

## 2. Trigger

| Day | Time | launchd label |
|-----|------|---------------|
| Weekdays (M–F) | 9:15pm | com.jade.nightly.plist |
| Weekends (Sat–Sun) | 8:45pm | com.jade.nightly.plist (same plist, two StartCalendarInterval entries) |

**Terminal interaction constraint:** launchd cannot spawn an interactive
terminal session directly. Implementation uses a launchd plist that opens
Terminal.app running `jade_nightly.py`. See Section 6.

---

## 3. Inputs

- `SOUL.md` — injected via `build_system_prompt()` in `jade_prompts.py`
- `memory/goals/ACTIVE_GOALS.md` — goal domains for relevant question selection
- Today's Google Calendar events — fetched via `integrations/gcal.py` (same
  call as morning briefing, no re-auth required)
- `memory/logs/nightly/YYYY-MM-DD.md` from prior nights — last 3 days read
  for continuity context (e.g. if Spencer mentioned something yesterday)
- Spencer's typed responses during the session

---

## 4. Outputs

### 4a. Nightly log file
Path: `memory/logs/nightly/YYYY-MM-DD.md`

Structure:
```
# Nightly Log — YYYY-MM-DD
## Day Summary
[Jade's 2-sentence synthesis of the day]

## Domain Check-ins
[One entry per domain probed, with Spencer's response]

## Struggles / Blockers
[Verbatim or paraphrased from Spencer's responses]

## Tomorrow's Priorities
[Jade's extracted list — 3 items max, ranked]

## Spencer's Stated Intentions
[Anything Spencer explicitly said he wants to do tomorrow]

## Open Loops
[Anything unresolved that Jade should watch for]
```

### 4b. Tomorrow context file
Path: `memory/cache/tomorrow_context.json`

Written at end of every nightly session. Read by `jade_briefing.py` at 7am.
Structure:
```json
{
  "date": "YYYY-MM-DD",
  "priorities": ["...", "...", "..."],
  "stated_intentions": ["..."],
  "open_loops": ["..."],
  "struggles_yesterday": ["..."]
}
```

If `tomorrow_context.json` is stale (date != today) or missing, morning
briefing falls back to ACTIVE_GOALS.md only — no error, no mention of gap
unless `missed_nightly` flag is set (see Section 7).

---

## 5. Conversation Flow

Jade drives the conversation. Spencer types responses. Jade adapts follow-up
questions based on responses — this is a real conversation, not a form.

### Phase A — Day debrief (always runs)
Jade opens with a brief acknowledgment of the day, then asks:
1. How did your highest-priority thing go today?
2. What got in the way?

Questions are reworded each night to avoid feeling robotic. Jade uses calendar
events to make them specific (e.g. "You had the Think Tank meeting today —
how'd that go?" not "How did your work go?").

### Phase B — Domain check-ins (context-dependent)
Jade selects 1–3 domains to probe based on today's calendar + ACTIVE_GOALS.md.

Domain selection rules (rule-based in Phase 1.5, adaptive in Phase 3+):
- **ACT prep** — probe if today was a non-practice weekday (high availability)
  or if ACT test date is ≤30 days out
- **College app** — probe if it's a weekend or if a college-related event
  was on calendar
- **Wellbeing Think Tank** — probe if a WTT event/task was on calendar
- **Lacrosse** — probe only on practice days (4:30–7pm blocks); keep brief

Jade asks 1–2 questions per domain, not an interrogation.

### Phase C — Tomorrow planning (always runs)
Jade synthesizes what it heard and proposes tomorrow's top 3 priorities.
Spencer can accept, reject, or modify. Final list is written to
`tomorrow_context.json`.

Jade also asks: "Anything specific you want to make sure happens tomorrow?"
Response written to `stated_intentions`.

### Phase D — Open loops (conditional)
Only runs if Jade detected an unresolved item during Phase A/B (e.g. Spencer
mentioned something but didn't resolve it). Jade flags it explicitly:
"You mentioned X but didn't land on a next step — want to close that now or
carry it?"

### Phase E — Close
Jade gives a 1–2 sentence send-off calibrated to the day. Not motivational
fluff — honest read. If it was a good day, say so. If Spencer avoided
something, name it briefly and close.

Total session target: **8–12 minutes**. Jade keeps it tight.

---

## 6. Implementation Constraints

### launchd + interactive terminal
launchd cannot directly spawn an interactive terminal. Solution:

```xml
<!-- com.jade.nightly.plist -->
<key>ProgramArguments</key>
<array>
    <string>/usr/bin/osascript</string>
    <string>-e</string>
    <string>tell application "Terminal" to do script "cd ~/Jade && python3 jade_nightly.py"</string>
</array>
```

This opens a new Terminal window at the scheduled time. Spencer interacts
there. Window stays open after session ends (Spencer closes manually).

### Model
`claude-haiku-4-5-20251001`, max_tokens=1000 per turn.
Conversation history passed in full on each turn (stateless API, stateful
session managed in `jade_nightly.py`).

### No streaming in Phase 1.5
Jade prints full response per turn. Streaming deferred to Phase 7 (TTS).

### Flat file logging
SQLite deferred to Phase 3. All output written to markdown flat files.
Migration path: Phase 3 ingests all flat files into SQLite on first run.

---

## 7. Edge Cases — Resolved

| Scenario | Behavior |
|----------|----------|
| Spencer skips the nightly entirely | `tomorrow_context.json` not written. Morning briefing detects stale/missing file, adds one line: "No check-in last night." No drama, no lecture. |
| Spencer closes Terminal mid-session | Partial log written with whatever was captured. `tomorrow_context.json` written with partial data if Phase C was reached, otherwise not written. |
| No calendar events today | Jade skips calendar-specific questions, falls back to ACTIVE_GOALS.md domains only |
| Session runs long (>15 min) | No hard cutoff. Jade does not artificially truncate. Spencer can type "wrap it up" to trigger Phase E early. |
| Spencer gives one-word answers | Jade probes once more, then moves on. Does not badger. Logs the thin response as-is. |
| ACT test date ≤7 days out | ACT domain always included regardless of calendar, and elevated to Phase A priority |

---

## 8. ISC — Integration Success Criteria

Phase 1.5 is complete when all of the following pass:

- [ ] **ISC-1:** `jade_nightly.py` launches from Terminal at scheduled time via launchd osascript method
- [ ] **ISC-2:** Jade opens with a specific, calendar-aware greeting (not generic)
- [ ] **ISC-3:** Domain check-ins reflect today's actual calendar events
- [ ] **ISC-4:** Phase C produces a `tomorrow_context.json` with valid schema
- [ ] **ISC-5:** `jade_briefing.py` reads `tomorrow_context.json` and includes stated intentions + priorities in morning output
- [ ] **ISC-6:** Morning briefing explicitly notes "No check-in last night" when `tomorrow_context.json` is missing or stale
- [ ] **ISC-7:** Nightly log written to `memory/logs/nightly/YYYY-MM-DD.md` with all 6 sections populated
- [ ] **ISC-8:** SOUL.md tone holds throughout — peer register, no fluff, no validation of avoidance
- [ ] **ISC-9:** Session completes in under 15 minutes on a normal day
- [ ] **ISC-10:** Tested on both a weekday trigger (9:15pm) and a weekend trigger (8:45pm)
- [ ] **ISC-11:** `python3 jade_nightly.py --now` triggers session immediately regardless of schedule
- [ ] **ISC-12:** If Spencer runs manually before scheduled time and `tomorrow_context.json` is written with today's date, launchd trigger at scheduled time is a no-op (skips gracefully with log entry)

---

## 9. Out of Scope (Phase 1.5)

- SQLite persistence (Phase 3) — migration from flat files is ~30 lines and low risk, but schema design requires real usage data. 2–3 weeks of flat file logs will tell us what queries we actually need. Migrating now means designing a schema blind.
- TTS / voice output (Phase 7)
- Mobile notifications (later phase)
- Adaptive question learning (Phase 3+ — requires memory)
- ROG/MSI routing (Phase 9)
- Raspberry Pi interface (Phase 10)

---

## 10. Files Touched

| File | Action |
|------|--------|
| `jade_nightly.py` | Create |
| `jade_prompts.py` | Update — add `build_nightly_system_prompt(context)` |
| `jade_briefing.py` | Update — read `tomorrow_context.json` if present |
| `launchd/com.jade.nightly.plist` | Create |
| `memory/logs/nightly/` | Create directory |
| `memory/cache/tomorrow_context.json` | Auto-created on first nightly run |
| `docs/CHANGELOG.md` | Update |
| `docs/PROJECT_STATUS.md` | Update |
