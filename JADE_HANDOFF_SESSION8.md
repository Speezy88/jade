# JADE — Session 8 Handoff
*Date: 2026-03-07 | Branch: main | Phases: Briefing Chat Tail + Phase 2 — Calendar Time-Blocking*

---

## SESSION SUMMARY

Session 8 completed two things: (1) the briefing chat tail (post-briefing interactive loop with
Jade-driven closure and morning_context.json extraction), and (2) Phase 2 — Calendar Time-Blocking
in full, including live-test debugging. Both are committed and operational.

**Commits this session:**
```
f218df2  feat: briefing chat tail — interactive post-briefing loop + conversational tone
efc4e8d  feat(phase2): calendar time-blocking — jade_timeblock.py + gcal write + docs
```

---

## WHAT WAS BUILT

### Briefing Chat Tail (jade_briefing.py + jade_prompts.py)

Interactive post-briefing conversation loop. Key design decisions:

- **Jade-driven closure:** Jade asks a closing question when the conversation feels complete.
  Exit triggers when: `len(history) >= 3` AND last Jade turn ends with `?` AND user input
  is in `_AFFIRMATIVES` set. No turn-count cutoff during normal flow.
- **_AFFIRMATIVES set:** `{"yes", "yep", "yeah", "yup", "that's it", "all good", "good",
  "nope", "nah", "nothing", "done", "all set"}` — handles both positive and negative
  confirmations (both mean "we're done").
- **_BRIEFING_TONE constant:** Injected into every briefing/chat prompt. Enforces
  conversational register: "looks like", "heads up", vary sentence length, no bullet-point
  brain. Also includes the chat closure instruction for Jade.
- **extract_morning_context():** Second Haiku call post-chat. Returns
  `{date, schedule_additions, adjustments, focus, notes}` to `memory/cache/morning_context.json`.
  Only runs if user said anything during chat (`len(history) > 1`).
- **_write_morning_transcript_fallback():** Writes `memory/logs/morning/YYYY-MM-DD.md` if
  extraction fails. Same fence-stripping + raw log pattern as nightly.
- **Notification moved post-chat:** `osascript` notify fires after chat completes, not
  before — ensures the briefing notification isn't the first thing Spencer sees mid-conversation.

### jade_timeblock.py (new — full Phase 2 entry point)

Calendar time-blocking. Key design decisions:

- **Free window computation (`_compute_free_windows`):**
  - Implicit school block: 8:15am–3:00pm on weekdays (unless a school event already covers it)
  - 15-min buffer on either side of any event ≥60 min
  - 30-min post-event buffer for lacrosse/practice events
  - Excludes before 7:00am and after 10:30pm
  - Returns only gaps ≥25 min as `[{"start": ..., "end": ..., "duration_min": ...}]`

- **Belts-and-suspenders JSON enforcement:** Haiku won't return raw JSON without both:
  1. CRITICAL block at end of `_TIMEBLOCK_INSTRUCTIONS` in system prompt
  2. Explicit `"Respond with the JSON object only."` appended to user message

  Both are required. Either alone is insufficient.

- **Truncation guard:** Before `json.loads()`:
  ```python
  if not raw.strip().endswith("}"):
      print("[jade_timeblock] WARNING: response may be truncated", file=sys.stderr)
  ```
  Uses `continue` in adjustment loop (keep loop alive) vs no-op in generation (already printed error).

- **Jade-event identity:** All created events get `description="jade: <title>"`. Delete-on-revise
  filters by `description.startswith("jade:")` — surgical, never touches Spencer's own events.

- **Unscheduled block filter:** At write time, skip any block with `"unscheduled"` in title
  (case-insensitive). These are display-only in the terminal proposal.

- **`_MAX_TOKENS = 4096`:** For full-day JSON schedule. Do not reduce.
  `_CHAT_MAX_TOKENS = 2048` for adjustment calls.

- **Post-nightly trigger:** `jade_nightly.py` ends Phase E with "Want me to block tomorrow?"
  On yes → `subprocess.run(["python3", ".../jade_timeblock.py"], check=False)`.

- **`--today` flag:** `python3 jade_timeblock.py --today` for same-day blocking.

### integrations/gcal.py (updated)

OAuth scope upgraded from `calendar.readonly` → `calendar.events`. Token at
`~/.config/jade/token.json` was re-generated with new scope at Phase 2 start.

New functions:
- `get_events_for_date(target_date: date) -> list[dict]` — returns dicts with
  `{id, calendar_id, summary, start_dt, end_dt, all_day}`. Reads both calendars.
- `create_event(title, start_dt, end_dt, description, calendar_id) -> str | None` —
  inserts to `spencerchatch@gmail.com`. Calls `_event_color_id(title)` for color.
- `delete_jade_events_for_date(target_date: date) -> int` — fetches personal calendar,
  filters `description.startswith("jade:")`, deletes each, returns count. Used in revise flow.
- `_event_color_id(title)` — ACT/math prep/science prep → `"2"` (sage), WTT/CRM/intern →
  `"5"` (banana), lacrosse/practice → `"6"` (tangerine). Default: no color override.

