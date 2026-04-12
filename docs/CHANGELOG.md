# CHANGELOG.md
*Append-only. Most recent entry at top.*

---

## 2026-04-11 — Nightly redesign + Notion data source priority + jade_ingest.py

**Nightly redesign (`jade_nightly.py`):** Rewrote from a 12-minute, 5-phase conversational debrief (Haiku, multi-turn) into a 2–3 minute pure script with no LLM calls. Part 1: iterates over `get_todays_tasks()`, asks yes/no per incomplete task, calls `update_task_status()` immediately. Part 3: lists tomorrow's tasks, one free-text addition, writes `tomorrow_context.json` (soft context only) and a structured nightly log. Part 2 (Project Next Action) deferred to Phase 2.6. `build_nightly_system_prompt()` in `jade_prompts.py` reduced to a Phase 2.6 stub. SOUL.md gained a NIGHTLY CHECK-IN SPECIFICATION section documenting the new behavior.

**Notion data source priority enforcement:** `jade_briefing.py` now guards Notion calls behind a credentials + `notion_ids.json` existence check — returns `None` (not `[]`) when unavailable so `jade_prompts.py` can surface an explicit "Notion unavailable" error instead of silently showing "no tasks." `_format_context()` in `jade_prompts.py` updated to distinguish `None` (unavailable) from `[]` (healthy, zero results). Data source contract documented in `build_system_prompt()` docstring and AI_STEERING_RULES.md.

**`jade_ingest.py` (new):** Standalone bulk ingest. Spencer pastes raw text; Haiku (single-turn) classifies into tasks/projects with exact Notion area/priority strings; preview shown; on confirm, `create_task()` called per task. Projects shown in preview but skipped until Phase 2.6. `jade_setup.py` updated to include "Manatee Aquatic" in `_AREA_OPTIONS`.

**`jade_notion.py`:** Renamed `"Estimated Duration"` property to `"Estimated Duration (min)"` across all three call sites (read at line 144, write in `create_task()`, write in `create_recurring_task()`).

Files changed:
- `jade_nightly.py` — complete rewrite (pure script, ~140 lines vs 364)
- `jade_prompts.py` — `_format_nightly_context()` reduced to Phase 2.6 stub; `build_system_prompt()` data source contract; `_format_context()` None/[] distinction
- `jade_briefing.py` — Notion availability guard (credentials + notion_ids.json check)
- `jade_ingest.py` — added (bulk ingest, standalone)
- `jade_setup.py` — added "Manatee Aquatic" to `_AREA_OPTIONS`
- `integrations/jade_notion.py` — "Estimated Duration" → "Estimated Duration (min)"
- `SOUL.md` — NIGHTLY CHECK-IN SPECIFICATION added; briefing spec updated with data sources
- `AI_STEERING_RULES.md` — Notion data source rule added
- `docs/ARCHITECTURE.md` — nightly diagram, File Responsibilities (jade_nightly.py updated, jade_ingest.py added), Prompt Assembly stub, Integration Contract field name

---

## 2026-04-10 — Phase 2.5 complete: Notion Task Layer + nightly exit fix

**Notion workspace setup (`jade_setup.py`):** One-time script that creates all 6 Notion
databases (Tasks, Projects, Research Vault, Skills, Practice Log, Opportunities) via Notion
API with correct schemas and cross-DB relations in dependency order. Writes all DB IDs to
`memory/notion_ids.json`. `--check` mode validates each DB is accessible and every relation
property points to the correct target DB ID (catches stale IDs after `--force` re-runs).
Uses urllib exclusively — `requests` was found to return 401 on valid Notion API calls on
this machine; `ssl._create_unverified_context()` works around macOS Python.org SSL cert issue.

**Notion task layer (`integrations/jade_notion.py`):** `get_todays_tasks()`,
`get_upcoming_tasks(n)`, `get_overdue_tasks()` query the Tasks DB and return sorted task
dicts (priority → due time). `create_task()`, `update_task_status()`, and
`create_recurring_task()` handle writes. Recurrence: `ceil(total_target / chunk_size)` daily
child instances, `end = start + n − 1` days. Credentials from `~/.config/jade/credentials`,
DB IDs from `memory/notion_ids.json`. All functions catch exceptions and return safe defaults.

**Briefing + nightly wired:** `jade_briefing.py` now fetches `tasks_today` and
`tasks_overdue` at 7am; both are injected into the system prompt via `jade_prompts.py`'s
updated `_format_context()`. `jade_nightly.py` injects the same data so Jade references
tasks by name during check-in. `jade_prompts.py` gained `_format_task_line()` and the
`_NIGHTLY_CLOSE_PROTOCOL` sentinel system for clean session exits.

**Nightly exit hardening:** `jade_nightly.py` gained a `[SESSION_COMPLETE]` sentinel
protocol — Jade appends it after Phase E and on detecting close signals; the loop strips
it before display and calls `sys.exit(0)`. 10-minute inactivity timeout via
`signal.SIGALRM`. Post-Phase-E ack turn added. `sys.exit(0)` at run end.

Files changed:
- `jade_setup.py` — added (one-time Notion workspace setup)
- `integrations/jade_notion.py` — added (task queries + writes)
- `jade_briefing.py` — added jade_notion import, tasks_today + tasks_overdue to context
- `jade_nightly.py` — added jade_notion wiring; sentinel exit protocol; signal timeout
- `jade_prompts.py` — `_format_task_line()`, tasks in `_format_context()` + `_format_nightly_context()`, `_NIGHTLY_CLOSE_PROTOCOL`
- `memory/notion_ids.json` — added (written by jade_setup.py)
- `docs/ARCHITECTURE.md` — Notion data flow, new file entries, prompt assembly, credentials

