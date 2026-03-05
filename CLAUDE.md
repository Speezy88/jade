# JADE — Claude Code Context
*Assembled from modular components. Read every session.*
*Last updated: March 2026 | v4.0*

---

## WHAT JADE IS

Jade is Spencer Hatch's personal AI infrastructure. A peer-level system built around one person's goals, schedule, and behavioral patterns. Not a generic assistant.

**Intelligence = Model + Scaffolding.** The scaffolding in this file — context, skills, hooks, steering rules — matters more than the model. A well-designed system with a mediocre model outperforms a brilliant model with poor scaffolding. Every time.

Core identity and behavioral rules → `@SOUL.md`
Multi-agent patterns → `@AGENTS.md`
Integration gotchas → `@TOOLS.md`
Current architecture → `@docs/ARCHITECTURE.md`
Project status → `@docs/PROJECT_STATUS.md`
Behavioral guardrails → `@AI_STEERING_RULES.md`

---

## WHO SPENCER IS

**Spencer Hatch** — Junior, Seattle Academy, Seattle WA. ENTJ.
Lacrosse midfielder. Project Manager, Manatee Aquatic. Intern, Wellbeing Think Tank.
Intermediate coder. Hardware design experience. Thinks in systems. Builds toward the next goal before the current one is finished.

**Friction patterns — Jade watches for these:**
1. Procrastination on tasks perceived as small, tedious, or below interest level
2. Vision-execution gap: strong long-term planning, slow to build the scaffolding
3. System adoption: new habits erode after the first week
4. Discipline under load: performance gap widens during dense schedule periods

---

## INFRASTRUCTURE

### Local Cluster
| Node | IP | GPU | Models | Tier |
|------|----|-----|--------|------|
| ROG (PC1) | 192.168.1.58:11434 | RTX 3070 | deepseek-r1:14b, mistral:7b, nomic-embed-text | 2 — Heavy |
| MSI (PC2) | 192.168.1.152:11434 | RTX 2060 | mistral:7b, llama3.1:8b, nomic-embed-text | 1 — Fast |
| Cloud | Anthropic API | — | Haiku (daily ops), Sonnet (dev) | 3 — Critical |

```python
ENDPOINTS = {
    "pc1_heavy": "http://192.168.1.58:11434",
    "pc2_fast":  "http://192.168.1.152:11434",
    "cloud":     "anthropic_api"
}
```

**Routing** → `@jade_router.py` | **Offline fallback:** step up chain automatically, never break.
**Pending:** ROG RAM → 32GB → pull deepseek-r1:32b

---

## FILE STRUCTURE

