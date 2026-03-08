# PROJECT_STATUS.md
*Last updated: 2026-03-08*

---

## Current Phase: 3 — Signal System

Phases 1, 1.5, and 2 are complete and operational.

---

## Phase Status

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | Morning briefing — live Calendar + Schoology + Weather, launchd, SOUL.md | ✅ Complete |
| 1.5 | Nightly check-in — `jade_nightly.py`, interactive 5-phase session | ✅ Complete |
| 2 | Calendar time-blocking — `/timeblock` command, gcal read+write | ✅ Complete |
| 3 | Signal system — ratings.jsonl, FAILURES/, structured memory | **Current** |
| 4 | Goal action plans + briefing check-ins | Planned |
| 5 | Nightly briefing — day vs plan, gap analysis, streaks | Planned |
| 5.5 | Task duration intelligence — Drive API + manual `/log` + time model | Planned |
| 6 | Meeting note taker — Whisper local + `/meeting` + execution plans | Planned |
| 7 | Activity monitor — app-level logging, Tier 1 summarizer | Planned |
| 8 | TTS — Kokoro local first, ElevenLabs fallback | Planned |
| 9 | ChromaDB + nomic-embed-text semantic memory | Planned |
| 10 | Multi-agent orchestration across both PCs | Future |
| 11 | Raspberry Pi physical interface | Future |

---

## What's Built (Phases 1 + 1.5 + 2)

**Phase 1 + chat tail:**
- `jade_briefing.py` — 7am briefing, live data + nightly context, Haiku, interactive chat loop (Jade-driven closure), `extract_morning_context()` → `morning_context.json`, notification post-chat
- `jade_prompts.py` — `build_system_prompt()` (with `_BRIEFING_TONE`) + `build_nightly_system_prompt()`, single source of prompt assembly
- `integrations/weather.py` — OpenWeatherMap, never raises
- `integrations/gcal.py` — Google Calendar OAuth2, two calendars, sorted
- `integrations/schoology.py` — ICS fetch, 6h cache, error fallback
- `launchd/com.jade.briefing.plist` — loaded and operational at 7am
- `launchd/com.jade.doc-check.plist` — loaded and operational at 10pm
- `scripts/check_doc_staleness.py` — nightly doc freshness enforcement
- Core config: SOUL.md, AI_STEERING_RULES.md, AGENTS.md, ACTIVE_GOALS.md

**Phase 1.5:**
- `jade_nightly.py` — interactive 5-phase nightly check-in (A→E), structured extraction, log + context write, post-Phase-E timeblock prompt
- `launchd/com.jade.nightly.plist` — 9:15pm weekdays / 8:45pm weekends

**Phase 2:**
- `jade_timeblock.py` — free-window computation, Haiku schedule proposal, adjustment loop, GCal write, revise-with-delete, duration signal logging
- `integrations/gcal.py` — upgraded to `calendar.events` scope; `get_events_for_date()`, `create_event()`, `delete_jade_events_for_date()`
- `jade_prompts.py` — `build_timeblock_system_prompt()` + `_TIMEBLOCK_INSTRUCTIONS`
- `memory/logs/timeblock/` — per-run JSON logs
- `memory/logs/duration_signals.jsonl` — override signal capture (seeds Phase 5.5)

---

## Where to Start Next Session

**Phase 3: Signal System**

1. Build `memory/LEARNING/SIGNALS/ratings.jsonl` capture — hook or manual entry
2. Build `memory/LEARNING/FAILURES/` — full context capture for ratings ≤3
3. Wire `rating_capture.py` hook (UserPromptSubmit) to auto-capture 1–10 ratings
4. Build `/retro` command to trigger end-of-session loop with ratings prompt

---

## Known Gaps

- Google Calendar school calendar (`spencerhatch@seattleacademy.org`) may not be
  accessible via Gmail OAuth — if events are missing, check calendar sharing settings
- `jade_router.py` not yet built — all routing is hardcoded to cloud (Haiku/Sonnet)
- No signal capture yet (Phase 3) — briefing quality ratings not being recorded
- `memory/WORK/` task tracking not in use yet — ISC.json workflow manual only
- `jade_timeblock.py` ISC-4/ISC-5 (ACT commitment auto-read from ACTIVE_GOALS.md, Haiku estimate basis) — not formally verified; works in practice via prompt injection

---

## Infrastructure Notes

- **ROG RAM upgrade pending:** 32GB → enables deepseek-r1:32b pull
- **Local inference not yet integrated** — all calls go to Anthropic cloud
- **Cost ceiling:** ≤$15/month | Current usage: Phase 1 Haiku calls ~$0.30/month estimated
