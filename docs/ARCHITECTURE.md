# ARCHITECTURE.md
*Last updated: 2026-03-07 | Phase 1.5 complete*

---

## System Overview

Jade is a personal AI infrastructure for Spencer Hatch. The core pattern:
**live data → context → system prompt → Haiku → output**.

```
.env (keys)
    │
    ├── integrations/weather.py   → weather string
    ├── integrations/gcal.py      → calendar event list
    └── integrations/schoology.py → assignment list (cached)
                │
                ▼
         jade_prompts.py
         build_system_prompt()          build_nightly_system_prompt()
         [SOUL + STEERING + GOALS       [SOUL + STEERING + GOALS
          + runtime context]             + nightly context + recent logs]
                │                                  │
                ▼                                  ▼
         Anthropic API (Haiku)          Anthropic API (Haiku, multi-turn)
                │                                  │
                ▼                                  ▼
         jade_briefing.py               jade_nightly.py
         stdout + chat loop             interactive terminal (5 phases A→E)
                │                          │
         extract_morning_context()  extract_structured() → nightly log
                │                   + tomorrow_context.json
         morning_context.json            │
         (fallback: logs/morning/)  launchd (9:15pm/8:45pm via osascript)
                │
         launchd (7am)
```

---

## File Responsibilities

| File | Role | Phase |
|------|------|-------|
| `jade_prompts.py` | Single source of truth for system prompt assembly. `build_system_prompt(context)` for briefing; `build_nightly_system_prompt(context)` for nightly check-in. No other file assembles prompts. | 1 |
| `jade_briefing.py` | Morning briefing entry point. Calls all integrations, loads nightly context, builds prompt, calls Haiku, prints briefing. After print: interactive chat loop (max 10 turns, Jade-driven closure). Post-chat: `extract_morning_context()` → `memory/cache/morning_context.json`. Fires notification after chat completes. Falls back to `memory/logs/morning/` transcript on extraction failure. Called by launchd at 7am. | 1 |
| `jade_nightly.py` | Nightly interactive check-in. Five-phase conversation (A→E). Post-session structured extraction to `memory/logs/nightly/` and `memory/cache/tomorrow_context.json`. Hardened extraction: strips markdown fences, logs raw response on failure, writes transcript fallback. Called by launchd via osascript at 9:15pm (weekdays) / 8:45pm (weekends). | 1.5 |
| `jade_router.py` | Task routing logic — local vs cloud model selection. Not yet built. | Planned |
| `jade_timeblock.py` | Time-blocked schedule generation. Not yet built. | 2 |
| `integrations/weather.py` | OpenWeatherMap free tier. `get_weather()` → formatted string. Never raises. | 1 |
| `integrations/gcal.py` | Google Calendar OAuth2. `get_today_events()` → list of strings. Fetches from `spencerchatch@gmail.com` and `spencerhatch@seattleacademy.org`. Merges and sorts by start time. Never raises. | 1 |
| `integrations/schoology.py` | Schoology ICS feed. `get_upcoming_assignments()` → list of strings. 6h cache at `memory/cache/schoology.json`. Never raises. | 1 |
| `scripts/check_doc_staleness.py` | Nightly doc staleness check via launchd at 10pm. Notifies if PROJECT_STATUS.md or CHANGELOG.md are stale after a dev session. | 0 |
| `SOUL.md` | Jade's behavioral identity. Injected into every prompt via `build_system_prompt()`. Protected — requires explicit approval to modify. | 0 |
| `AI_STEERING_RULES.md` | Behavioral guardrails (SYSTEM + USER layers). Injected via `build_system_prompt()`. Protected. | 0 |
| `memory/ACTIVE_GOALS.md` | Spencer's live goal state. Injected via `build_system_prompt()`. | 0 |
| `memory/cache/schoology.json` | 6h Schoology assignment cache. Schema: `{fetched_at: ISO string, assignments: [{summary, due_date}]}` | 1 |

---

## Prompt Assembly

`build_system_prompt(context: dict | None)` in `jade_prompts.py`:

