# JADE Phase 2.5–2.7 Spec: Notion Integration + Research Layer

**Status:** PLANNING — Ready for Claude Code execution  
**Depends on:** Phase 1 (briefing) + Phase 1.5 (nightly check-in) complete  
**Author:** Spencer + Jade  
**Date:** April 2026

---

## Overview

Three tightly coupled phases that turn Notion into JADE's external brain:

| Phase | Name | Deliverable |
|-------|------|-------------|
| 2.5 | Notion Task Layer | To-do database → feeds morning briefing + nightly |
| 2.6 | Notion Project Engine | Create/edit projects in enforced schema format |
| 2.7 | Research Pipeline | Perplexity source-finding → Claude synthesis → findings land in project |
| 2.8 | Skills Layer | Skill roadmaps + practice log + opportunities, research-powered |

**Core design principle:** Every project page must answer "where am I and what do I do right now" in under 10 seconds. Everything else serves that.

---

## Workspace Architecture

### Top-Level Structure

```
Spencer's Notion Workspace
├── 🏠 Home Dashboard          ← Daily view: tasks due today + next actions
├── ✅ Tasks                   ← Master task database (all areas)
├── 📁 Projects                ← Master project database (all areas)
├── 🔬 Research Vault          ← Perplexity + Claude findings + source library
├── 🛠️ Skills                  ← Personal skill development (own DB structure)
└── Areas/
    ├── 🎓 School + ACT + College Apps
    ├── 🧠 Wellbeing Think Tank
    ├── 🎯 Personal Goals
    ├── 💼 Side Projects / Business
    └── 📚 Reading + Learning
```

### Area Folder Format (Consistent Across All 5 Areas)

Each Area folder contains:
```
[Area Name]/
├── Area Overview          ← One-page summary: current focus, active projects
├── Projects (filtered)    ← View of Projects DB filtered to this area
├── Tasks (filtered)       ← View of Tasks DB filtered to this area
└── Research (filtered)    ← View of Research Vault filtered to this area
```

This means one master database per type (Tasks, Projects, Research) with area-filtered views — not separate databases per area. Keeps everything queryable by Jade in one place.

Skills is the exception — it has its own dedicated database (Skills DB) rather than being a filtered view, because skill pages have a fundamentally different schema from projects and tasks.

---

## Phase 2.5 — Notion Task Layer

### Task Database Schema

| Field | Type | Values / Notes |
|-------|------|----------------|
| Task Name | Title | Required |
| Area | Select | School/ACT/College Apps, Wellbeing Think Tank, Personal Goals, Side Projects/Business, Reading/Learning |
| Priority | Select | 🔴 High, 🟡 Medium, 🟢 Low |
| Due Date | Date | Date + time when relevant |
| Energy | Select | 🔵 Deep Work, ⚡ Light Work |
| Estimated Duration | Number | Minutes |
| Linked Project | Relation | → Projects DB |
| Recurring | Checkbox | Is this a recurring task? |
| Recurrence Type | Select | Daily chunk, Weekly, Custom |
| Total Target (mins) | Number | For goal-based recurrence: total time budget |
| Chunk Size (mins) | Number | Daily time chunk (e.g. 30) |
| Recurrence Start | Date | When recurring blocks begin |
| Recurrence End | Date | Auto-calculated: Start + (Total ÷ Chunk) days |
| Status | Select | Not Started, In Progress, Done, Skipped |
| Notes | Text | Any context Jade or Spencer adds |

### Goal-Based Recurrence Logic

This is distinct from standard repeating tasks. When `Recurring = true` and `Recurrence Type = Daily chunk`:

```
Input:  Total Target = 360 mins (6 hrs), Chunk = 30 mins/day
Output: 12 daily task instances created, each 30 mins
        Recurrence End = Start Date + 12 days
        Each instance links back to parent task for progress tracking
```

`jade_notion.py` handles this calculation and bulk-creates the child task instances in Notion via API. Parent task shows aggregate progress.

### Briefing Integration

