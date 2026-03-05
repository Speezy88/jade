# TOOLS.md — Integration Gotchas and Discovered Patterns
*Updated immediately when a new gotcha is discovered. Never let this go stale.*
*IMPORTANT — Read before touching any integration. These prevent repeating known failures.*

---

## ANTHROPIC API

**Model strings (exact — never guess or shorthand):**
- Daily briefings: `claude-haiku-4-5-20251001`
- Dev sessions: `claude-sonnet-4-6`

**Max tokens by task type:**
- Briefings: 500 (intentionally tight — forces concision)
- Time-blocking: 1000
- Tutoring / reasoning: 2000

**API key:** `.env` as `ANTHROPIC_API_KEY`. Always `load_dotenv()` before `os.getenv()`.
**Never log it. Never print it. Never hardcode it.**

**Cost reference:** Haiku ~$0.25/million input tokens | Sonnet ~$3/million input tokens

---

## GOOGLE CALENDAR

**Auth:** OAuth 2.0 — not a simple API key.
**Credentials:** `~/.config/jade/credentials.json` — never in repo, never in `.env`
**Token:** `~/.config/jade/token.json` — auto-generated after first auth, auto-refreshed

**Scopes:**
```python
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]
```

**Known gotchas:**
- Token expires — SDK auto-refreshes if token.json has a refresh token. If auth fails, delete token.json and re-auth.
- Google returns UTC. Always convert to `America/Los_Angeles` before displaying or reasoning about times.
- All-day events have `date` not `dateTime` — handle both or crash on all-day events.
- First run requires browser auth flow — launchd cannot do this. Pre-auth manually before scheduling.

**Fetch pattern (24h events):**
```python
from datetime import datetime, timedelta

now = datetime.utcnow().isoformat() + "Z"
end = (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z"
events = service.events().list(
    calendarId="primary",
    timeMin=now, timeMax=end,
    singleEvents=True, orderBy="startTime"
).execute().get("items", [])
```

---

## SCHOOLOGY (.ICS FEED)

**URL:** `SCHOOLOGY_ICS_URL` in `.env` — never hardcode
**Parser:** `icalendar` Python library
**Cache:** `memory/cache/schoology.json` — 6h refresh via launchd

**Known gotchas:**
- Full export includes past events — always filter `DTSTART >= today`
- Some DTSTART is a date, some is a datetime — handle both
- Feed lags ~6h after teacher posts — treat as "current as of last refresh", not real-time
- URL can change if Schoology re-generates subscription link — if feed stops working, re-export

**Parse pattern:**
```python
from icalendar import Calendar
from datetime import date, datetime, timedelta
import requests, os

def fetch_assignments(days_ahead=14):
    r = requests.get(os.getenv("SCHOOLOGY_ICS_URL"))
    cal = Calendar.from_ical(r.content)
    cutoff = date.today() + timedelta(days=days_ahead)
    assignments = []
    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart = component.get("DTSTART").dt
            if isinstance(dtstart, datetime):
                dtstart = dtstart.date()
            if date.today() <= dtstart <= cutoff:
                assignments.append({
                    "summary": str(component.get("SUMMARY")),
                    "due": dtstart.isoformat()
                })
    return sorted(assignments, key=lambda x: x["due"])
```

---

## OLLAMA (LOCAL INFERENCE)

**Endpoints:**
- ROG (Tier 2): `http://192.168.1.58:11434`
- MSI (Tier 1): `http://192.168.1.152:11434`

**Installed models:**
| Node | Model | Size | Use |
|------|-------|------|-----|
| ROG | deepseek-r1:14b | 9GB | Reasoning, planning (→32b when RAM upgraded) |
| ROG | mistral:7b | 4.4GB | Fast fallback |
| ROG | nomic-embed-text | 274MB | Embeddings (Phase 8) |
| MSI | mistral:7b | 4.4GB | Briefings, fast tasks |
| MSI | llama3.1:8b | ~5GB | Fast utility |
| MSI | nomic-embed-text | 274MB | Embeddings |

**Known gotchas:**
- Windows requires `OLLAMA_HOST=0.0.0.0` set as SYSTEM environment variable (not user) before service starts
- ROG: Ollama runs as Windows service (auto-starts on boot)
- MSI: Ollama runs via `ollama_start.bat` in Windows startup folder (Windows service approach failed)
- Both nodes: Windows Firewall inbound rule open on TCP 11434
- `deepseek-r1` outputs `<think>...</think>` chain-of-thought before final answer — strip these blocks before using response in briefing
- Ollama on Windows does NOT inherit shell PATH — use absolute paths in service configuration

**Offline detection:**
```python
import requests

def is_node_alive(endpoint: str, timeout: float = 2.0) -> bool:
    try:
        r = requests.get(endpoint, timeout=timeout)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False
```

**Ollama API call:**
```python
def call_ollama(endpoint: str, model: str, prompt: str) -> str:
    response = requests.post(
        f"{endpoint}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False}
    )
    return response.json()["response"]
```

---

## MACOS LAUNCHD

