#!/usr/bin/env python3
"""
scripts/check_doc_staleness.py

Nightly doc staleness check — runs at 10pm via launchd.
Fires regardless of how the Claude Code session ended (explicit exit,
terminal close, machine sleep, inactivity timeout).

Checks that key docs were updated today. If stale, sends a macOS
notification and appends a warning to logs/staleness.log.

This protects the self-improving loop from silent failure — stale
PROJECT_STATUS.md or CHANGELOG.md means /goal-review and /retro
reason from outdated context.

Triggered by: ~/Library/LaunchAgents/com.jade.doc-check.plist
Logs to: ~/Jade/logs/doc_check.log
         ~/Jade/logs/doc_check_error.log
"""

import sys
import subprocess
from datetime import date, datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

JADE_DIR = Path("/Users/spencerhatch/Jade")
LOG_FILE  = JADE_DIR / "logs/doc_check.log"
STALE_LOG = JADE_DIR / "logs/staleness.log"

# Files that must be touched on any day a dev session occurred.
# We detect dev sessions by checking if any .py file was modified today.
DEV_SESSION_INDICATORS = [
    "jade_briefing.py",
    "jade_timeblock.py",
    "jade_router.py",
    "jade_prompts.py",
    "jade_nightly.py",
]

REQUIRED_FRESH_ON_DEV = [
    "docs/PROJECT_STATUS.md",
    "docs/CHANGELOG.md",
]

# These must always be fresh regardless of dev activity — briefing script
# touches them every morning, so staleness here means the briefing itself failed.
ALWAYS_CHECK = [
    ("logs/briefing.log", 1),   # (path, max_days_stale)
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")

def notify(title: str, message: str):
    """Send macOS notification via terminal-notifier."""
    try:
        subprocess.run(
            ["/opt/homebrew/bin/terminal-notifier",
             "-title", title,
             "-message", message,
             "-sound", "default",
             "-group", "jade-doc-check"],
            timeout=5,
            capture_output=True
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # terminal-notifier not installed or timed out — log only
        log(f"[notify fallback] {title}: {message}")

def days_since_modified(path: Path) -> float:
    """Returns days since file was last modified. Returns 999 if file missing."""
    if not path.exists():
        return 999.0
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.now() - mtime).total_seconds() / 86400

def dev_session_occurred_today() -> bool:
    """
    Returns True if any dev session indicator file was modified today.
    This prevents false alarms on days Spencer didn't open Claude Code at all.
    """
    today = date.today()
    for rel_path in DEV_SESSION_INDICATORS:
        full_path = JADE_DIR / rel_path
        if full_path.exists():
            mtime = date.fromtimestamp(full_path.stat().st_mtime)
            if mtime == today:
                return True

    # Also check git log for any commits today
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--since=midnight"],
            cwd=str(JADE_DIR),
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout.strip():
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return False

# ── Main check ────────────────────────────────────────────────────────────────

def run():
    today = date.today()
    issues = []

    # 1. Check if a dev session occurred today
    had_dev_session = dev_session_occurred_today()

    # 2. If yes, verify required docs were updated
    if had_dev_session:
        for rel_path in REQUIRED_FRESH_ON_DEV:
            full_path = JADE_DIR / rel_path
            if not full_path.exists():
                issues.append(f"MISSING: {rel_path}")
                continue
            mtime = date.fromtimestamp(full_path.stat().st_mtime)
            if mtime < today:
                days = days_since_modified(full_path)
                issues.append(
                    f"STALE: {rel_path} — last updated {mtime} "
                    f"({days:.0f}d ago). Run /update-docs."
                )

    # 3. Always check briefing log freshness
    for rel_path, max_days in ALWAYS_CHECK:
        full_path = JADE_DIR / rel_path
        days = days_since_modified(full_path)
        if days > max_days:
            if not full_path.exists():
                issues.append(f"MISSING: {rel_path} — briefing may not be configured yet")
            else:
                issues.append(
                    f"BRIEFING GAP: {rel_path} — last entry {days:.0f}d ago. "
                    f"Check launchd plist and briefing_error.log."
                )

    # 4. Report
    if issues:
        # Write to staleness log
        STALE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(STALE_LOG, "a") as f:
            f.write(f"\n[{today}] STALENESS DETECTED:\n")
            for issue in issues:
                f.write(f"  • {issue}\n")

        # Notify Spencer
        count = len(issues)
        summary = issues[0].split("—")[0].strip() if issues else ""
        notify(
            title="Jade — Doc Check",
            message=f"{count} stale item{'s' if count > 1 else ''}. {summary}"
        )
        log(f"STALE: {count} issues found — notification sent")
        for issue in issues:
            log(f"  {issue}")

    else:
        if had_dev_session:
            log("OK: dev session detected, all docs current")
        else:
            log("OK: no dev session today, skipping doc check")

    return len(issues)

if __name__ == "__main__":
    exit_code = run()
    sys.exit(0)  # always exit 0 — this is a monitor, not a blocker
