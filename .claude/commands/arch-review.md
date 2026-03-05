# /arch-review
# Place at: ~/Jade/.claude/commands/arch-review.md
# Usage: /arch-review
# Tier 3 use — run before marking any phase complete

Pre-phase-close architecture verification.
Confirms code matches documented architecture. Catches drift before it accumulates.

---

## EXECUTION SEQUENCE

**1. Get the list of files changed in this phase.**
```bash
git diff main --name-only         # all changes since branching from main
git log --oneline main..HEAD      # commits in this branch
```

**2. Read current ARCHITECTURE.md.**

**3. Check each changed file against documentation.**

For each new or significantly modified file, verify:
- Is it listed in the File Responsibilities table?
- Are its inputs and outputs described?
- Are its connections to other components documented?
- If it introduces a new data flow, is that flow in the architecture diagram?

**4. Check for undocumented components.**
```bash
# Find Python files not mentioned in ARCHITECTURE.md
python_files=$(find . -name "*.py" -not -path "./.git/*" -not -path "./scripts/*")
for f in $python_files; do
    basename=$(basename $f)
    if ! grep -q "$basename" docs/ARCHITECTURE.md; then
        echo "UNDOCUMENTED: $f"
    fi
done
```

**5. Check for documented components that no longer exist.**
Scan ARCHITECTURE.md for file references. Verify each file still exists.
Report any documented files that are missing.

**6. Check ISC completion.**
For the current phase's WORK directory:
```bash
cat memory/WORK/[current-task]/ISC.json
```
Verify every criterion has evidence in `memory/WORK/[current-task]/verification/`.
If any criterion lacks evidence, block phase close.

**7. Generate the review report.**
```
ARCH REVIEW — Phase [X]
━━━━━━━━━━━━━━━━━━━━━━━

DOCUMENTATION GAPS (must fix before phase close):
  ⚠ jade_router.py — not in File Responsibilities table
  ⚠ New data flow: gcal.py → jade_briefing.py — not in architecture diagram

DOCUMENTATION VERIFIED:
  ✓ jade_briefing.py — documented
  ✓ integrations/gcal.py — documented
  ✓ integrations/schoology.py — documented

ISC VERIFICATION:
  ✓ jade_briefing.py runs without errors (evidence: logs/briefing.log)
  ✓ Live calendar data in output (evidence: verification/gcal_test.txt)
  ⚠ launchd fires at 7am — no evidence yet (needs overnight test)

VERDICT: NOT READY TO CLOSE — 3 items need resolution
```

**8. If gaps exist:**
Propose the specific ARCHITECTURE.md additions needed.
Present to Spencer for approval — do not auto-write to ARCHITECTURE.md.

**9. If all clear:**
```
ARCH REVIEW PASSED — Phase [X] ready to close.
Next: run /update-docs, then merge to main.
```

---

## ROUTE
This command uses the `arch-review-agent` sub-agent.
Route to: ROG Tier 2 (deepseek-r1:14b) — reasoning over code structure required.