`jade_notion.py` exposes:
```python
get_todays_tasks()      # Tasks due today, sorted by priority then time
get_upcoming_tasks(n)   # Next n days of tasks
get_overdue_tasks()     # Anything past due and not Done/Skipped
```

`jade_briefing.py` calls these at 7am. Morning briefing gains a new section:

```
TODAY'S TASKS
─────────────
🔴 [High] Finish college app essay draft — 90 mins (Deep Work) — due 11:59pm
🟡 [Med]  ACT practice set — 30 mins (Deep Work) — 4:00pm
🟢 [Low]  Read chapter 3 — 20 mins (Light Work) — anytime

⚠️  OVERDUE: WTT slide deck (was due yesterday)
```

`jade_nightly.py` calls `get_todays_tasks()` at session start to ask about specific tasks by name rather than generic "how did your work go."

---

## Phase 2.6 — Notion Project Engine

### Project Database Schema

#### Header Fields (visible at top of every project page)

| Field | Type | Values / Notes |
|-------|------|----------------|
| Project Name | Title | Required |
| One-Line Goal | Text | What does done look like in one sentence? |
| Why It Matters | Text | Motivation/stake — why this, why now |
| Area | Select | Same 5 areas as Tasks |
| Status | Select | 🔲 Not Started, 🔄 Active, 🚧 Blocked, ✅ Done |
| Deadline | Date | Hard or target (flagged in second field) |
| Deadline Type | Select | Hard (non-negotiable), Target (aim for) |
| Time Budget | Number | Total hours estimated for full project |
| Owner | Person | Spencer by default |
| Collaborators | Person (multi) | Optional |
| Progress % | Formula | Auto-calculated from linked Done tasks ÷ total tasks |

#### The 10-Second Re-Orientation Block

This is the first thing visible when you open any project page. Fixed section at top of page body (not a database field — a Notion page section):

```
┌─────────────────────────────────────────────┐
│  ⚡ NEXT ACTION                              │
│  [Single most important thing to do right now]│
│                                             │
│  📍 WHERE I AM                              │
│  [1-2 sentences on current phase/status]    │
│                                             │
│  🚧 BLOCKERS (if any)                       │
│  [What's in the way, if anything]           │
└─────────────────────────────────────────────┘
```

Jade updates this block after every nightly check-in where the project was discussed. Spencer can edit manually anytime.

#### Page Body Structure (Standard for All Projects)

```
## Milestones
[ ] Milestone 1 — [date]
[ ] Milestone 2 — [date]
[ ] Milestone 3 — [date]

## Success Criteria
- I'll know this is done when: ___
- Quality bar: ___

## Linked Tasks
[Filtered view of Tasks DB → this project]

## Research
[Filtered view of Research Vault → this project]
[Perplexity + Claude findings land here]

## Notes & Journal
[Ongoing thoughts, decisions, context — append-only with dates]

## Resources
[Links, files, references]
```

### Project Creation — Jade Interface

When Spencer says (in nightly check-in or directly):
> "Create a project for [X]"

Jade runs `create_project()` which:

1. Prompts for any missing required fields (Name, Goal, Why, Area, Deadline)
2. Validates schema compliance — no project created without Name + Goal + Area
3. Creates the Notion page with all fields populated
4. Writes the 10-second re-orientation block with current status = "Just started"
5. Creates an initial Next Action based on what Spencer says
6. Returns the Notion URL and confirms creation

```python
# jade_notion.py
def create_project(name, goal, why, area, deadline, deadline_type,
                   time_budget, collaborators=None, milestones=None):
    """Enforces schema. Raises ValueError if required fields missing."""

def edit_project(project_id, updates: dict):
    """Partial update — only touch fields in updates dict."""

def update_next_action(project_id, next_action, where_i_am, blockers=None):
    """Rewrites the 10-second re-orientation block."""

def get_active_projects(area=None):
    """Returns active projects, optionally filtered by area."""
```

### Project Editing — Jade Interface

