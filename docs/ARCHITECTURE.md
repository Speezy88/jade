# ARCHITECTURE.md
*Last updated: 2026-03-06 | Phase 1 complete*

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
         build_system_prompt()
         [SOUL.md + AI_STEERING_RULES.md + ACTIVE_GOALS.md + runtime context]
                │
                ▼
         Anthropic API (Haiku)
                │
                ▼
         jade_briefing.py → stdout + macOS notification
                │
         launchd (7am)
```

---

## File Responsibilities

| File | Role | Phase |
|------|------|-------|
| `jade_prompts.py` | Single source of truth for system prompt assembly. `build_system_prompt(context)` is the only place prompts are built. | 1 |
| `jade_briefing.py` | Morning briefing entry point. Calls all integrations, builds prompt, calls Haiku, prints output, fires notification. Called by launchd at 7am. | 1 |
| `jade_router.py` | Task routing logic — local vs cloud model selection. Not yet built. | Planned |
| `jade_nightly.py` | Evening check-in. Interactive. Not yet built. | 1.5 |
| `jade_timeblock.py` | Time-blocked schedule generation. Not yet built. | 2 |
| `integrations/weather.py` | OpenWeatherMap free tier. `get_weather()` → formatted string. Never raises. | 1 |
| `integrations/gcal.py` | Google Calendar OAuth2. `get_today_events()` → list of strings. Fetches from `spencerchatch@gmail.com` and `spencerhatch@seattleacademy.org`. Merges and sorts by start time. Never raises. | 1 |
| `integrations/schoology.py` | Schoology ICS feed. `get_upcoming_assignments()` → list of strings. 6h cache at `memory/cache/schoology.json`. Never raises. | 1 |
| `jade_nightly.py` | Nightly interactive check-in. Not yet built. | 1.5 |
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
  + ## RUNTIME CONTEXT (if context dict provided)
      today, weather, calendar_events, assignments
```

Sections joined by `\n\n---\n\n`. No prompt assembly happens anywhere else in the codebase.

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
| `com.jade.doc-check.plist` | 10:00 PM daily | `scripts/check_doc_staleness.py` |

Logs:
- `logs/briefing.log` — briefing stdout
- `logs/briefing_error.log` — briefing stderr
- `logs/doc_check.log` — doc check stdout
- `logs/staleness.log` — append-only staleness events

### Local Cluster (not yet integrated)

| Node | IP | GPU | Tier |
|------|----|-----|------|
| ROG | 192.168.1.58:11434 | RTX 3070 | 2 — Heavy |
| MSI | 192.168.1.152:11434 | RTX 2060 | 1 — Fast |

---

## Not Yet Built (Planned)

- `jade_router.py` — model routing (local vs cloud)
- `jade_nightly.py` — evening check-in (Phase 1.5)
- `jade_timeblock.py` — time-blocking (Phase 2)
- Signal system — ratings.jsonl, FAILURES/ (Phase 3)
- ChromaDB semantic memory (Phase 9)
- Multi-agent orchestration (Phase 10)
