# /update-docs
# Place at: ~/Jade/.claude/commands/update-docs.md
# Usage: /update-docs  OR  /update-docs "phase 1 briefing complete"
# Tier 2 use — run after every completed feature

Sync all automated documentation with the current state of the codebase.
Required before session close. The stop_hook enforces this.

---

## EXECUTION SEQUENCE

**1. Determine what changed.**
```bash
git diff HEAD --name-only        # uncommitted changes
git log --oneline -10            # recent commits
```
Build a list of: which files changed, which phase they belong to, what functionality was added.

**2. Update `docs/ARCHITECTURE.md`.**
Check each changed file against the current ARCHITECTURE.md:
- Is the file documented in the File Responsibilities table?
- Are its data flows described?
- Did any component interactions change?

Add or update only the sections that were affected. Do not rewrite sections that weren't touched.
Run `scripts/assemble_claude.py` if any component in `components/` was modified.

**3. Update `docs/CHANGELOG.md`.**
Add a new entry at the top:
```markdown
## YYYY-MM-DD — [commit message or brief description]
[2-3 sentences: what was built, why it matters, any architectural implications]
Files changed: [list]
```
If `scripts/smart_changelog.py` already wrote an entry for this commit, verify it's accurate — edit if not, don't duplicate.

**4. Update `docs/PROJECT_STATUS.md`.**
- Move any completed items from "Not Yet Built" to a "Completed" section
- Update the phase milestone table status
- Update "Where to start next session" to reflect the actual next step
- Resolve any "Known Gaps" that were addressed in this session
- Update hardware or infrastructure notes if anything changed

**5. Update relevant `docs/features/` files.**
For each major integration or feature that was built or significantly changed:
- `docs/features/briefing.md` — if jade_briefing.py was touched
- `docs/features/gcal_integration.md` — if gcal.py was touched
- `docs/features/schoology.md` — if schoology.py was touched
- `docs/features/routing.md` — if jade_router.py was touched
- `docs/features/time_model.md` — if time model files were touched
- `docs/features/meeting_notes.md` — if meeting integration was touched
Create new feature files for any feature not yet documented.

**6. Commit the doc changes.**
```bash
git add docs/
git commit -m "docs: sync documentation after [brief description]"
```

**7. Confirm.**
Report what was updated:
```
/update-docs complete:
  ✓ ARCHITECTURE.md — added [component]
  ✓ CHANGELOG.md — new entry
  ✓ PROJECT_STATUS.md — phase 1 marked complete, phase 2 set as current
  ✓ docs/features/briefing.md — created
```

---

## WHAT /update-docs NEVER DOES
- Does not modify SOUL.md, AGENTS.md, AI_STEERING_RULES.md, or CLAUDE.md directly
- Does not create documentation for work that wasn't actually completed
- Does not duplicate CHANGELOG entries already written by smart_changelog.py
- Does not rewrite architecture sections for components that weren't changed