```
~/Jade/
├── CLAUDE.md                      ← this file
├── SOUL.md                        ← Jade's identity (injected via build_system_prompt())
├── AI_STEERING_RULES.md           ← behavioral guardrails (SYSTEM + USER layers)
├── AGENTS.md                      ← delegation patterns, sub-agents, hooks
├── TOOLS.md                       ← integration gotchas
├── .env                           ← ANTHROPIC_API_KEY only
├── .gitignore
├── requirements.txt
│
├── components/                    ← modular CLAUDE.md components (auto-assembled)
│   ├── 00-identity.md             ← who Spencer is
│   ├── 10-algorithm.md            ← the 7-phase build process
│   ├── 20-routing.md              ← task routing logic
│   ├── 30-memory.md               ← memory system tiers
│   └── 40-skills.md               ← skill routing and definitions
│
├── skills/                        ← reusable capability modules
│   ├── briefing/
│   │   ├── SKILL.md               ← when to use + briefing quality standard
│   │   └── workflows/
│   │       └── morning_briefing.md
│   ├── python-jade/
│   │   ├── SKILL.md               ← Jade Python conventions
│   │   └── workflows/
│   │       └── api_call_pattern.md
│   └── prompt-engineering/
│       └── SKILL.md               ← prompt quality guidelines
│
├── memory/
│   ├── WORK/                      ← active task memory (Miessler Tier 2)
│   │   └── YYYYMMDD-HHMMSS_task-name/
│   │       ├── META.yaml          ← status, session lineage, timestamps
│   │       ├── ISC.json           ← Ideal State Criteria for this task
│   │       ├── items/             ← work artifacts
│   │       └── verification/      ← evidence of completion
│   ├── LEARNING/                  ← accumulated system wisdom (Miessler Tier 3)
│   │   ├── ALGORITHM/             ← how to do tasks better
│   │   ├── FAILURES/              ← full context for low ratings (1-3)
│   │   ├── SYNTHESIS/             ← aggregated pattern analysis
│   │   └── SIGNALS/
│   │       └── ratings.jsonl      ← every rating + sentiment signal (structured)
│   ├── sessions/                  ← raw transcripts, 30-day retention (Miessler Tier 1)
│   ├── goals/
│   │   ├── ACTIVE_GOALS.md        ← injected into every prompt
│   │   ├── college_app/
│   │   ├── wellbeing_internship/
│   │   └── jade_build/
│   ├── cache/
│   │   └── schoology.json
│   ├── time_model/                ← task duration intelligence (Phase 5.5)
│   │   ├── manual_log.csv         ← Spencer's logged task durations
│   │   ├── docs_sessions.json     ← auto-pulled from Google Drive API
│   │   ├── actuals.json           ← planned vs actual comparisons
│   │   └── model.json             ← derived estimates per task type
│   └── meetings/                  ← meeting note taker (Phase 6)
│       └── YYYYMMDD-[slug]/
│           ├── audio.mp3          ← original recording (local only)
│           ├── transcript.txt     ← Whisper output
│           ├── notes.json         ← structured extraction
│           └── execution_plan.md  ← Spencer-approved action plan
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CHANGELOG.md
│   ├── PROJECT_STATUS.md
│   └── features/
│
├── .claude/
│   ├── commands/                  ← slash commands (Tier 1=daily, 2=weekly, 3=per-phase)
│   │   ├── brief.md               ← /brief [T1] — manual briefing trigger
│   │   ├── timeblock.md           ← /timeblock [T1] — time-blocked schedule
│   │   ├── log.md                 ← /log [T1] — task duration entry
│   │   ├── approve.md             ← /approve [T1] — review proposed changes
│   │   ├── retro.md               ← /retro [T2] — end-of-session loop
│   │   ├── update-docs.md         ← /update-docs [T2] — doc sync
│   │   ├── goal-review.md         ← /goal-review [T2] — weekly execution analysis
│   │   ├── meeting.md             ← /meeting [T2] — process meeting audio
│   │   ├── create-issues.md       ← /create-issues [T3] — phase kickoff
│   │   └── arch-review.md         ← /arch-review [T3] — pre-phase-close check
│   └── hooks/                     ← lifecycle hooks (automatic, ~50ms each)
│       ├── load_context.py        ← SessionStart: inject context, rebuild if stale
│       ├── format_reminder.py     ← UserPromptSubmit: FULL/ITERATION/MINIMAL detection
│       ├── rating_capture.py      ← UserPromptSubmit: signals to ratings.jsonl
│       ├── pre_tool_use.py        ← PreToolUse: file protection, injection detection
│       ├── post_tool_use.py       ← PostToolUse: auto-stage writes
│       └── stop_hook.py           ← Stop: enforce doc freshness before close
│
├── scripts/
│   ├── assemble_claude.py         ← rebuilds CLAUDE.md from components/
│   ├── smart_changelog.py         ← LLM reads git diff → meaningful entry
│   ├── check_doc_staleness.py     ← nightly staleness check (via launchd 10pm)
│   └── drift_detector.py          ← weekly: flags undocumented components
│
├── jade_briefing.py
├── jade_timeblock.py
├── jade_nightly.py
├── jade_router.py
├── jade_prompts.py
│
├── integrations/
│   ├── gcal.py
│   ├── schoology.py
│   └── notifier.py
│
├── launchd/                       ← plist files (copy to ~/Library/LaunchAgents/)
│   ├── com.jade.briefing.plist    ← 7am morning briefing
│   └── com.jade.doc-check.plist  ← 10pm nightly doc staleness check
│
├── logs/
│   ├── briefing.log
│   ├── briefing_error.log
│   ├── doc_check.log              ← daily OK/STALE entries
│   ├── doc_check_error.log
│   ├── staleness.log              ← append-only staleness event record
│   └── activity/
│
└── .learnings/
    ├── LEARNINGS.md
    ├── ERRORS.md
    └── FEATURE_REQUESTS.md
```

---

## THE ALGORITHM
*Apply to every non-trivial task. Three response modes — use the right one.*

### Response Mode Detection (automatic)
| Mode | When | Example |
|------|------|---------|
| FULL | Problem-solving, new feature, analysis | "Build the briefing script" |
| ITERATION | Continuing existing work | "Ok, try it with a different model" |
| MINIMAL | Acknowledgments, ratings, greetings | "8", "ok", "thanks" |

**IMPORTANT — Do not run the full Algorithm on MINIMAL interactions. It wastes tokens and context.**

### FULL Mode — 7-Phase Algorithm
| Phase | What Happens |
|-------|-------------|
| OBSERVE | Reverse-engineer the request. What was asked? What was implied? What is definitely NOT wanted? Create ISC. |
| THINK | Validate ISC. Assess available skills. Select right agents and tools. |
| PLAN | Finalize approach. Write the plan. Get Spencer's explicit approval. |
| BUILD | Create artifacts. Invoke skills. Spawn sub-agents if needed. |
| EXECUTE | Run the work against ISC. |
| VERIFY | **THE CULMINATION.** Test every ISC criterion. Record evidence. Did we actually succeed? |
| LEARN | Harvest insights. Update LEARNINGS.md. What would we do differently? |

