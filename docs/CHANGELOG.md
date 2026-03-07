# CHANGELOG.md
*Append-only. Most recent entry at top.*

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
