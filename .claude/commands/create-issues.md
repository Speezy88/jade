# /create-issues
# Place at: ~/Jade/.claude/commands/create-issues.md
# Usage: /create-issues  OR  /create-issues phase1  OR  /create-issues path/to/spec.md
# Tier 3 use — run at phase kickoff

Convert a phase spec or milestone table into tracked GitHub issues.
GitHub issues become the source of truth. Not to-do files. Not conversation history.

---

## PREREQUISITES
GitHub CLI installed and authenticated:
```bash
gh --version          # verify installed
gh auth status        # verify authenticated
gh repo view          # verify you're in the right repo
```
If any fail, stop and fix before proceeding.

---

## ARGUMENT HANDLING
- No argument → use the BUILD PHASES table from CLAUDE.md
- `phase1` / `phase2` etc. → scope to that phase only
- File path → read that file as the spec source

---

## EXECUTION SEQUENCE

**1. Read the source spec.**

**2. Decompose into discrete issues.**
Each issue must be:
- One independently completable deliverable (not a whole phase)
- Specific enough that done/not-done is unambiguous in under 5 seconds
- Sized for one focused session (≤4 hours of work)
- If a task would take more than one session, split it

**3. For each issue, create it via GitHub CLI:**
```bash
gh issue create \
  --title "[Phase X] Descriptive title" \
  --body "## What This Is
[1-2 sentence description of the deliverable]

## Ideal State Criteria
- [ ] [Binary, testable criterion — state not action]
- [ ] [Binary, testable criterion]
- [ ] [Binary, testable criterion]

## Dependencies
[Issues that must close first, or 'None']

## Estimated Time
[estimated session time based on time model, or 'unknown']

## Notes
[Any gotchas from TOOLS.md relevant to this issue]" \
  --label "phase-X"
```

**4. Label conventions:**
- `phase-1` through `phase-10` — build phases
- `time-model` — task duration intelligence features
- `meeting-notes` — meeting note taker features
- `bug` — discovered defects
- `enhancement` — improvements to existing features
- `blocked` — waiting on another issue or external dependency
- `needs-approval` — requires Spencer's review before work begins

**5. After creating all issues:**
```bash
gh issue list --label "phase-X"    # verify they were created
```

**6. Update PROJECT_STATUS.md.**
Add the issue numbers to the phase milestone table.
Format: `Phase 1 | Morning briefing | 🔨 Current | #1, #2, #3`

**7. Confirm the result.**
```
Created 6 issues for Phase 1:
  #1 — [Phase 1] Set up jade_prompts.py and build_system_prompt()
  #2 — [Phase 1] Build integrations/gcal.py with OAuth
  #3 — [Phase 1] Build integrations/schoology.py with .ics cache
  #4 — [Phase 1] Wire jade_briefing.py with live data
  #5 — [Phase 1] Configure launchd plist and test scheduling
  #6 — [Phase 1] 3-day briefing pilot and rating baseline
```

---

## ISSUE SIZING RULE
If Spencer couldn't close an issue in one 2-3 hour session, split it.
Over-sized issues are the most common reason work stalls — they feel too big to start.
