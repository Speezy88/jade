# briefing.md — Morning Briefing Feature
*Phase 1 | Status: Complete and operational*

---

## What It Does

Runs at 7am via launchd. Fetches live weather, calendar events, and assignments.
Assembles a context-rich system prompt. Calls Haiku to generate a structured briefing.
Prints to terminal and fires a macOS notification.

## Entry Point

`jade_briefing.py` — called by `launchd/com.jade.briefing.plist`

## Call Sequence

```
jade_briefing.py
  ├── load_dotenv("/Users/spencerhatch/Jade/.env")
  ├── get_weather()         → "50°F, overcast clouds. High 50°F."
  ├── get_today_events()    → ["4:30 PM — Lacrosse practice"]
  ├── get_upcoming_assignments() → ["Calc HW — due today"]
  ├── build_system_prompt(context={today, weather, calendar_events, assignments})
  ├── anthropic.Anthropic().messages.create(model="claude-haiku-4-5-20251001", max_tokens=500)
  ├── print(briefing)       → stdout → logs/briefing.log
  └── notify(first 2 lines) → macOS notification
```

## Output Format (from SOUL.md briefing spec)

1. One-line situational read on the day
2. Real available work windows from live calendar data
3. Top three priorities, ranked by urgency and stakes
4. One callout on a high-stakes project
5. One closing line — specific, actionable

## Error Handling

- Any integration failure: integrations return fallback strings, briefing still runs
- Fatal error (API failure, missing files): prints to stderr, fires error notification, exits 1
- All errors written to `logs/briefing_error.log` via launchd stderr redirect

## Logs

```bash
tail -f ~/Jade/logs/briefing.log         # stdout
tail -f ~/Jade/logs/briefing_error.log   # stderr / errors
```

## Manual Trigger

```bash
cd ~/Jade && python3 jade_briefing.py
```

## launchd Management

```bash
launchctl start com.jade.briefing    # trigger immediately
launchctl stop com.jade.briefing     # stop if running
launchctl unload ~/Library/LaunchAgents/com.jade.briefing.plist   # disable
launchctl load ~/Library/LaunchAgents/com.jade.briefing.plist     # re-enable
launchctl list | grep jade           # check status
```
