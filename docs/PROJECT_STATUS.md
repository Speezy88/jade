# PROJECT_STATUS.md
*Last updated: 2026-04-11*

---

## Current Phase: 2.6 — Notion Project Engine

Phases 1, 1.5, 2, and 2.5 are complete and operational.

---

## Phase Status

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | Morning briefing — live Calendar + Schoology + Weather, launchd, SOUL.md | ✅ Complete |
| 1.5 | Nightly check-in — `jade_nightly.py`, pure script (task closeout + tomorrow flag) | ✅ Complete |
| 2 | Calendar time-blocking — `/timeblock` command, gcal read+write | ✅ Complete |
| 2.5 | Notion Task Layer — Tasks DB, `jade_notion.py`, briefing + nightly wired | ✅ Complete |
| 2.6 | Notion Project Engine — Projects DB, `create_project()`, 10-sec block, nightly edits | **Current** |
| 2.7 | Research Pipeline — Perplexity → Claude synthesis → Research Vault | Planned |
| 2.8 | Skills Layer — Skills DB, Practice Log, Opportunities, research-powered roadmaps | Planned |
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

## What's Built (Phases 1 + 1.5 + 2 + 2.5)

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
- `jade_nightly.py` — pure script, no LLM. Part 1: yes/no task closeout → `update_task_status()`. Part 3: tomorrow list + addition prompt → `tomorrow_context.json` + nightly log. Post-run: offers timeblock.
- `launchd/com.jade.nightly.plist` — 9:15pm weekdays / 8:45pm weekends

**Phase 2:**
- `jade_timeblock.py` — free-window computation, Haiku schedule proposal, adjustment loop, GCal write, revise-with-delete, duration signal logging
- `integrations/gcal.py` — upgraded to `calendar.events` scope; `get_events_for_date()`, `create_event()`, `delete_jade_events_for_date()`
- `jade_prompts.py` — `build_timeblock_system_prompt()` + `_TIMEBLOCK_INSTRUCTIONS`
- `memory/logs/timeblock/` — per-run JSON logs
- `memory/logs/duration_signals.jsonl` — override signal capture (seeds Phase 5.5)

**Phase 2.5:**
- `jade_setup.py` — one-time Notion workspace setup; creates 6 DBs via Notion API; writes `memory/notion_ids.json`; `--check` validates relations; areas include "Manatee Aquatic"
- `integrations/jade_notion.py` — task queries (`get_todays_tasks`, `get_overdue_tasks`, `get_upcoming_tasks`) + writes (`create_task`, `update_task_status`, `create_recurring_task`); urllib only, never raises; property name: "Estimated Duration (min)"
- `jade_briefing.py` — injects `tasks_today` + `tasks_overdue`; Notion availability guard (credentials + notion_ids.json check → `None` if missing)
- `jade_prompts.py` — `_format_task_line()`, task sections in briefing formatter; `None` vs `[]` distinction for Notion availability
- `jade_ingest.py` — bulk Notion ingest; paste raw text → Haiku classifies → preview → `create_task()`; projects shown but skipped (Phase 2.6)
- Notion workspace: 6 databases live with correct schemas and relations

---

## Where to Start Next Session

**Phase 2.6: Notion Project Engine**

Spec: `docs/features/Jade_Phase_2.5-2.7_Spec.md` (Phase 2.6 section)

1. Add `create_project()`, `edit_project()`, `update_next_action()`, `get_active_projects()` to `integrations/jade_notion.py`
2. Wire project creation/editing into nightly check-in (Phase C discussion → update next action)
3. Active projects with deadline < 48hrs → flagged in morning briefing
4. ISC-7 through ISC-12 must all pass before moving to Phase 2.7

---

## Known Gaps

- Google Calendar school calendar (`spencerhatch@seattleacademy.org`) may not be
  accessible via Gmail OAuth — if events are missing, check calendar sharing settings
- `jade_router.py` not yet built — all routing is hardcoded to cloud (Haiku/Sonnet)
- No signal capture yet (Phase 3) — briefing quality ratings not being recorded
- `memory/WORK/` task tracking not in use yet — ISC.json workflow manual only
- `jade_timeblock.py` ISC-4/ISC-5 (ACT commitment auto-read from ACTIVE_GOALS.md, Haiku estimate basis) — not formally verified; works in practice via prompt injection
- Phase 2.5 ISC-1 through ISC-6 have correct code paths but live end-to-end verification requires tasks to exist in the Notion Tasks DB
- Notion API uses `ssl._create_unverified_context()` workaround — fix properly by running `/Applications/Python\ 3.13/Install\ Certificates.command`

---

## Infrastructure Notes

- **ROG RAM upgrade pending:** 32GB → enables deepseek-r1:32b pull
- **Local inference not yet integrated** — all calls go to Anthropic cloud
- **Cost ceiling:** ≤$15/month | Current usage: Phase 1 Haiku calls ~$0.30/month estimated
