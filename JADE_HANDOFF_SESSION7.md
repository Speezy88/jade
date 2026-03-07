# JADE — Session 7 Handoff
*Date: 2026-03-07 | Branch: main | Phase: 1.5 — Nightly Check-In*

---

## SESSION SUMMARY

This session completed Phase 1.5 (Nightly Check-In) build and fixed the post-session
JSON extraction bug discovered during live testing. Phase 1 continuity was also closed:
`jade_briefing.py` now reads `tomorrow_context.json` from the previous night's session.

**Commits this session:**
```
8a663c7  feat(phase1.5): add nightly check-in — jade_nightly.py + extraction robustness
b0f79ff  docs: sync documentation after Phase 1.5 nightly check-in
```

---

## WHAT WAS BUILT

### jade_nightly.py (new)
Interactive 5-phase nightly check-in. Key design decisions:

- **Stateless API, stateful session:** Full `history: list[dict]` passed on every Haiku
  call. No streaming (deferred to Phase 7/TTS).
- **Phase control via hidden instructions:** Phase markers `[PHASE A]`, `[PHASE B - DOMAIN: x]`
  etc. are injected into the user content of each API call — not visible to Spencer, but
  give Haiku structure for what to do next.
- **Domain selection is calendar-aware** (`select_domains(events)`): ACT prep if ≤30 days
  to exam or no other domains; WTT/lacrosse/college app from calendar keywords. Max 3
  domains per session.
- **Dedup guard:** `already_ran_today()` checks `tomorrow_context.json` date. `--now` bypasses.
- **Partial write at Phase C:** `write_tomorrow_context()` called with partial data after
  Phase C to protect against interrupted sessions (ISC-4 partial coverage even on crash).

### jade_prompts.py (updated)
Added `build_nightly_system_prompt(context: dict)` and `_format_nightly_context(ctx: dict)`.
Context keys: `today`, `days_to_act`, `calendar_events`, `domains`, `recent_logs`.
Includes hardcoded `## Nightly Session Structure` instructions at the end of every nightly prompt.

### jade_briefing.py (updated)
Added `_load_nightly_context()`: reads `tomorrow_context.json`, returns nightly data if
dated today, returns `{"missed_nightly": True}` otherwise. Context spread into briefing
prompt via `**_load_nightly_context()`.

`_format_context()` in `jade_prompts.py` was extended for:
- `missed_nightly: True` → adds "Note: No check-in last night."
- `priorities` → "Stated priorities for today (from last night's check-in): ..."
- `stated_intentions` → "Spencer's stated intentions for today: ..."

### launchd/com.jade.nightly.plist (new)
Uses osascript to open Terminal.app with `jade_nightly.py`. launchd cannot spawn
interactive terminals directly — this is the only working pattern.
- Weekdays (Mon–Fri): 9:15 PM
- Weekends (Sat–Sun): 8:45 PM
**Status: file committed but `launchctl load` not yet run.**

---

## EXTRACTION BUG — STATUS: FIXED AND COMMITTED

### What happened
Post-session `extract_structured()` call failed with `json.JSONDecodeError`. Haiku returned
markdown-fenced JSON (` ```json ... ``` `) despite `_EXTRACTION_SYSTEM` explicitly
instructing "Return ONLY valid JSON. No prose. No code fences."

### Fix implemented (commit 8a663c7)
Three layers:

**1. Fence stripping in `extract_structured()`:**
```python
def extract_structured(client, history) -> tuple[dict, str]:
    # ... API call ...
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = "\n".join(
            l for l in raw.splitlines()
            if not l.strip().startswith("```")
        ).strip()
    return json.loads(raw), raw   # returns (dict, raw_str)
```

**2. Raw response logging on failure (in `run()` post-session block):**
```python
try:
    structured, raw_response = extract_structured(client, history)
    write_nightly_log(structured)
    write_tomorrow_context(structured)
except Exception as exc:
    print(f"[jade_nightly] WARNING: extraction failed ({exc})", file=sys.stderr)
    try:
        print(f"[jade_nightly] Raw extraction response: {raw_response!r}", file=sys.stderr)
    except NameError:
        pass  # API call failed before raw_response was assigned
    _write_transcript_fallback(history, today)