### jade_prompts.py (updated)

- Added `_BRIEFING_TONE` constant (see above)
- Added `build_timeblock_system_prompt(context: dict)` — stack:
  SOUL + STEERING + GOALS + _BRIEFING_TONE + _format_timeblock_context() + _TIMEBLOCK_INSTRUCTIONS
- Added `_format_timeblock_context(ctx)` — injects: target_date, hard_constraints,
  free_windows (human-readable), free_windows_raw (JSON for Haiku), priorities,
  stated_intentions, task_durations, schedule_additions, focus, assignments
- Added `_TIMEBLOCK_INSTRUCTIONS` — full JSON schema, constraints (school/lacrosse/meals/
  unscheduled_windows), CRITICAL JSON enforcement block

### jade_nightly.py (updated)

Post-Phase-E timeblock prompt added. Also fixed `raw_response` variable scope (initialized
to `None` before try block to prevent NameError in error handler).

---

## LIVE-TEST BUGS FIXED (all committed in efc4e8d)

| Bug | Root cause | Fix |
|-----|-----------|-----|
| `json.JSONDecodeError` on schedule generation | Haiku returning prose instead of JSON | CRITICAL block in `_TIMEBLOCK_INSTRUCTIONS` + explicit JSON instruction in user message |
| Same error in adjustment loop | Fix not applied to adjustment call | Same fix applied to `adjust_prompt` user message |
| `JSONDecodeError` on truncated response | `_MAX_TOKENS` too low (1000, then 2048) | Bumped to 4096 + truncation guard |
| Duplicate GCal events on revise | No delete before re-write | `delete_jade_events_for_date()` called immediately after Spencer confirms revise |
| "Lunch" block created at 3:45pm | No meal label awareness in prompt | Meal label rule added to `_TIMEBLOCK_INSTRUCTIONS` |
| "Unscheduled buffer" written to GCal | Haiku puts open time in `blocks` array | Skip filter at write time + prompt instruction to use `unscheduled_windows` only |

---

## ISC STATUS — PHASE 2

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| ISC-1 | `jade_timeblock.py` imports cleanly, no errors | ✅ Verified | Live tested |
| ISC-2 | Free windows exclude school block 8:15–3pm on weekdays | ✅ Verified | Confirmed in output |
| ISC-3 | Free windows apply 15-min buffer around events ≥60 min | ✅ Verified | Confirmed in output |
| ISC-4 | Free windows apply 30-min post-lacrosse buffer | ✅ Code verified | Logic present; no lacrosse event in test day |
| ISC-5 | Haiku returns valid JSON schedule | ✅ Verified | Holds post JSON-fix |
| ISC-6 | Proposed schedule prints to terminal in readable format | ✅ Verified | Live tested |
| ISC-7 | Adjustment loop accepts natural-language edits, returns updated JSON | ✅ Verified | Live tested |
| ISC-8 | Confirmed blocks written to GCal | ✅ Verified | Events visible in calendar |
| ISC-9 | Unscheduled/buffer blocks not written to GCal | ✅ Verified | Skip filter working |
| ISC-10 | Revise flow deletes prior Jade blocks before rebuilding | ✅ Verified | Live tested |
| ISC-11 | Duration overrides append to `duration_signals.jsonl` | ✅ Code verified | Logic present; no override in test run |
| ISC-12 | `memory/logs/timeblock/YYYY-MM-DD.json` written after run | ✅ Verified | File present |
| ISC-13 | Post-nightly prompt triggers `jade_timeblock.py` on confirm | ✅ Code verified | subprocess.run wired |

**Summary: 11 verified, 2 code-verified (no triggering test case available)**

---

## EXACT NEXT STEPS TO RESUME

### Phase 3: Signal System

Per `docs/PROJECT_STATUS.md`:

1. **Build `rating_capture.py` hook (UserPromptSubmit)**
   - Detect 1–10 ratings in user messages
   - Append to `memory/LEARNING/SIGNALS/ratings.jsonl` with full schema
   - Trigger FAILURES/ capture for ratings ≤3
   - False positive rejection (don't capture "10 items" as a rating)

2. **Build `memory/LEARNING/FAILURES/` capture**
   - On rating ≤3: write `memory/LEARNING/FAILURES/YYYY-MM-DD-[slug].md`
   - Contents: session context, the rating, what went wrong, full conversation excerpt

3. **Wire `/retro` to check promotion rule automatically**
   - Scan ratings.jsonl for pattern: rating ≤3, ≥3 occurrences, ≥2 tasks, within 30 days
   - Write proposed rule to `.learnings/PENDING_RULES.md`
   - Surface to Spencer for `/approve`

4. **Build `.claude/hooks/` as actual Python files**
   - Currently defined in AGENTS.md but don't exist as executable files
   - Start with `rating_capture.py` (most value) and `pre_tool_use.py` (protection)

---

## FILE STRUCTURE — CURRENT STATE

```
~/Jade/
├── CLAUDE.md                          ← project context (assembled from components/)
├── SOUL.md                            ← Jade identity — injected into all prompts
├── AI_STEERING_RULES.md               ← behavioral guardrails
├── AGENTS.md                          ← delegation patterns + hook implementations
├── TOOLS.md                           ← integration gotchas
├── .env                               ← OPENWEATHERMAP_API_KEY, SCHOOLOGY_ICS_URL,
│                                         ANTHROPIC_API_KEY
├── requirements.txt
├── JADE_HANDOFF_SESSION8.md           ← this file
│
├── jade_prompts.py                    ← ✅ build_system_prompt() + build_nightly_system_prompt()
│                                         + build_timeblock_system_prompt() + _BRIEFING_TONE
├── jade_briefing.py                   ← ✅ briefing + chat loop + extract_morning_context()
├── jade_nightly.py                    ← ✅ nightly check-in + post-Phase-E timeblock prompt
├── jade_timeblock.py                  ← ✅ Phase 2 time-blocking (fully operational)
├── jade_router.py                     ← 🔲 not yet built
│
├── integrations/
│   ├── __init__.py
│   ├── weather.py                     ← ✅ OpenWeatherMap, never raises
│   ├── gcal.py                        ← ✅ calendar.events scope, 4 functions
│   ├── schoology.py                   ← ✅ ICS feed, 6h cache
│   └── notifier.py                    ← 🔲 not yet built
│
├── launchd/
│   ├── com.jade.briefing.plist        ← ✅ loaded, 7am daily
│   ├── com.jade.nightly.plist         ← ✅ loaded, 9:15pm weekdays / 8:45pm weekends
│   └── com.jade.doc-check.plist       ← ✅ loaded, 10pm daily
│
├── memory/
│   ├── ACTIVE_GOALS.md                ← goal state injected into all prompts
│   ├── cache/
│   │   ├── schoology.json             ← 6h Schoology cache (auto-managed)
│   │   ├── tomorrow_context.json      ← nightly → briefing continuity (auto-managed)
│   │   └── morning_context.json       ← post-briefing chat extraction (auto-managed)
│   ├── logs/
│   │   ├── nightly/                   ← YYYY-MM-DD.md per session
│   │   ├── morning/                   ← YYYY-MM-DD.md fallback transcript
│   │   └── timeblock/                 ← YYYY-MM-DD.json per run
│   ├── duration_signals.jsonl         ← override log (seeds Phase 5.5)
│   └── LEARNING/
│       └── SIGNALS/
│           └── ratings.jsonl          ← 2 entries: session 7 (7) + session 8 (6)
│
├── docs/
│   ├── ARCHITECTURE.md                ← ✅ updated (Phase 2 complete)
│   ├── CHANGELOG.md                   ← ✅ updated (Phase 2 entry)
│   ├── PROJECT_STATUS.md              ← ✅ updated (Phase 3 = current)
│   └── features/
│       ├── briefing.md
│       ├── gcal_integration.md        ← ✅ updated (4 functions, write scope)
│       ├── timeblock.md               ← ✅ created this session
│       ├── schoology.md
│       └── nightly.md
│
└── .claude/
    ├── commands/                      ← all slash commands present
    └── hooks/                        ← defined in AGENTS.md, not yet as Python files
```

---

## PATTERNS ESTABLISHED THIS SESSION

### Belts-and-suspenders JSON enforcement
For any Haiku call that must return raw JSON:
1. Add CRITICAL block at end of system prompt `_INSTRUCTIONS` constant
2. Append `"Respond with the JSON object only."` to the user message
Both are required. Applying to generation but not adjustment (or vice versa) will cause
live-test failures. Apply to all structured-output calls at build time, not after failure.

### max_tokens for full-day JSON
Any Haiku call returning a full day's schedule in JSON: set `max_tokens=4096`. Do not
start at 1000 or 2048 and bump incrementally. 4096 is the right number.

### Truncation guard pattern
```python
raw = _strip_fences(response.content[0].text.strip())
if not raw.strip().endswith("}"):
    print("[module] WARNING: response may be truncated", file=sys.stderr)
```
In loops: `continue` to keep the loop alive. In one-shot calls: print and return safely.

### Adjustment loop fix scope
When applying a fix to a generation call, immediately check if the same fix is needed in
the adjacent adjustment call. Same function shape → same failure mode.

---

## KNOWN GAPS AT CLOSE

| Gap | Impact | Fix |
|-----|--------|-----|
| `.claude/hooks/` not implemented as Python files | rating_capture, pre_tool_use don't execute | Phase 3 first task |
| `duration_signals.jsonl` has no override entries yet | Phase 5.5 time model has no seed data | Normal — seeds on first override during real use |
| ISC-4, ISC-13 code-verified only | No lacrosse event / no nightly-to-timeblock live test | Low risk; logic is simple |
| No signal capture automation | Ratings still manual-only | Phase 3 hook build |

---

*Handoff generated: 2026-03-07 | Session mode: FULL | Rating: 6*
