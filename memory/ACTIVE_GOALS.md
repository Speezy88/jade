# ACTIVE_GOALS.md
*Injected into every prompt via build_system_prompt(). Spencer's live goal state.*
*Update when deadlines change, progress is made, or priorities shift.*
*Last updated: 2026-03-05*

---

## 1. College Application — Fall 2026

**List (in progress — not fully locked):**

| Tier | Schools |
|------|---------|
| Hard Reach (1–2) | UPenn, Boston University |
| Reach (1–3) | UW Seattle, U Michigan, NYU Stern, Northwestern, USC |
| Target (1–3) | Arizona State, U Arizona, Babson, Indiana, Colorado Boulder |
| Likely (1–2) | Fordham, Lehigh, Santa Clara, Loyola Marymount |
| UC Schools | UCB, UCLA, UCSB, UCI, UC Davis |

**Key dates:**
- Common App opens: August 1, 2026
- EA/ED deadlines: November 2026 (varies by school)

**Current status:** In research phase. List not fully concrete. No essays started.

**Biggest gap:** Needs a high-impact, out-of-the-box community service project that stands out. This is the single most important thing missing from the application right now.

---

## 2. ACT — Target 32+ Math, 32+ Science

| Section | Current | Target | Gap |
|---------|---------|--------|-----|
| English | 35 | 35 | ✓ |
| Reading | 32 | 32 | ✓ |
| Math | 27 | 32 | -5 |
| Science | 28 | 32 | -4 |
| **Composite** | **30.5** | **32+** | |

**Next test date:** April 14, 2026 — 40 days out
**Weekly prep commitment:** 30 minutes/day
**Current streak:** 0 sessions

**Priority:** Math and Science only. English and Reading are done.

---

## 3. Wellbeing Think Tank Internship

**Boss:** Chase Sterling

**Active workstreams:**
- CRM UI — next deliverable, update in progress
- Membership rollout — user experience design
- Social Media — ongoing

**Next deliverable:** Updated CRM UI

---

## 4. Jade Build

**Current phase:** Phase 1 — Morning Briefing
**Next milestone:** `jade_briefing.py` running via launchd at 7am

**Build sequence:**
1. ACTIVE_GOALS.md ← you are here
2. `jade_prompts.py` — `build_system_prompt()`
3. `integrations/weather.py` — OpenWeatherMap
4. Google Calendar OAuth — browser auth on Mac
5. `integrations/gcal.py` — read-only
6. `integrations/schoology.py` — ICS + cache
7. `jade_briefing.py` — wire everything
8. Test manually, verify ISC, load launchd plist

**Hard blockers:**
- Google Calendar OAuth requires Mac + browser (cannot do on Windows)
- `OPENWEATHERMAP_API_KEY` needed — register at openweathermap.org (free)

**Phase 1.5 (next):** Nightly briefing — `jade_nightly.py`, interactive check-in