```

**3. Transcript fallback `_write_transcript_fallback(history, today)`:**
Writes conversation as `memory/logs/nightly/YYYY-MM-DD.md` with header
`(raw transcript — extraction failed)`. Filters out `[PHASE...]` control turns.
Preserves all Spencer responses and Jade outputs.

### Verification (all passed)
```
PASS: import
PASS: markdown fences stripped correctly
PASS: transcript fallback written correctly (phase turns filtered, content preserved)
```

---

## ISC STATUS — PHASE 1.5

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| ISC-1 | `jade_nightly.py` launches via launchd osascript at scheduled time | ❌ Not verified | Plist not loaded yet. Needs `launchctl load` + wait for next trigger time |
| ISC-2 | Jade opens with calendar-aware greeting | ✅ Verified | Background `--now` run confirmed calendar-specific greeting (referenced clear calendar) |
| ISC-3 | Domain check-ins reflect today's actual calendar | ❌ Not verified | Needs full live interactive test |
| ISC-4 | Phase C produces `tomorrow_context.json` with valid schema | ⚠️ Partial | Code complete; partial write at Phase C confirmed. Full schema unverified without live run |
| ISC-5 | Briefing reads `tomorrow_context.json`, includes priorities + intentions | ✅ Code verified | `_load_nightly_context()` reads and spreads data; `_format_context()` renders it |
| ISC-6 | Briefing notes "No check-in last night" when file missing/stale | ✅ Code verified | `missed_nightly` flag implemented in `_format_context()` |
| ISC-7 | Nightly log written with all 6 sections populated | ⚠️ Partial | `write_nightly_log()` complete; extraction hardened; no full live log yet |
| ISC-8 | SOUL.md tone holds — peer register, no fluff | ❌ Not verified | Needs live interactive test |
| ISC-9 | Session completes in <15 min | ❌ Not verified | Needs live interactive test |
| ISC-10 | Tested on weekday trigger + weekend trigger | ❌ Not verified | Plist not loaded |
| ISC-11 | `--now` triggers session immediately | ✅ Verified | Flag implemented and tested |
| ISC-12 | Launchd no-op if session already ran today | ✅ Code verified | `already_ran_today()` checks date in `tomorrow_context.json` |

**Summary: 5 verified, 2 partial, 5 pending live test**

---

## EXACT NEXT STEPS TO RESUME

### Step 1 — Load the plist and run a live interactive test
```bash
cp ~/Jade/launchd/com.jade.nightly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jade.nightly.plist
launchctl list | grep jade   # verify both jade jobs show up

# Run immediately in a REAL terminal (not Claude Code background — needs stdin):
python3 ~/Jade/jade_nightly.py --now
```
This live test will verify ISC-2, ISC-3, ISC-4 (full schema), ISC-7, ISC-8, ISC-9, ISC-11.

### Step 2 — Verify morning briefing picks up nightly context
After the live test completes and `tomorrow_context.json` is written:
```bash
python3 ~/Jade/jade_briefing.py
```
Check output includes "Stated priorities for today" and "Spencer's stated intentions."
This verifies ISC-5.

### Step 3 — Verify missed nightly note
Delete or rename `tomorrow_context.json`, then run briefing:
```bash
mv ~/Jade/memory/cache/tomorrow_context.json ~/Jade/memory/cache/tomorrow_context.json.bak
python3 ~/Jade/jade_briefing.py
# Should include: "Note: No check-in last night."
mv ~/Jade/memory/cache/tomorrow_context.json.bak ~/Jade/memory/cache/tomorrow_context.json
```
This verifies ISC-6.

### Step 4 — Phase 1.5 sign-off
Once ISC-1 through ISC-12 are all green, run `/arch-review` to formally close Phase 1.5,
then `/update-docs` to mark it final.

### Step 5 — Phase 2: `/timeblock`
1. Delete `~/.config/jade/token.json` (OAuth re-auth required for write scope)
2. Update `integrations/gcal.py` scope from `calendar.readonly` → `calendar.events`
3. Re-auth: `python3 -c "from integrations.gcal import get_today_events; get_today_events()"`
4. Build `jade_timeblock.py`
5. Wire `.claude/commands/timeblock.md`

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
├── JADE_HANDOFF_SESSION7.md           ← this file
│
├── jade_prompts.py                    ← ✅ build_system_prompt() + build_nightly_system_prompt()
├── jade_briefing.py                   ← ✅ 7am briefing + _load_nightly_context()
├── jade_nightly.py                    ← ✅ Phase 1.5 nightly check-in (all fixes applied)
├── jade_router.py                     ← 🔲 not yet built
├── jade_timeblock.py                  ← 🔲 not yet built
│
├── integrations/
│   ├── __init__.py
│   ├── weather.py                     ← ✅ OpenWeatherMap, never raises
│   ├── gcal.py                        ← ✅ OAuth2, 2 calendars, calendar.readonly scope
│   ├── schoology.py                   ← ✅ ICS feed, 6h cache, URL validated upfront
│   └── notifier.py                    ← 🔲 not yet built (using subprocess directly in briefing)
│
├── launchd/
│   ├── com.jade.briefing.plist        ← ✅ loaded, 7am daily
│   ├── com.jade.nightly.plist         ← ✅ committed, NOT YET LOADED
│   └── com.jade.doc-check.plist       ← ✅ loaded, 10pm daily
│
├── memory/
│   ├── ACTIVE_GOALS.md                ← goal state injected into all prompts
│   ├── cache/
│   │   ├── schoology.json             ← 6h Schoology cache (auto-managed)
│   │   └── tomorrow_context.json      ← nightly → briefing continuity (auto-managed)
│   ├── logs/
│   │   └── nightly/                   ← YYYY-MM-DD.md per session (auto-created)
│   └── LEARNING/
│       └── SIGNALS/
│           └── ratings.jsonl          ← 1 entry: 2026-03-06, rating 7, phase1_briefing
│
├── docs/
│   ├── ARCHITECTURE.md                ← ✅ updated this session
│   ├── CHANGELOG.md                   ← ✅ updated this session
│   ├── PROJECT_STATUS.md              ← ✅ updated this session
│   └── features/
│       ├── phase1-spec.md
│       ├── phase1.5-spec.md
│       ├── briefing.md
│       ├── gcal_integration.md
│       ├── schoology.md
│       ├── nightly.md                 ← ✅ created this session
│       └── TOOLS.md
│
├── .claude/
│   ├── commands/                      ← all slash commands present
│   └── hooks/                        ← hooks defined in AGENTS.md, not yet implemented as files
│
├── scripts/
│   ├── check_doc_staleness.py         ← ✅ operational via launchd
│   ├── assemble_claude.py             ← 🔲 not yet built
│   ├── smart_changelog.py             ← 🔲 not yet built
│   └── drift_detector.py              ← 🔲 not yet built
│
└── logs/
    ├── briefing.log
    ├── briefing_error.log
    ├── doc_check.log
    └── staleness.log
```