**IMPORTANT — Never skip VERIFY. Claiming completion without testing criteria is a critical failure.**

### Ideal State Criteria (ISC) Standard
Every ISC criterion must be:
- **Binary** — YES or NO in under 2 seconds
- **State, not action** — "Tests pass" not "Run tests"
- **Granular** — one concern per criterion
- **Specific** — "briefing.py runs without errors" not "script works"

Store ISC in `memory/WORK/[task-name]/ISC.json` — not in chat, not in prose.

---

## MEMORY SYSTEM

Three tiers, based on Miessler Memory System v7.0:

**Tier 1 — Session Memory**
Raw transcripts in `memory/sessions/` — 30-day rolling retention. Automatic.

**Tier 2 — Work Memory**
Structured task context in `memory/WORK/[task-name]/`:
- `META.yaml` — status, session lineage, timestamps
- `ISC.json` — verifiable success conditions
- `items/` — work artifacts
- `verification/` — evidence of completion

Create a WORK directory for every non-trivial task before starting it.

**Tier 3 — Learning Memory**
Accumulated wisdom in `memory/LEARNING/`:
- `SIGNALS/ratings.jsonl` — every rating as structured JSON, not flat text
- `FAILURES/` — full context capture for ratings 1–3
- `ALGORITHM/` — better approaches discovered
- `SYNTHESIS/` — aggregated pattern analysis (run monthly)

**Signal format (ratings.jsonl):**
```json
{"date": "2026-03-04", "session_id": "abc123", "rating": 8, "comment": "briefing was tight", "feature": "morning_briefing", "implicit_sentiment": null}
{"date": "2026-03-05", "session_id": "def456", "rating": 3, "comment": "hallucinated schedule", "feature": "morning_briefing", "implicit_sentiment": "frustrated"}
```

**Promotion rule:** Signal pattern with rating ≤3, occurring ≥3 times, across ≥2 distinct tasks, within 30 days → propose new AI Steering Rule. Spencer approves before it's added to `AI_STEERING_RULES.md`.

---

## SKILLS

Skills are reusable capability modules. When a request matches a skill's triggers, route to it.

| Skill | Trigger Keywords | What It Provides |
|-------|-----------------|-----------------|
| `skills/briefing/` | "briefing", "morning", "daily" | Quality standard, format, tone for briefings |
| `skills/python-jade/` | any Python development task | Jade conventions, error handling, API call patterns |
| `skills/prompt-engineering/` | "prompt", "system prompt", "improve output" | Prompt quality guidelines, test-before-commit pattern |

Build new skills when a workflow is repeated 3+ times. Encode it once, reuse forever.

---

## CORE ARCHITECTURE RULES

**IMPORTANT — these rules are non-negotiable:**

1. **build_system_prompt() is the only place prompts are assembled.** Never inline system prompts in scripts.

2. **Live data or no claim.** If Jade states anything about Spencer's schedule, it must have fetched it. No hallucinated context.

3. **Jade proposes, Spencer approves.** Goal files (`memory/goals/*/`) are never mutated autonomously.

4. **ISC before code.** Create `memory/WORK/[task]/ISC.json` before writing a line. VERIFY every criterion before closing the task.

5. **Privacy boundary.** Activity monitor: app-level only. Raw logs: local only. OAuth credentials: `~/.config/jade/credentials.json` — never in `.env`, never committed.

6. **Protected files.** SOUL.md, AGENTS.md, AI_STEERING_RULES.md require Spencer's explicit approval before any modification. The PreToolUse hook enforces this automatically.

---

## HOOKS
*The nervous system. Fires automatically. Not dependent on Spencer remembering anything.*
*Full implementations in `AGENTS.md`. Summary here.*

| Hook | Trigger | What It Does |
|------|---------|-------------|
| `load_context.py` | SessionStart | Rebuilds CLAUDE.md if components changed. Injects SOUL.md, ACTIVE_GOALS.md, AI_STEERING_RULES.md. Surfaces open WORK tasks and pending approvals. |
| `format_reminder.py` | UserPromptSubmit | Detects FULL / ITERATION / MINIMAL mode. Prevents full Algorithm on simple replies. |
| `rating_capture.py` | UserPromptSubmit | Captures 1–10 ratings to ratings.jsonl. Triggers failure capture for ratings ≤3. Rejects false positives. |
| `pre_tool_use.py` | PreToolUse | Blocks writes to protected files. Scans external content for injection patterns. |
| `post_tool_use.py` | PostToolUse | Auto-stages every file write. Skips credentials files. |
| `stop_hook.py` | Stop | Blocks session close if PROJECT_STATUS.md or CHANGELOG.md are stale. |

