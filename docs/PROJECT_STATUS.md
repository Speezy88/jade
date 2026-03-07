# PROJECT_STATUS.md
*Last updated: 2026-03-07*

---

## Current Phase: 2 — Calendar Time-Blocking

Phases 1 and 1.5 are complete and operational.

---

## Phase Status

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | Morning briefing — live Calendar + Schoology + Weather, launchd, SOUL.md | ✅ Complete |
| 1.5 | Nightly check-in — `jade_nightly.py`, interactive 5-phase session | ✅ Complete |
| 2 | Calendar time-blocking — `/timeblock` command, gcal read+write | **Current** |
| 3 | Signal system — ratings.jsonl, FAILURES/, structured memory | Planned |
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

## What's Built (Phases 1 + 1.5)

**Phase 1:**
- `jade_briefing.py` — 7am briefing, live data + nightly context, Haiku, macOS notification
- `jade_prompts.py` — `build_system_prompt()` + `build_nightly_system_prompt()`, single source of prompt assembly
- `integrations/weather.py` — OpenWeatherMap, never raises
- `integrations/gcal.py` — Google Calendar OAuth2, two calendars, sorted
- `integrations/schoology.py` — ICS fetch, 6h cache, error fallback
- `launchd/com.jade.briefing.plist` — loaded and operational at 7am
- `launchd/com.jade.doc-check.plist` — loaded and operational at 10pm
- `scripts/check_doc_staleness.py` — nightly doc freshness enforcement
- Core config: SOUL.md, AI_STEERING_RULES.md, AGENTS.md, ACTIVE_GOALS.md

**Phase 1.5:**
- `jade_nightly.py` — interactive 5-phase nightly check-in (A→E), structured extraction, log + context write
- `launchd/com.jade.nightly.plist` — 9:15pm weekdays / 8:45pm weekends (pending `launchctl load`)

---

## Where to Start Next Session

**Immediate (before Phase 2):**

Load the nightly plist and do a live interactive test:
```bash
cp ~/Jade/launchd/com.jade.nightly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jade.nightly.plist
python3 ~/Jade/jade_nightly.py --now   # run in a real terminal, not background
```

**Phase 2: `/timeblock` command**

1. Add Google Calendar write scope (`calendar.events`) to gcal OAuth — re-auth required
2. Build `jade_timeblock.py` — reads calendar, generates time-blocked schedule
3. Wire `/timeblock` slash command in `.claude/commands/timeblock.md`
4. Test: propose blocks, write to calendar, verify in Google Calendar

**Hard constraint:** gcal OAuth currently has `calendar.readonly` scope.
Phase 2 requires `calendar.events` (read+write). Will need to delete
`~/.config/jade/token.json` and re-auth with expanded scope.

---

## Known Gaps

- Google Calendar school calendar (`spencerhatch@seattleacademy.org`) may not be
  accessible via Gmail OAuth — if events are missing, check calendar sharing settings
- `jade_router.py` not yet built — all routing is hardcoded to cloud (Haiku/Sonnet)
- No signal capture yet (Phase 3) — briefing quality ratings not being recorded
- `memory/WORK/` task tracking not in use yet — ISC.json workflow manual only

---

## Infrastructure Notes

- **ROG RAM upgrade pending:** 32GB → enables deepseek-r1:32b pull
- **Local inference not yet integrated** — all calls go to Anthropic cloud
- **Cost ceiling:** ≤$15/month | Current usage: Phase 1 Haiku calls ~$0.30/month estimated