**You must use launchd — NOT cron.** cron fails silently on sleep/wake on macOS.
**launchd fires missed jobs after wake** — if the Mac was asleep at the scheduled time, it runs once on next wake.

---

### Plist Inventory

| Plist | Schedule | Script | Purpose |
|-------|----------|--------|---------|
| `com.jade.briefing.plist` | 7:00am daily | `jade_briefing.py` | Morning briefing |
| `com.jade.doc-check.plist` | 10:00pm daily | `scripts/check_doc_staleness.py` | Nightly doc staleness check |

**Plist location:** `~/Library/LaunchAgents/`
**Load all:**
```bash
launchctl load ~/Library/LaunchAgents/com.jade.briefing.plist
launchctl load ~/Library/LaunchAgents/com.jade.doc-check.plist
```
**Verify loaded:**
```bash
launchctl list | grep jade
# Should show both com.jade.briefing and com.jade.doc-check
```
**Test manually:**
```bash
launchctl start com.jade.briefing
launchctl start com.jade.doc-check
```
**Unload:**
```bash
launchctl unload ~/Library/LaunchAgents/com.jade.briefing.plist
launchctl unload ~/Library/LaunchAgents/com.jade.doc-check.plist
```

---

### com.jade.briefing.plist — 7am Morning Briefing

Runs `jade_briefing.py` every morning at 7am.
Fetches live Google Calendar + Schoology data, generates briefing, sends macOS notification.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.jade.briefing</string>

  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/spencerhatch/Jade/jade_briefing.py</string>
  </array>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>7</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key>
    <string>/Users/spencerhatch</string>
  </dict>

  <key>WorkingDirectory</key>
  <string>/Users/spencerhatch/Jade</string>

  <key>StandardOutPath</key>
  <string>/Users/spencerhatch/Jade/logs/briefing.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/spencerhatch/Jade/logs/briefing_error.log</string>

  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
```

---

### com.jade.doc-check.plist — 10pm Nightly Doc Staleness Check

Runs `scripts/check_doc_staleness.py` every night at 10pm.
Detects whether a dev session occurred (git commits, modified .py files).
If yes, checks that PROJECT_STATUS.md and CHANGELOG.md were updated today.
Sends a macOS notification if stale. Silent on days with no dev activity.

This is the fallback enforcement for the stop_hook — it fires regardless of how
the Claude Code session ended (explicit exit, terminal close, machine sleep, timeout).

File is at: `launchd/com.jade.doc-check.plist` in the Jade repo.
Copy to LaunchAgents before loading:
```bash
cp ~/Jade/launchd/com.jade.doc-check.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jade.doc-check.plist
```

**Logs:**
- `logs/doc_check.log` — daily OK/STALE entries
- `logs/doc_check_error.log` — script errors
- `logs/staleness.log` — append-only record of every staleness event

---

### Known gotchas (all plists)

- launchd runs with a minimal environment — does NOT inherit shell PATH or env vars
- Use absolute paths for python3 and every script path in the plist
- `.env` not auto-loaded — use `load_dotenv("/Users/spencerhatch/Jade/.env")` with absolute path
- Google Calendar OAuth requires browser auth on first run — pre-auth manually before loading briefing plist
- If Mac is asleep at the scheduled time, launchd fires once on next wake — this is correct behavior
- `terminal-notifier` path on Apple Silicon: `/opt/homebrew/bin/terminal-notifier`
- `terminal-notifier` path on Intel Mac: `/usr/local/bin/terminal-notifier`
- macOS will prompt for notification permissions on first notification — approve immediately
- Check `*_error.log` files for silent failures before assuming a job ran successfully
- After any plist edit: unload → edit → reload. Changes do not take effect while loaded.

---

## MACOS NOTIFICATIONS

```python
import subprocess

def notify(title: str, message: str):
    subprocess.run([
        "terminal-notifier",
        "-title", title,
        "-message", message,
        "-sound", "default"
    ])
```

**Install:** `brew install terminal-notifier`
**Gotcha:** macOS prompts for notification permissions on first run — approve before scheduling launchd

---

## PYTHON ENVIRONMENT

**Required packages:**
```
anthropic
python-dotenv
google-auth-oauthlib
google-api-python-client
icalendar
requests
```

**Python version:** 3.10+ — match `/usr/bin/python3` on Mac

---

## SKILLS SYSTEM

Jade's skills live in `skills/`. Each skill has:
- `SKILL.md` — trigger keywords, when to use, domain knowledge
- `workflows/` — step-by-step procedures
- (optional) `tools/` — CLI utilities for deterministic sub-tasks

**Current skills:**
| Skill | Triggers | Purpose |
|-------|---------|---------|
| `skills/briefing/` | "briefing", "morning", "daily summary" | Briefing quality standard and format |
| `skills/python-jade/` | any Python dev in Jade | Jade Python conventions, API call patterns |
| `skills/prompt-engineering/` | "prompt", "improve output", "system prompt" | Prompt quality, test-before-commit |

**Rule:** If you repeat a workflow 3+ times, encode it as a skill.

---

*Add new entries immediately when a gotcha is discovered.*
*Format: tool → what failed → why → how to prevent.*