```
SOUL.md
  + AI_STEERING_RULES.md (optional — warns if missing, doesn't crash)
  + memory/ACTIVE_GOALS.md
  + ## BRIEFING TONE (conversational register + chat closure instruction)
  + ## RUNTIME CONTEXT (if context dict provided)
      today, weather, calendar_events, assignments
```

Sections joined by `\n\n---\n\n`. No prompt assembly happens anywhere else in the codebase.

`build_nightly_system_prompt(context: dict)` in `jade_prompts.py`:

```
SOUL.md
  + AI_STEERING_RULES.md (optional)
  + memory/ACTIVE_GOALS.md
  + ## NIGHTLY SESSION CONTEXT
      today, days_to_act, calendar_events, domains, recent_logs (last 3 nights)
  + Nightly Session Structure instructions
```

---

## Integration Contracts

### integrations/weather.py
- **Input:** `OPENWEATHERMAP_API_KEY` from `.env`
- **Output:** `"52°F, overcast clouds. High 55°F."` or `"Weather unavailable."`
- **Failure mode:** Returns fallback string. Never raises.

### integrations/gcal.py
- **Input:** OAuth token at `~/.config/jade/token.json`, credentials at `~/.config/jade/credentials.json`
- **Calendars:** `spencerchatch@gmail.com`, `spencerhatch@seattleacademy.org`
- **Output:** `["9:00 AM — Math class", "All day — No School"]` or `[]`
- **Failure mode:** Per-calendar errors logged to stderr, skipped. Full failure returns `[]`. Never raises.

### integrations/schoology.py
- **Input:** `SCHOOLOGY_ICS_URL` from `.env`, cache at `memory/cache/schoology.json`
- **Cache TTL:** 6 hours
- **Output:** `["AP History reading — due today", ...]` or `[]` or `["Schoology unavailable — check manually."]`
- **Failure mode:** Missing URL or fetch error → error string list. Empty cache → `[]`. Never raises.

---

## Credential Locations

| Credential | Location | Notes |
|------------|----------|-------|
| `ANTHROPIC_API_KEY` | `~/Jade/.env` | Required for all API calls |
| `OPENWEATHERMAP_API_KEY` | `~/Jade/.env` | Free tier |
| `SCHOOLOGY_ICS_URL` | `~/Jade/.env` | ICS feed URL (https://, not webcal://) |
| Google OAuth credentials | `~/.config/jade/credentials.json` | Never committed |
| Google OAuth token | `~/.config/jade/token.json` | Auto-generated on first auth |

---

## Infrastructure

### launchd Jobs

| Plist | Fires | Script |
|-------|-------|--------|
| `com.jade.briefing.plist` | 7:00 AM daily | `jade_briefing.py` |
| `com.jade.nightly.plist` | 9:15 PM weekdays / 8:45 PM weekends | `jade_nightly.py` (via osascript → Terminal) |
| `com.jade.doc-check.plist` | 10:00 PM daily | `scripts/check_doc_staleness.py` |

Logs:
- `logs/briefing.log` — briefing stdout
- `logs/briefing_error.log` — briefing stderr
- `logs/doc_check.log` — doc check stdout
- `logs/staleness.log` — append-only staleness events
- `memory/logs/nightly/YYYY-MM-DD.md` — nightly check-in structured log
- `memory/logs/morning/YYYY-MM-DD.md` — morning chat fallback transcript (when extraction fails)
- `memory/cache/tomorrow_context.json` — nightly context passed to next morning's briefing
- `memory/cache/morning_context.json` — morning chat extraction; schema: `{date, schedule_additions, adjustments, focus, notes}`

### Local Cluster (not yet integrated)

| Node | IP | GPU | Tier |
|------|----|-----|------|
| ROG | 192.168.1.58:11434 | RTX 3070 | 2 — Heavy |
| MSI | 192.168.1.152:11434 | RTX 2060 | 1 — Fast |

---

## Not Yet Built (Planned)

- `jade_router.py` — model routing (local vs cloud)
- `jade_timeblock.py` — time-blocking (Phase 2)
- Signal system — ratings.jsonl, FAILURES/ (Phase 3)
- ChromaDB semantic memory (Phase 9)
- Multi-agent orchestration (Phase 10)