Jade can edit projects from:
- **Nightly check-in:** "How's the WTT slide deck going?" → update Next Action, add journal note
- **Direct command:** "Mark the ACT prep project as blocked — waiting on test scores"
- **Morning briefing:** If a project deadline is within 48 hours, Jade flags it

---

## Phase 2.7 — Research Pipeline

### Why Not NotebookLM as the Automated Layer

NotebookLM was evaluated and ruled out as an automated pipeline dependency for two reasons:

1. **Wrong tool for JADE's workflow.** NotebookLM excels at deep analysis of documents you *already have*. JADE's research need is the opposite — starting from a topic or project goal and finding the best sources. That's a source-discovery problem, which is Perplexity's core strength.

2. **No official API.** All current NotebookLM MCP integrations operate via unofficial browser automation, which can break with any Google UI update and may violate Google's Terms of Service. A core productivity system shouldn't depend on that.

**NotebookLM's role stays in the stack** — but as a manual companion tool. When Spencer has a specific set of PDFs or documents to digest deeply (e.g. college application essays, ACT prep materials, WTT research papers), NotebookLM is the right tool to open manually. It does not get automated.

### Architecture

```
Research Request (natural language)
      │
      ▼
jade_research.py
      │
      ├─→ Source Finding — Perplexity Deep Research API
      │       - Runs 10–50 web searches autonomously
      │       - Returns ranked sources with inline citations
      │       - Handles current events, web sources, real-time data
      │
      ├─→ Academic Layer (conditional) — Google Scholar / Semantic Scholar API
      │       - Triggered when topic = school, ACT, WTT research
      │       - Peer-reviewed sources weighted higher
      │
      ▼
Synthesis — Claude (Haiku, same model as rest of JADE)
      - Reads Perplexity source list + content
      - Synthesizes 3–5 key findings in plain language
      - Rates source confidence (High/Medium/Low)
      - Identifies open questions and gaps
      - Maps findings to project Goal + Success Criteria
      │
      ▼
Research Note created in Notion Research Vault
      - Title, query, date, sources, findings, open questions
      - Linked to Project (if applicable)
      - Applied Insights written into project Research section
```

### Tool Roles (Clear Separation)

| Tool | Role | Automated? |
|------|------|-----------|
| Perplexity Deep Research API | Source discovery + web research | ✅ Yes |
| Google/Semantic Scholar | Academic source finding | ✅ Yes (conditional) |
| Claude (Haiku) | Synthesis + applied insights | ✅ Yes |
| Notion Research Vault | Persistent storage of all findings | ✅ Yes |
| NotebookLM | Deep-dive on specific document sets | ❌ Manual only |

### Research Vault Schema

| Field | Type | Notes |
|-------|------|-------|
| Research Title | Title | Auto-generated from query |
| Query | Text | What was asked |
| Area | Select | Same 5 areas |
| Linked Project | Relation | → Projects DB (optional) |
| Date | Date | When research ran |
| Sources | Text | URLs + titles, ranked |
| Key Findings | Text | 3-5 bullet synthesis |
| Open Questions | Text | What this research didn't answer |
| Confidence | Select | High / Medium / Low |
| Status | Select | Draft, Reviewed, Applied |

### Research Triggers

Research can be initiated from:
1. **Direct:** "Jade, research [topic] for my [project]"
2. **Project creation:** "Create a project for X" → Jade asks "Want me to pull research on X?"
3. **Nightly check-in:** Spencer mentions needing to understand something → Jade offers to research overnight
4. **Briefing flag:** If a project has no research and deadline < 2 weeks, Jade flags it

### Applied Research

"Applies findings where relevant in the project file" means:

When research is linked to a project, Jade:
1. Reads the project's Goal + Success Criteria
2. Reads the Research Vault findings
3. Identifies which findings are directly actionable for this project
4. Writes an "Applied Insights" subsection inside the project's Research section:

```
## Research
### Sources
[links to Research Vault entries]

### Applied Insights
Based on research into [topic]:
- [Finding 1] → suggests [specific action for this project]
- [Finding 2] → informs [milestone or decision]
- Open question: [X] — may need follow-up research before [milestone]
```