---

## 2026-03-08 — Phase 2 complete: Calendar Time-Blocking

`jade_timeblock.py` is operational. Fetches GCal events, computes free windows (with
school/lacrosse buffers and 15-min padding on long events), calls Haiku to generate a
JSON schedule proposal, presents it in the terminal with an adjustment loop (max 3 rounds,
natural-language edits via Haiku), then writes confirmed blocks to Google Calendar via
`create_event()`. On revise, `delete_jade_events_for_date()` removes prior Jade blocks
before rebuilding. Duration overrides append to `duration_signals.jsonl` to seed Phase 5.5.
Unscheduled/buffer blocks are filtered at write time (display-only). `jade_nightly.py`
updated with a post-Phase-E "Want me to block tomorrow?" prompt. `integrations/gcal.py`
upgraded from `calendar.readonly` to `calendar.events` scope with three new functions.
`jade_prompts.py` extended with `build_timeblock_system_prompt()`.

Files changed:
- `jade_timeblock.py` — added (Phase 2 entry point)
- `integrations/gcal.py` — scope upgrade + `get_events_for_date()`, `create_event()`, `delete_jade_events_for_date()`
- `jade_prompts.py` — added `build_timeblock_system_prompt()`, `_format_timeblock_context()`, `_TIMEBLOCK_INSTRUCTIONS`
- `jade_nightly.py` — added post-Phase-E timeblock prompt

---

## 2026-03-07 — Briefing chat tail + conversational tone

Added an interactive chat loop to `jade_briefing.py` that runs after the morning briefing
prints. Jade drives toward closure (asks a closing question when the conversation feels
complete); exit triggers when the previous Jade turn ended with `?` and Spencer confirms
with any affirmative. Post-chat, `extract_morning_context()` writes structured data to
`memory/cache/morning_context.json` (schema: `{date, schedule_additions, adjustments,
focus, notes}`), with a transcript fallback to `memory/logs/morning/` on failure.
`jade_prompts.py` updated with `_BRIEFING_TONE` injected into every briefing/chat prompt
to enforce conversational register ("looks like", "heads up", vary sentence length — no
bullet-point brain). `ARCHITECTURE.md` updated to reflect new data flows.

Files changed:
- `jade_briefing.py` — chat loop, `extract_morning_context()`, `_write_morning_transcript_fallback()`, morning_context.json write, notify moved post-chat
- `jade_prompts.py` — `_BRIEFING_TONE` constant + injected into `build_system_prompt()`
- `docs/ARCHITECTURE.md` — diagram, File Responsibilities, Prompt Assembly, Logs sections updated

---

## 2026-03-07 — Phase 1.5 complete: Nightly Check-In

`jade_nightly.py` is operational — an interactive 5-phase terminal session (A: day debrief,
B: domain check-ins, C: tomorrow planning, D: open loops, E: close) driven by Haiku with a
multi-turn conversation. Post-session, a second structured Haiku call extracts a JSON log
written to `memory/logs/nightly/` and `tomorrow_context.json`, which the next morning's
briefing reads to give Jade continuity across days. Extraction is hardened against Haiku's
tendency to wrap JSON in markdown fences: fences are stripped before parsing, the raw
response is logged on failure, and the full conversation is written as a markdown fallback
if parsing fails entirely. `jade_briefing.py` updated to load nightly context; launchd plist
added for weekday 9:15pm / weekend 8:45pm scheduling via osascript.

Files changed:
- `jade_nightly.py` — added (Phase 1.5 entry point)
- `jade_prompts.py` — added `build_nightly_system_prompt()`, `_format_nightly_context()`
- `jade_briefing.py` — added `_load_nightly_context()`, context spread
- `launchd/com.jade.nightly.plist` — added

---

## 2026-03-06 — Phase 1 complete: Morning Briefing

Phase 1 is fully operational. `jade_briefing.py` runs manually and via launchd at 7am.
Live data from Google Calendar, Schoology, and OpenWeatherMap is injected into the
system prompt alongside SOUL.md and ACTIVE_GOALS.md before being passed to Haiku.
MacOS notification fires with the first two lines of the briefing on each run.

Files added:
- `jade_briefing.py` — entry point, wire-up, launchd target
- `jade_prompts.py` — `build_system_prompt()`, single source of prompt assembly
- `integrations/weather.py` — OpenWeatherMap free tier
- `integrations/gcal.py` — Google Calendar OAuth2, multi-calendar
- `integrations/schoology.py` — ICS fetch with 6h cache
- `launchd/com.jade.briefing.plist` — 7am launchd job
- `docs/ARCHITECTURE.md` — initial architecture documentation
- `docs/PROJECT_STATUS.md` — project status tracking

---

## 2026-03-05 — Phase 1 spec and core config

Phase 1 spec written and approved. Core config files (SOUL.md, AGENTS.md,
AI_STEERING_RULES.md, ACTIVE_GOALS.md, CLAUDE.md) established. Doc staleness
check script and launchd plist operational at 10pm nightly.

Files added:
- `SOUL.md` — Jade behavioral identity
- `AI_STEERING_RULES.md` — behavioral guardrails
- `AGENTS.md` — delegation patterns and hook implementations
- `CLAUDE.md` — assembled project context
- `memory/ACTIVE_GOALS.md` — Spencer's live goal state
- `docs/features/phase1-spec.md` — Phase 1 implementation spec
- `docs/features/TOOLS.md` — integration gotchas reference
- `scripts/check_doc_staleness.py` — nightly doc freshness check
- `launchd/com.jade.doc-check.plist` — 10pm launchd job
