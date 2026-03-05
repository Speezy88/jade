# /brief
# Place at: ~/Jade/.claude/commands/brief.md
# Usage: /brief  OR  /brief afternoon  OR  /brief "3pm-6pm"
# Tier 1 use — Spencer types this daily

Manually trigger a Jade morning briefing for the current moment.
Accepts an optional time window argument (e.g., "afternoon", "3pm-6pm", "evening").

---

## EXECUTION SEQUENCE

**1. Detect mode from argument.**
- No argument → full day briefing (same as scheduled 7am run)
- Time argument → briefing scoped to that window only

**2. Fetch live data. Do not proceed without it.**
Run both of these before generating any content:
```bash
python integrations/gcal.py --hours 24        # fetch today's calendar events
python integrations/schoology.py --refresh    # refresh assignment cache if >6h stale
```
If either fetch fails, report the failure explicitly. Do not substitute assumed data.

**3. Read current context.**
- `memory/goals/ACTIVE_GOALS.md`
- `memory/time_model/model.json` (if it exists — use for window estimates)
- Any open items from `memory/WORK/` with today's deadline

**4. Generate briefing following SOUL.md specification.**

Required components in order:
1. **Situational read** — one honest line about today's shape (schedule density, energy demands, competing priorities)
2. **Available work windows** — derived strictly from live calendar data, with duration in minutes
3. **Top 3 priorities** — ranked by urgency × stakes. Reference active goals, not generic advice.
4. **High-stakes callout** — one specific item from college app, ACT prep, internship, or Jade build
5. **Closing line** — one specific, forward-moving action. Not a motivational phrase.

**5. If time model data exists**, annotate work windows with realistic estimates:
- "45-min window → sufficient for a problem set (median 38 min)" ✓
- "20-min window → not enough for essay drafting (median 68 min)" ✗

**6. Do not ask Spencer questions after delivering the briefing.**
The briefing is a delivery, not a conversation opener.

---

## TONE REFERENCE
Direct. Tight. No filler. The output of someone who has already read the calendar and has 60 seconds to tell Spencer what actually matters.
See full specification → `SOUL.md § Briefing Specification`
