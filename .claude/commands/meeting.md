# /meeting
# Place at: ~/Jade/.claude/commands/meeting.md
# Usage: /meeting path/to/audio.mp3  OR  /meeting path/to/audio.mp3 "Wellbeing weekly sync"
# Tier 2 use — Spencer runs this after any recorded meeting

Process a meeting recording into structured notes, action items, and an executable plan.

---

## PREREQUISITES

Whisper must be installed: `pip install openai-whisper`
For live system audio capture: `brew install blackhole-2ch ffmpeg`

---

## ARGUMENT PARSING

- **audio_path** (required) — path to .mp3, .m4a, .wav, or .mp4 file
- **meeting_context** (optional) — brief description of who/what the meeting was about

If no audio path is provided, check `~/Desktop/` and `~/Downloads/` for audio files modified in the last 2 hours. If exactly one is found, use it and confirm with Spencer before proceeding.

---

## EXECUTION SEQUENCE

**1. Validate the file.**
```python
from pathlib import Path
path = Path(audio_path)
assert path.exists(), f"File not found: {audio_path}"
assert path.suffix.lower() in [".mp3", ".m4a", ".wav", ".mp4", ".webm"]
```

**2. Generate a meeting ID.**
Format: `YYYYMMDD-[slug-from-context-or-filename]`
Example: `20260304-wellbeing-weekly`

**3. Create the meeting directory.**
```bash
mkdir -p memory/meetings/[meeting_id]/
cp [audio_path] memory/meetings/[meeting_id]/audio[ext]
```

**4. Transcribe with local Whisper.**
Audio never leaves the machine. Transcription is entirely local.
```python
import whisper
model = whisper.load_model("small")   # "small" balances speed and accuracy
result = model.transcribe(str(audio_path))
transcript = result["text"]

# Save raw transcript
Path(f"memory/meetings/{meeting_id}/transcript.txt").write_text(transcript)
```
Report progress: "Transcribing... [duration] of audio"

**5. Extract structure via Claude Haiku.**
```python
prompt = f"""Meeting context: {meeting_context or "not provided"}

Transcript:
{transcript[:8000]}

Return valid JSON only — no preamble, no markdown fences:
{{
  "summary": "2-3 sentence meeting summary",
  "participants": ["name or role"],
  "decisions": ["decision made"],
  "action_items": [
    {{
      "task": "specific task",
      "owner": "person responsible",
      "deadline": "YYYY-MM-DD or relative like 'by Friday'",
      "priority": "high|medium|low",
      "estimated_minutes": null
    }}
  ],
  "open_questions": ["unresolved items"],
  "suggested_calendar_blocks": [
    {{
      "task": "calendar event title",
      "estimated_minutes": 45,
      "suggested_window": "morning|afternoon|evening|flexible",
      "deadline_pressure": "high|medium|low"
    }}
  ]
}}"""
```

Save structured output to `memory/meetings/[meeting_id]/notes.json`.

**6. Cross-reference time model.**
For each action item with `estimated_minutes: null`, check `memory/time_model/model.json`
and fill in the estimate if a matching task_type exists.
Note the source: `"estimated_minutes": 45, "estimate_source": "personal_median_8_samples"`

**7. Generate execution plan.**
Create `memory/meetings/[meeting_id]/execution_plan.md`:
```markdown
# Execution Plan — [meeting_id]
Generated: [date] | Pending Spencer approval

## Summary
[meeting summary]

## Action Items
| Task | Owner | Deadline | Est. Time | Priority |
|------|-------|----------|-----------|----------|
| ...  | ...   | ...      | ...       | ...      |

## Proposed Calendar Blocks
[list of suggested time blocks with rationale]

## Open Questions to Resolve
[list]
```

**8. Present to Spencer.**
Show the summary and action item table.
Ask: "Add these action items to your task queue and propose calendar blocks? [yes / adjust / skip]"

If yes → save to `memory/WORK/` as open tasks, run `/timeblock` logic to propose calendar blocks
If adjust → Spencer edits, then commit
If skip → execution plan saved but nothing added to queue

**9. Surface in future briefings.**
Action items from approved meeting plans are automatically included in `/brief` output
when their deadline is within 48h or they are marked high priority.

---

## WHAT /meeting NEVER DOES
- Does not send audio to any external service
- Does not transcribe without local Whisper installed
- Does not add calendar blocks without Spencer's explicit approval
- Does not fabricate action items — if the transcript is unclear, notes the ambiguity