---

## DECISIONS AND PATTERNS ESTABLISHED THIS SESSION

### Extraction return signature
`extract_structured()` returns `tuple[dict, str]` — `(parsed dict, raw response)`.
The raw string is passed back to the caller specifically so the error handler can log it
without needing a try/except split around the API call itself. This pattern should be
followed for any future structured extraction calls.

### Phase control injection pattern
Jade's conversation phases are controlled by injecting `[PHASE X] ...` instructions into
the `user` content slot of each API turn, not into the system prompt. This keeps the
system prompt clean and makes the phase logic explicit and auditable in the history list.
Future multi-phase flows (Phase 5 gap analysis, etc.) should use the same pattern.

### Partial write on Phase C
`write_tomorrow_context()` is called with partial data at the end of Phase C, before
Phases D and E complete. This ensures ISC-4 holds even if Spencer closes the terminal
mid-session. The final full write at the end of `run()` overwrites this with complete data.

### Haiku JSON reliability
Haiku will wrap JSON in markdown fences despite explicit `Return ONLY valid JSON` instructions.
This is not intermittent — treat it as a guaranteed behavior and always strip fences before
parsing any structured Haiku response. Added to tacit knowledge; should be added to
AI_STEERING_RULES.md if observed again in Phase 2+ (promotion threshold: 3 occurrences).

### osascript is the only launchd → interactive terminal path
launchd cannot spawn an interactive terminal session. The `osascript` + Terminal.app method
is the only working approach on macOS. Any future feature that requires a terminal UI from
launchd must use this same pattern.

---

## KNOWN GAPS AT CLOSE

| Gap | Impact | Fix |
|-----|--------|-----|
| `com.jade.nightly.plist` not loaded | Nightly won't auto-trigger | `launchctl load` per next steps |
| No live interactive test complete | ISC-2,3,4,7,8,9 unverified | Run `--now` in real terminal |
| `hooks/` files don't exist as Python files | Hooks defined in AGENTS.md but not executable | Future phase |
| gcal OAuth is `calendar.readonly` | Phase 2 time-blocking requires write scope | Phase 2 re-auth |
| No signal capture yet | Ratings.jsonl has 1 manual entry only | Phase 3 |

---

## OPEN QUESTION

Phase D in the spec is conditional — "only runs if Jade detected an unresolved item."
The current implementation always runs Phase D (asks open loops question unconditionally).
This is a pragmatic simplification: Haiku can't reliably detect "unresolved items" in
prior turns without additional prompt engineering. The simpler "always ask Phase D briefly"
is better than a complex detection system. Spec should be updated to match implementation
if it proves fine in live testing.

---

*Handoff generated: 2026-03-07 | Session mode: FULL | Rating: pending*