---

## SLASH COMMANDS
*Full implementations in `.claude/commands/`. Summary here.*

**Tier 1 — Daily use:**
| Command | Usage | What It Does |
|---------|-------|-------------|
| `/brief` | Any time | Manual briefing trigger. Fetches live data. Uses time model if available. |
| `/timeblock` | Morning or after schedule change | Time-blocked schedule from live calendar + task queue + duration model. |
| `/log` | After any work session | Quick time entry. Appends to manual_log.csv. Shows running median. |
| `/approve` | When Jade has proposed changes | Review and commit proposed goal files, steering rules, SOUL.md changes. |

**Tier 2 — Weekly use:**
| Command | Usage | What It Does |
|---------|-------|-------------|
| `/retro` | End of every dev session | Self-improving loop. Captures learnings. Checks promotion rule. Proposes component updates. |
| `/update-docs` | After completing any feature | Syncs ARCHITECTURE, CHANGELOG, PROJECT_STATUS. Required before session close. |
| `/goal-review` | Sunday | Execution gap analysis. Rebuilds time model. Surfaces drifting goals. Stages pending changes for /approve. |
| `/meeting` | After any recorded meeting | Whisper transcription → structured notes → execution plan → proposed calendar blocks. |

**Tier 3 — Per-phase use:**
| Command | Usage | What It Does |
|---------|-------|-------------|
| `/create-issues` | Phase kickoff | Converts phase spec into sized GitHub issues with ISC. |
| `/arch-review` | Pre-phase-close | Code vs documentation gap check. ISC verification. Routes to ROG Tier 2. |
| `/changelog` | Post-commit (auto) | LLM diff interpretation via MSI Tier 1. Also runs automatically on commit. |

---

## BUILD PHASES

| Phase | Deliverable | Status | WORK Dir |
|-------|-------------|--------|---------|
| 1 | Morning briefing — live Calendar + Schoology, launchd, SOUL.md | 🔨 Current | `memory/WORK/phase-1-briefing/` |
| 2 | Calendar time-blocking — `/timeblock` command, gcal read+write | Planned | — |
| 3 | Signal system — ratings.jsonl, FAILURES/, structured memory | Planned | — |
| 4 | Goal action plans + briefing check-ins | Planned | — |
| 5 | Nightly briefing — day vs plan, gap analysis, streaks | Planned | — |
| 5.5 | Task duration intelligence — Drive API + manual `/log` + time model | Planned | — |
| 6 | Meeting note taker — Whisper local + `/meeting` command + execution plans | Planned | — |
| 7 | Activity monitor — app-level logging, Tier 1 summarizer | Planned | — |
| 8 | TTS — Kokoro local first, ElevenLabs fallback | Planned | — |
| 9 | ChromaDB + nomic-embed-text semantic memory | Planned | — |
| 10 | Multi-agent orchestration across both PCs | Future | — |
| 11 | Raspberry Pi physical interface | Future | — |

---

## INTEGRATIONS

**Google Calendar** → `@docs/features/gcal_integration.md`
SDK: `google-auth-oauthlib` + `googleapiclient` | Credentials: `~/.config/jade/credentials.json`

**Schoology** → `@docs/features/schoology.md`
.ics feed | Parser: `icalendar` | Cache: `memory/cache/schoology.json` — 6h refresh

**Anthropic API:** Briefings → `claude-haiku-4-5-20251001` | Dev → `claude-sonnet-4-6`

**Scheduler:** `launchd` — NOT cron. Plist: `~/Library/LaunchAgents/com.jade.briefing.plist`

---

## COST CEILING: ≤$15/month
Haiku briefings ~$3 | Sonnet dev ~$8 | ElevenLabs if added ~$5 | Local inference free

---

## SESSION CHECKLIST
*The load_context.py hook handles most of this automatically. This is the manual fallback.*

1. `cd ~/Jade && claude` — LoadContext hook fires, injects everything
2. Verify active WORK tasks loaded — check `memory/WORK/` for open tasks
3. Shift+Tab → Plan Mode — scope the session
4. Create `memory/WORK/[task]/ISC.json` before any code
5. Approve plan before execution
6. New Git branch per significant feature
7. `/update-docs` when feature done
8. `/retro` at end of session — stop_hook enforces this
9. Rate today's briefing 1–10 — rating_capture hook records automatically

---

*This file is assembled from `components/` by `scripts/assemble_claude.py`.*
*Edit components, not this file directly. Run assemble_claude.py after any component change.*
*AI Steering Rules are in `AI_STEERING_RULES.md` — not here.*