---

## Phase 2.8 — Skills Layer

### Design Philosophy

Skills follow Spencer's learning model: **Learn → Apply → Observe → Mentor feedback**. Every stage of every skill roadmap is structured around these four buckets. Research doesn't produce a generic resource dump — it produces actionable guidance in each bucket for the current stage.

Skills is architecturally separate from Projects and Tasks because the schema and lifecycle are different. A project has a deadline and finishes. A skill compounds indefinitely and has stages, not a done state.

### Skills Database Structure

```
🛠️ Skills/
├── Skills DB              ← One page per skill, standard schema
├── Practice Log DB        ← Lightweight entries for High priority skills only
└── Opportunities DB       ← Best current opportunities per skill, replaced each cycle
```

### Skills DB — Page Schema (Header Fields)

| Field | Type | Values / Notes |
|-------|------|----------------|
| Skill Name | Title | Required — e.g. "Programming / CS", "Sales" |
| Priority | Select | 🔴 High, 🟡 Medium, 🟢 Low |
| Current Stage | Text | Name of the active roadmap stage |
| Stage Status | Select | Active, Blocked, Complete |
| Next Session | Text | Single most important thing to do next time |
| Last Practiced | Date | Jade flags if cold for 14+ days (High priority only) |
| Linked Projects | Relation | → Projects DB (projects that build this skill) |
| Linked Research | Relation | → Research Vault (research tied to this skill) |

### Skill Page Body (Standard Across All Skills)

```
## Roadmap
Stage 1: [name]  ✅ Complete
Stage 2: [name]  ← CURRENT
Stage 3: [name]
Stage 4: [name]
...

## Current Stage
### Learn
[What to study, read, or watch at this stage — specific resources]

### Apply
[Specific project or exercise to build real competency]

### Observe
[What to pay attention to, how to self-assess progress]

### Mentor
[Who to find, what to ask, communities to join, people to follow]

## Opportunities
[Filtered view of Opportunities DB → this skill]
[Replaced each research cycle with the 3–5 best current options]

## Practice Log
[Filtered view of Practice Log DB → this skill]
[High priority skills only — lightweight entries]

## Research
[Filtered view of Research Vault → this skill]
```

### Practice Log DB — Schema

Lightweight by design. Jade prompts for this during nightly check-in for High priority skills only. Takes 30 seconds, not a form.

| Field | Type | Notes |
|-------|------|-------|
| Entry Title | Title | Auto-generated: "[Skill] — [Date]" |
| Skill | Relation | → Skills DB |
| Date | Date | Auto-filled |
| What I Did | Text | One line — what was practiced |
| What I Noticed | Text | One line — observation, insight, or friction |

### Opportunities DB — Schema

Replaced (not appended) each research cycle. Jade keeps the 3–5 best current options per skill, discards stale ones.

| Field | Type | Notes |
|-------|------|-------|
| Opportunity Name | Title | Name of course, mentor, project, competition, etc. |
| Skill | Relation | → Skills DB |
| Type | Select | Course, Book, Mentor/Community, Project, Competition, Other |
| URL | URL | Link to the resource |
| Why It's Relevant | Text | One line — why Jade surfaced this |
| Stage Relevance | Text | Which roadmap stage this applies to |
| Last Updated | Date | Date of the research cycle that added it |

### Research Layer Behavior for Skills

**Trigger: New skill created**
Jade runs a full research job producing:
- A complete stage-by-stage roadmap for this skill (5–8 stages typical)
- For the current stage: full Learn / Apply / Observe / Mentor breakdown
- Top 3–5 opportunities (courses, communities, projects, competitions)
- All written into the skill page and Opportunities DB

**Trigger: Stage advancement**
Spencer says "I finished Stage 2 of Programming" (in nightly check-in or directly) → Jade:
1. Marks current stage complete on the roadmap
2. Advances `Current Stage` field to next stage
3. Runs a focused research job for the new stage only
4. Updates Current Stage section (Learn/Apply/Observe/Mentor) with new findings
5. Refreshes Opportunities DB with stage-relevant options

