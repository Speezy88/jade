# /retro
# Place at: ~/Jade/.claude/commands/retro.md
# Usage: /retro
# Tier 2 use — run at the end of every dev session

End-of-session reflection and self-improving loop.
Captures what worked, what didn't, and whether any patterns qualify for promotion.

---

## EXECUTION SEQUENCE

**1. Classify the session.**
Read the session's prompts and outputs to determine mode:
- **FULL** — new feature built, algorithm ran, ISC written and verified
- **ITERATION** — existing feature modified, no new ISC needed
- **MINIMAL** — config changes, doc updates, quick fixes only

**2. Read session context.**
```bash
git diff HEAD --name-only       # what files changed this session
git log --oneline -5            # recent commits
```

**3. Generate the retro.**

Format:
```
SESSION RETRO — [date]
━━━━━━━━━━━━━━━━━━━━━━

Mode: [FULL / ITERATION / MINIMAL]
Duration: [estimated from time model if logged, otherwise ask]
Phase: [which build phase this session worked on]

WHAT WORKED
[Specific things that went smoothly — not generic praise]

WHAT DIDN'T
[Specific friction points, wrong turns, time sinks]

PATTERNS TO WATCH
[Any behavior matching Spencer's known friction patterns?
 Reference SOUL.md friction list. Be specific.]

ALGORITHM CHECK
[Did the session follow OBSERVE→THINK→PLAN→BUILD→EXECUTE→VERIFY→LEARN?
 If any step was skipped, name it.]
```

**4. Check the promotion rule.**
Scan `memory/LEARNING/SIGNALS/ratings.jsonl` and `memory/LEARNING/FAILURES/` for:
- Any error pattern with ≥3 occurrences
- Across ≥2 distinct tasks
- Within the last 30 days

If a pattern qualifies, write the proposed rule to `.learnings/PENDING_RULES.md`.
Do not write it to `AI_STEERING_RULES.md` directly — that requires `/approve`.

**5. Propose component updates if warranted.**
If the session revealed that any `components/` file is outdated or inaccurate,
write the proposed update to a `.proposed.md` file alongside the original.
Never auto-commit component changes.

**6. Prompt for session rating.**
End with:
```
Rate this session 1–10. Captured automatically when you reply.
```

**7. Remind Spencer what's next.**
Pull the "Where to start next session" line from `docs/PROJECT_STATUS.md`.
Surface it as the closing line.

---

## WHAT /retro NEVER DOES
- Does not write to AI_STEERING_RULES.md, SOUL.md, or AGENTS.md directly
- Does not mark a phase complete — that requires /arch-review first
- Does not skip the promotion rule check, even on MINIMAL sessions
- Does not pad the retro with motivational language
