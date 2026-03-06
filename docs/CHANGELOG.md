# CHANGELOG.md
*Append-only. Most recent entry at top.*

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