**Trigger: Proactive refresh (scheduled)**
Only `Priority = High` skills. Jade runs monthly and:
- Checks for new/better opportunities
- Replaces Opportunities DB if better ones found
- Flags anything notable in the next morning briefing
Medium and Low priority skills: research only on demand or stage advancement.

**Trigger: Manual**
"Jade, research [skill]" or "Jade, refresh opportunities for Sales" → runs immediately.

### Jade's Ongoing Skill Management

```python
# jade_notion.py additions
def create_skill(name, priority, entry_stage=None):
    """Creates skill page, triggers initial research job."""

def advance_skill_stage(skill_id, completed_stage):
    """Marks stage complete, advances current, triggers stage research."""

def update_skill_next_session(skill_id, next_session):
    """Updates Next Session field after nightly check-in discussion."""

def get_cold_skills(days=14):
    """Returns High priority skills not practiced in N days."""

def refresh_opportunities(skill_id):
    """Replaces Opportunities DB entries for a skill with fresh research."""
```

**Morning briefing additions:**
- High priority skills cold for 14+ days → flagged by name
- Any new high-value opportunity found in a monthly refresh → surfaced once

**Nightly check-in additions:**
- For High priority skills: "Did you practice [Skill] today? What did you work on / what did you notice?" → writes Practice Log entry if yes
- If Spencer mentions completing a stage → triggers stage advancement flow

### Adding a New Skill

One command in nightly check-in or directly:
> "Jade, add [Skill Name] as a [High/Medium/Low] priority skill"

Jade creates the page, runs the initial research job, populates the full roadmap and current stage, and returns the Notion URL. Under 2 minutes end to end.

---

```
Phase 2.5 first — Tasks layer is simplest and immediately useful
  ├── Set up Notion workspace structure (manual, one-time)
  ├── Create Tasks database with full schema
  ├── Build jade_notion.py (task CRUD + recurrence logic)
  ├── Wire into jade_briefing.py
  ├── Wire into jade_nightly.py
  └── ISC: briefing shows today's tasks, nightly references tasks by name

Phase 2.6 second — Projects layer builds on tasks
  ├── Create Projects database
  ├── Create area folder structure + filtered views
  ├── Add create_project() + edit_project() to jade_notion.py
  ├── Wire project creation/editing into nightly check-in
  └── ISC: Jade creates valid project, 10-sec block renders correctly

Phase 2.7 third — Research layer depends on both
  ├── Build jade_research.py with Perplexity Deep Research API
  ├── Add conditional Google/Semantic Scholar for academic topics
  ├── Wire Claude synthesis layer (reuses existing Haiku setup)
  ├── Create Research Vault database in Notion
  ├── Wire research triggers into nightly + project creation
  └── ISC: full pipeline runs, findings land in correct project page

Phase 2.8 last — Skills layer depends on research pipeline
  ├── Create Skills DB, Practice Log DB, Opportunities DB in Notion
  ├── Add skill functions to jade_notion.py
  ├── Wire initial research job into create_skill()
  ├── Wire stage advancement into nightly check-in
  ├── Wire cold-skill detection into morning briefing
  ├── Wire monthly refresh scheduler for High priority skills
  └── ISC: all criteria 19–24 pass
```

---

## ISC Criteria

### Phase 2.5
- ISC-1: Morning briefing shows today's tasks sorted by priority
- ISC-2: Overdue tasks flagged in briefing
- ISC-3: Nightly references specific task names from today's list
- ISC-4: Goal-based recurrence creates correct number of child instances
- ISC-5: Recurrence end date calculated correctly from chunk math
- ISC-6: Task status updates in Notion reflect in next briefing

### Phase 2.6
- ISC-7: `create_project()` fails with clear error if Name/Goal/Area missing
- ISC-8: All 10 schema fields populated on project creation
- ISC-9: 10-second re-orientation block renders at top of every project page
- ISC-10: `edit_project()` only touches specified fields, leaves others intact
- ISC-11: Nightly check-in updates Next Action after project discussion
- ISC-12: Active projects with deadline < 48hrs flagged in morning briefing

