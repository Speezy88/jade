# /approve
# Place at: ~/Jade/.claude/commands/approve.md
# Usage: /approve  OR  /approve goals  OR  /approve steering
# Tier 1 use — Spencer runs this when Jade has proposed changes

Review and approve Jade's proposed changes to goal files, steering rules, or SOUL.md.
Jade proposes. Spencer approves. Nothing gets committed without this step.

---

## WHAT GETS APPROVED HERE

Three categories of proposed changes:

**1. Goal file updates** (`memory/goals/`)
When Jade proposes updates to PLAN.md files or ACTIVE_GOALS.md.
Proposed files are saved as `*.proposed.md` alongside the original.

**2. AI Steering Rule additions** (`AI_STEERING_RULES.md`)
When the promotion rule triggers (error pattern ≥3 times, ≥2 tasks, 30 days).
Proposed rules are staged but not written until approved here.

**3. SOUL.md adjustments**
When the goal-review-agent identifies a behavioral pattern that warrants a trait adjustment
or a new standing instruction.

---

## EXECUTION SEQUENCE

**1. Scan for pending items.**
```bash
# Proposed goal files
find memory/goals/ -name "*.proposed.md"

# Proposed steering rules
cat .learnings/PENDING_RULES.md  # if it exists

# Proposed SOUL.md changes
cat .learnings/PENDING_SOUL.md   # if it exists
```

If nothing pending, report: "No pending approvals." and stop.

**2. For each pending item, present a diff.**
Show the current version alongside the proposed change.
Format:
```
PROPOSED CHANGE: memory/goals/college_app/PLAN.md
────────────────────────────────────────
CURRENT:
[current content of the relevant section]

PROPOSED:
[proposed content]

REASON: [why Jade is proposing this — source signal, pattern, or explicit request]
────────────────────────────────────────
Approve? [yes / edit / reject]
```

**3. Handle Spencer's response:**
- `yes` → overwrite the current file with the proposed version, delete the `.proposed.md`
- `edit` → open the proposed file for Spencer to modify, then re-present for approval
- `reject` → delete the `.proposed.md`, log the rejection to `.learnings/ERRORS.md` with reason if provided

**4. For AI Steering Rules specifically:**
After approval, append to the USER section of `AI_STEERING_RULES.md` and update the Promotion Log table.
After rejection, note the rejected rule in the Promotion Log with status "rejected" — prevents the same rule from being re-proposed for 60 days.

**5. Confirm what was committed:**
```
Approved and committed:
  ✓ memory/goals/college_app/PLAN.md updated
  ✓ AI Steering Rule added: "Always verify Schoology cache is fresh before briefing"
```

---

## WHAT /approve NEVER DOES
- Does not approve changes it didn't propose — only processes items in the pending queue
- Does not modify CLAUDE.md directly (that goes through component edit + assemble_claude.py)
- Does not approve and commit in the same step without showing Spencer the diff first
