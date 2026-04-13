# PROJECT_STATUS.md
*Last updated: 2026-04-12*

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
- `integrations/jade_notion.py` — task queries (`get_todays_tasks`, `get_overdue_tasks`, `get_upcoming_tasks`) + writes (`create_task`, `update_task_status`, `create_recurring_task`); urllib only, never raises
- `jade_briefing.py` — injects `tasks_today` + `tasks_overdue`; Notion availability guard
- `jade_prompts.py` — `_format_task_line()`, task sections in briefing formatter; `None` vs `[]` distinction
- `jade_ingest.py` — bulk Notion ingest v1 (tasks/projects only)
- Notion workspace: 6 databases live with correct schemas and relations

**Phase 2.6 (in progress — ISC partially verified):**
- `integrations/jade_notion.py` — added project functions: `create_project()`, `edit_project()`, `update_next_action()`, `get_active_projects()`; added ingest v2 functions: `append_page_content()`, `create_research_job()`, `create_practice_entry()`
- `jade_nightly.py` — Part 2 implemented: project review loop after task closeout → `update_next_action()`
- `jade_briefing.py` — `projects_urgent` deadline ≤ 48hrs flag added
- `jade_prompts.py` — `projects_urgent` rendering in `_format_context()`
- `jade_ingest.py` — full rewrite to v2: 5 destination types (task/project/research/practice/note), natural-language date resolution, project linking, `confirm_and_edit()` loop

---

## Where to Start Next Session

**Fix ISC-I9, then complete ISC verification for Phase 2.6**

1. **Debug ISC-I9** — note → project page body not writing. Check: (a) `print(project_map)` before `_write_note()` to confirm project name present; (b) does `append_page_content()` return True? (c) stderr for Notion API error. Root cause: likely project is not `🔄 Active` status (only Active projects are in `project_map`) or blocks PATCH failure.

2. **Run remaining ISC** — ISC-8 through ISC-12 (Phase 2.6) and ISC-I10 through ISC-I17 (ingest v2) not yet tested. Run each manually per the verification table in `docs/features/Jade_Phase_2.5-2.7_Spec.md`.

3. **Commit jade_ingest.py** — it is untracked (never committed). `git add jade_ingest.py && git commit`.

4. **Phase 2.7** — once Phase 2.6 ISC passes: Research Pipeline. `jade_research.py`, Research Vault DB writes from Jade (currently only ingest queues them). Spec: `docs/features/Jade_Phase_2.5-2.7_Spec.md` (Phase 2.7 section).

---

## Known Gaps

- **ISC-I9 open bug** — jade_ingest.py `_write_note()` not writing to project page body; falls back to task prompt instead. Debug next session.
- **ISC-8 through ISC-12, ISC-I10 through I17** — not yet tested. Phase 2.6 not formally closed.
- **jade_ingest.py untracked** — new file never committed to git. `git add jade_ingest.py` needed.
- **Practice Log "Skill" relation** — `create_practice_entry()` omits the Skill relation field (requires skill name→page_id lookup). Phase 2.8 fix.
- Google Calendar school calendar (`spencerhatch@seattleacademy.org`) may not be accessible via Gmail OAuth — if events are missing, check calendar sharing settings
- `jade_router.py` not yet built — all routing is hardcoded to cloud (Haiku/Sonnet)
- No signal capture yet (Phase 3) — briefing quality ratings not being recorded
- `jade_timeblock.py` ISC-4/ISC-5 — not formally verified; works in practice via prompt injection
- Notion API uses `ssl._create_unverified_context()` workaround — fix properly by running `/Applications/Python\ 3.13/Install\ Certificates.command`

---

## Infrastructure Notes

- **ROG RAM upgrade pending:** 32GB → enables deepseek-r1:32b pull
- **Local inference not yet integrated** — all calls go to Anthropic cloud
- **Cost ceiling:** ≤$15/month | Current usage: Phase 1 Haiku calls ~$0.30/month estimated