### Phase 2.7
- ISC-13: Research pipeline runs end-to-end from natural language query
- ISC-14: Sources ranked and attributed correctly in Research Vault
- ISC-15: Findings linked to correct project page
- ISC-16: Applied Insights section written in project Research section
- ISC-17: Academic source layer activates only for School/WTT/Reading area topics
- ISC-18: NotebookLM is NOT called at any point in the automated pipeline

### Phase 2.8
- ISC-19: New skill created via single command with all schema fields populated
- ISC-20: Initial research job produces full staged roadmap with Learn/Apply/Observe/Mentor per stage
- ISC-21: Stage advancement marks stage complete, advances current stage, triggers focused research
- ISC-22: Opportunities DB replaced (not appended) on each research cycle
- ISC-23: Practice Log entries created only for High priority skills during nightly check-in
- ISC-24: High priority skills cold for 14+ days flagged in morning briefing
- ISC-25: Monthly refresh runs only for High priority skills, skips Medium and Low
- ISC-26: New skill addable end-to-end (page + research + roadmap) in under 2 minutes

---

## Files Created by These Phases

```
~/Jade/
├── integrations/
│   ├── jade_notion.py        ← Task + Project + Skill CRUD (Phase 2.5, 2.6, 2.8)
│   └── jade_research.py      ← Research pipeline (Phase 2.7 + skill research jobs)
├── docs/features/
│   ├── phase2.5-spec.md
│   ├── phase2.6-spec.md
│   ├── phase2.7-spec.md
│   └── phase2.8-spec.md
└── memory/
    └── notion_ids.json       ← All DB IDs cached after workspace setup
```

### Credentials Needed (add to ~/.config/jade/)
```
NOTION_API_KEY             ← From Notion integration settings
NOTION_TASKS_DB_ID         ← After Tasks DB created
NOTION_PROJECTS_DB_ID      ← After Projects DB created
NOTION_RESEARCH_DB_ID      ← After Research Vault created
NOTION_SKILLS_DB_ID        ← After Skills DB created
NOTION_PRACTICE_LOG_DB_ID  ← After Practice Log DB created
NOTION_OPPORTUNITIES_DB_ID ← After Opportunities DB created
PERPLEXITY_API_KEY         ← For Deep Research source finding (Phase 2.7 + 2.8)
```

---

## Gray Areas Resolved

| Gray Area | Decision |
|-----------|----------|
| One DB per area vs. one DB with filters | One master DB + filtered views. Jade queries one place. |
| Skills: filtered view vs own DB | Own DB — schema is fundamentally different from Projects/Tasks |
| NotebookLM as automated pipeline | Ruled out — wrong tool for source discovery, no official API, browser automation fragility. Stays as manual companion for document-heavy deep dives. |
| Synthesis engine for research | Claude Haiku — already in JADE, no new model dependency needed |
| Status field on tasks vs projects | Both have Status — different values, not shared |
| Who creates the Notion workspace? | Manual one-time setup by Spencer, then Jade manages via API |
| Recurring tasks: create all instances upfront or on-demand? | Create all upfront — visible in calendar view, easier to track |
| Research confidence level | Jade self-rates based on source quality + consensus |
| Opportunities DB: append vs replace | Replace — Jade keeps 3–5 best current options, no graveyard of stale links |
| Practice Log: all skills vs selective | High priority skills only, prompted by Jade in nightly check-in, two fields max |
| Skill research refresh cadence | Monthly for High priority only — conserves Perplexity API costs |

---

*This spec is the source of truth for Phases 2.5, 2.6, 2.7, and 2.8.*
*Do not begin Phase 2.6 until Phase 2.5 ISC criteria all pass.*
*Do not begin Phase 2.7 until Phase 2.6 ISC criteria all pass.*
*Do not begin Phase 2.8 until Phase 2.7 ISC criteria all pass.*

