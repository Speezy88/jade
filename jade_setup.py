#!/usr/bin/env python3
"""
jade_setup.py

One-time Notion workspace setup — creates all 6 databases with correct schemas
under Spencer's Workspace. Writes DB IDs to memory/notion_ids.json.

Usage:
  python3 jade_setup.py           # create workspace (aborts if notion_ids.json exists)
  python3 jade_setup.py --force   # overwrite existing workspace
  python3 jade_setup.py --check   # validate existing workspace + relations

Pre-run:
  1. Create a Notion integration at notion.so/my-integrations
  2. Create a blank page named "Spencer's Workspace" and share it with the integration
  3. Add to ~/.config/jade/credentials:
       NOTION_API_KEY=secret_xxx
       NOTION_PARENT_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import ssl
import urllib.error
import urllib.request

# Python.org Python on macOS ships without root certs installed.
# Fix properly with: /Applications/Python\ 3.13/Install\ Certificates.command
# Until then, skip verification for connections to known Notion endpoints.
_SSL_CTX = ssl._create_unverified_context()


def _extract_notion_id(value: str) -> str:
    """
    Accepts a Notion page ID in any of these formats and returns a clean UUID:
      - Full URL: https://www.notion.so/Page-Name-33ee0769306080bb8d24d9ed22a4b642
      - Raw 32-char hex: 33ee0769306080bb8d24d9ed22a4b642
      - UUID with dashes: 33ee0769-3060-80bb-8d24-d9ed22a4b642
    """
    # Strip query string
    value = value.split("?")[0].strip()
    # Extract 32-char hex run (with or without dashes)
    hex_run = re.search(r"([0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12})", value)
    if hex_run:
        return hex_run.group(1)
    # Fallback: last 32 contiguous hex chars in the string
    plain = re.search(r"([0-9a-f]{32})(?:[^0-9a-f]|$)", value)
    if plain:
        raw = plain.group(1)
        return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
    raise ValueError(f"Could not extract a Notion page ID from: {value!r}")

_JADE_DIR       = Path("/Users/spencerhatch/Jade")
_NOTION_IDS     = _JADE_DIR / "memory" / "notion_ids.json"
_CREDS_PATH     = Path.home() / ".config" / "jade" / "credentials"
_NOTION_VERSION = "2022-06-28"
_API_BASE       = "https://api.notion.com/v1"

# Expected relations for --check validation: db_key → {property_name → target_db_key}
_EXPECTED_RELATIONS = {
    "tasks_db_id":        {"Linked Project":  "projects_db_id"},
    "research_db_id":     {"Linked Project":  "projects_db_id"},
    "skills_db_id":       {"Linked Projects": "projects_db_id",
                           "Linked Research": "research_db_id"},
    "practice_log_db_id": {"Skill":           "skills_db_id"},
    "opportunities_db_id":{"Skill":           "skills_db_id"},
}

_DB_DISPLAY_NAMES = {
    "projects_db_id":     "Projects",
    "tasks_db_id":        "Tasks",
    "research_db_id":     "Research Vault",
    "skills_db_id":       "Skills",
    "practice_log_db_id": "Practice Log",
    "opportunities_db_id":"Opportunities",
}


# ── Credentials ───────────────────────────────────────────────────────────────

def _load_credentials() -> dict:
    if not _CREDS_PATH.exists():
        print(
            f"\n[jade_setup] ERROR: Credentials file not found at {_CREDS_PATH}\n"
            "Add to that file:\n"
            "  NOTION_API_KEY=secret_xxx\n"
            "  NOTION_PARENT_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n",
            file=sys.stderr,
        )
        sys.exit(1)

    creds: dict[str, str] = {}
    for line in _CREDS_PATH.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, _, val = line.partition("=")
            creds[key.strip()] = val.strip()

    missing = [k for k in ("NOTION_API_KEY", "NOTION_PARENT_PAGE_ID") if k not in creds]
    if missing:
        print(
            f"\n[jade_setup] ERROR: Missing keys in {_CREDS_PATH}: {', '.join(missing)}\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Normalise — accept full Notion URLs as well as raw IDs
    try:
        creds["NOTION_PARENT_PAGE_ID"] = _extract_notion_id(creds["NOTION_PARENT_PAGE_ID"])
    except ValueError as e:
        print(f"\n[jade_setup] ERROR: {e}\n", file=sys.stderr)
        sys.exit(1)

    return creds


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _headers(api_key: str) -> dict:
    return {
        "Authorization":  f"Bearer {api_key}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type":   "application/json",
    }


def _notion_get(endpoint: str, api_key: str) -> dict:
    req = urllib.request.Request(
        f"{_API_BASE}/{endpoint}",
        headers=_headers(api_key),
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GET {endpoint} → {e.code}: {e.read().decode()}")


def _notion_post(endpoint: str, payload: dict, api_key: str) -> dict:
    req = urllib.request.Request(
        f"{_API_BASE}/{endpoint}",
        data=json.dumps(payload).encode(),
        headers=_headers(api_key),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"POST {endpoint} → {e.code}: {e.read().decode()}")


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_key(api_key: str) -> None:
    try:
        _notion_get("users/me", api_key)
        print("[jade_setup] API key valid ✓")
    except RuntimeError as e:
        print(f"\n[jade_setup] ERROR: {e}\n", file=sys.stderr)
        sys.exit(1)


# ── Shared option sets ────────────────────────────────────────────────────────

_AREA_OPTIONS = [
    {"name": "School/ACT/College Apps", "color": "blue"},
    {"name": "Wellbeing Think Tank",    "color": "green"},
    {"name": "Personal Goals",          "color": "purple"},
    {"name": "Side Projects/Business",  "color": "orange"},
    {"name": "Reading/Learning",        "color": "yellow"},
]

_PRIORITY_OPTIONS = [
    {"name": "🔴 High",   "color": "red"},
    {"name": "🟡 Medium", "color": "yellow"},
    {"name": "🟢 Low",    "color": "green"},
]


def _rel(db_id: str) -> dict:
    """One-way relation property schema."""
    return {
        "relation": {
            "database_id":   db_id,
            "type":          "single_property",
            "single_property": {},
        }
    }


# ── Property schema builders ──────────────────────────────────────────────────

def _build_projects_properties() -> dict:
    return {
        "Project Name":   {"title": {}},
        "One-Line Goal":  {"rich_text": {}},
        "Why It Matters": {"rich_text": {}},
        "Area":           {"select": {"options": _AREA_OPTIONS}},
        "Status":         {"select": {"options": [
            {"name": "🔲 Not Started", "color": "default"},
            {"name": "🔄 Active",      "color": "blue"},
            {"name": "🚧 Blocked",     "color": "red"},
            {"name": "✅ Done",        "color": "green"},
        ]}},
        "Deadline":       {"date": {}},
        "Deadline Type":  {"select": {"options": [
            {"name": "Hard",   "color": "red"},
            {"name": "Target", "color": "yellow"},
        ]}},
        "Time Budget":    {"number": {"format": "number"}},
        "Owner":          {"people": {}},
        "Collaborators":  {"people": {}},
        # Progress % requires a formula referencing Linked Tasks — add manually
        # in Notion UI after the Tasks → Projects relation is live.
    }


def _build_tasks_properties(projects_db_id: str) -> dict:
    return {
        "Task Name":          {"title": {}},
        "Area":               {"select": {"options": _AREA_OPTIONS}},
        "Priority":           {"select": {"options": _PRIORITY_OPTIONS}},
        "Due Date":           {"date": {}},
        "Energy":             {"select": {"options": [
            {"name": "🔵 Deep Work",  "color": "blue"},
            {"name": "⚡ Light Work", "color": "yellow"},
        ]}},
        "Estimated Duration": {"number": {"format": "number"}},
        "Linked Project":     _rel(projects_db_id),
        "Recurring":          {"checkbox": {}},
        "Recurrence Type":    {"select": {"options": [
            {"name": "Daily chunk", "color": "blue"},
            {"name": "Weekly",      "color": "green"},
            {"name": "Custom",      "color": "gray"},
        ]}},
        "Total Target":       {"number": {"format": "number"}},
        "Chunk Size":         {"number": {"format": "number"}},
        "Recurrence Start":   {"date": {}},
        "Recurrence End":     {"date": {}},
        "Status":             {"select": {"options": [
            {"name": "Not Started", "color": "default"},
            {"name": "In Progress", "color": "blue"},
            {"name": "Done",        "color": "green"},
            {"name": "Skipped",     "color": "gray"},
        ]}},
        "Notes":              {"rich_text": {}},
    }


def _build_research_properties(projects_db_id: str) -> dict:
    return {
        "Research Title": {"title": {}},
        "Query":          {"rich_text": {}},
        "Area":           {"select": {"options": _AREA_OPTIONS}},
        "Linked Project": _rel(projects_db_id),
        "Date":           {"date": {}},
        "Sources":        {"rich_text": {}},
        "Key Findings":   {"rich_text": {}},
        "Open Questions": {"rich_text": {}},
        "Confidence":     {"select": {"options": [
            {"name": "High",   "color": "green"},
            {"name": "Medium", "color": "yellow"},
            {"name": "Low",    "color": "red"},
        ]}},
        "Status":         {"select": {"options": [
            {"name": "Draft",    "color": "gray"},
            {"name": "Reviewed", "color": "blue"},
            {"name": "Applied",  "color": "green"},
        ]}},
    }


def _build_skills_properties(projects_db_id: str, research_db_id: str) -> dict:
    return {
        "Skill Name":      {"title": {}},
        "Priority":        {"select": {"options": _PRIORITY_OPTIONS}},
        "Current Stage":   {"rich_text": {}},
        "Stage Status":    {"select": {"options": [
            {"name": "Active",   "color": "blue"},
            {"name": "Blocked",  "color": "red"},
            {"name": "Complete", "color": "green"},
        ]}},
        "Next Session":    {"rich_text": {}},
        "Last Practiced":  {"date": {}},
        "Linked Projects": _rel(projects_db_id),
        "Linked Research": _rel(research_db_id),
    }


def _build_practice_log_properties(skills_db_id: str) -> dict:
    return {
        "Entry Title":    {"title": {}},
        "Skill":          _rel(skills_db_id),
        "Date":           {"date": {}},
        "What I Did":     {"rich_text": {}},
        "What I Noticed": {"rich_text": {}},
    }


def _build_opportunities_properties(skills_db_id: str) -> dict:
    return {
        "Opportunity Name":  {"title": {}},
        "Skill":             _rel(skills_db_id),
        "Type":              {"select": {"options": [
            {"name": "Course",           "color": "blue"},
            {"name": "Book",             "color": "green"},
            {"name": "Mentor/Community", "color": "purple"},
            {"name": "Project",          "color": "orange"},
            {"name": "Competition",      "color": "red"},
            {"name": "Other",            "color": "gray"},
        ]}},
        "URL":               {"url": {}},
        "Why It's Relevant": {"rich_text": {}},
        "Stage Relevance":   {"rich_text": {}},
        "Last Updated":      {"date": {}},
    }


# ── Database creation ─────────────────────────────────────────────────────────

def _create_database(parent_page_id: str, title: str, properties: dict, api_key: str) -> str:
    """Creates a full-page database under parent_page_id. Returns the database ID."""
    payload = {
        "parent":     {"type": "page_id", "page_id": parent_page_id},
        "title":      [{"type": "text", "text": {"content": title}}],
        "is_inline":  False,
        "properties": properties,
    }
    result = _notion_post("databases", payload, api_key)
    return result["id"]


def _notion_url(db_id: str) -> str:
    return f"https://notion.so/{db_id.replace('-', '')}"


# ── Check mode ────────────────────────────────────────────────────────────────

def _run_check(api_key: str) -> None:
    if not _NOTION_IDS.exists():
        print("[jade_setup] No notion_ids.json found. Run setup first.", file=sys.stderr)
        sys.exit(1)

    ids = json.loads(_NOTION_IDS.read_text())
    print("\n[jade_setup] Validating workspace...\n")
    all_ok = True

    for key, display_name in _DB_DISPLAY_NAMES.items():
        db_id = ids.get(key)
        if not db_id:
            print(f"  ✗ {display_name:20s} — ID missing from notion_ids.json")
            all_ok = False
            continue

        try:
            db = _notion_get(f"databases/{db_id}", api_key)
        except RuntimeError as e:
            print(f"  ✗ {display_name:20s} — {e}")
            all_ok = False
            continue

        print(f"  ✓ {display_name:20s} | {db_id}")

        # Validate relation properties point to the correct target DBs
        expected_rels = _EXPECTED_RELATIONS.get(key, {})
        props = db.get("properties", {})
        for prop_name, target_key in expected_rels.items():
            expected_id = ids.get(target_key, "").replace("-", "")
            prop = props.get(prop_name)
            if prop is None:
                print(f"      ✗ Relation '{prop_name}' — property not found in DB")
                all_ok = False
                continue
            actual_id = prop.get("relation", {}).get("database_id", "").replace("-", "")
            if actual_id == expected_id:
                print(f"      ✓ Relation '{prop_name}' → {_DB_DISPLAY_NAMES.get(target_key, target_key)}")
            else:
                print(
                    f"      ✗ Relation '{prop_name}' — stale target\n"
                    f"        expected: {expected_id}\n"
                    f"        actual:   {actual_id}"
                )
                all_ok = False

    print()
    if all_ok:
        print("[jade_setup] All checks passed ✓\n")
    else:
        print("[jade_setup] Some checks failed. Re-run with --force to rebuild.\n")
        sys.exit(1)


# ── Main setup ────────────────────────────────────────────────────────────────

def run(force: bool = False, check: bool = False) -> None:
    creds     = _load_credentials()
    api_key   = creds["NOTION_API_KEY"]
    parent_id = creds["NOTION_PARENT_PAGE_ID"]

    if check:
        _validate_key(api_key)
        _run_check(api_key)
        return

    if _NOTION_IDS.exists() and not force:
        existing = json.loads(_NOTION_IDS.read_text())
        print(
            f"\n[jade_setup] notion_ids.json already exists "
            f"(created {existing.get('created_at', 'unknown')}).\n"
            "Use --force to overwrite, or --check to validate the existing workspace.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    _validate_key(api_key)
    print(f"\n[jade_setup] Creating databases under 'Spencer's Workspace'...\n")

    ids: dict[str, str] = {}

    # Order matters — each step's lambda can only reference IDs created before it
    steps = [
        ("projects_db_id",     "Projects",      lambda: _build_projects_properties()),
        ("tasks_db_id",        "Tasks",          lambda: _build_tasks_properties(ids["projects_db_id"])),
        ("research_db_id",     "Research Vault", lambda: _build_research_properties(ids["projects_db_id"])),
        ("skills_db_id",       "Skills",         lambda: _build_skills_properties(ids["projects_db_id"], ids["research_db_id"])),
        ("practice_log_db_id", "Practice Log",   lambda: _build_practice_log_properties(ids["skills_db_id"])),
        ("opportunities_db_id","Opportunities",  lambda: _build_opportunities_properties(ids["skills_db_id"])),
    ]

    for key, title, build_props in steps:
        print(f"  Creating {title}...", end=" ", flush=True)
        try:
            db_id    = _create_database(parent_id, title, build_props(), api_key)
            ids[key] = db_id
            print("✓")
        except RuntimeError as e:
            print(f"✗\n\n[jade_setup] ERROR creating {title}: {e}\n", file=sys.stderr)
            sys.exit(1)

    # Write IDs to memory/notion_ids.json
    output = {
        **ids,
        "parent_page_id": parent_id,
        "created_at":     datetime.now(timezone.utc).isoformat(),
    }
    _NOTION_IDS.parent.mkdir(parents=True, exist_ok=True)
    _NOTION_IDS.write_text(json.dumps(output, indent=2))
    print(f"\n[jade_setup] IDs written → {_NOTION_IDS}\n")

    # Success table
    name_w = 20
    id_w   = 36
    print(f"  {'Database':<{name_w}}  {'ID':<{id_w}}  URL")
    print("  " + "─" * (name_w + id_w + 48))
    for key, display_name in _DB_DISPLAY_NAMES.items():
        db_id = ids[key]
        print(f"  {display_name:<{name_w}}  {db_id:<{id_w}}  {_notion_url(db_id)}")

    # Manual steps checklist
    print("\n" + "─" * 62)
    print("  MANUAL STEPS REMAINING")
    print("─" * 62)
    print("  [ ] Open 'Spencer's Workspace' in Notion, verify all 6 DBs")
    print("  [ ] Add Progress % formula to Projects DB:")
    print('        if(empty(prop("Linked Tasks")), 0,')
    print('          round(length(filter(prop("Linked Tasks"),')
    print('          current.prop("Status") == "Done"))')
    print('          / length(prop("Linked Tasks")) * 100))')
    print("  [ ] Create area folder pages (School/ACT, WTT, Personal Goals,")
    print("        Side Projects, Reading) with filtered views of each DB")
    print("  [ ] Create Home Dashboard page with today task view")
    print("─" * 62)
    print("\n[jade_setup] Run --check to validate all relations.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="One-time Notion workspace setup for JADE"
    )
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing notion_ids.json and recreate all DBs")
    parser.add_argument("--check", action="store_true",
                        help="Validate existing workspace and relation targets")
    args = parser.parse_args()
    run(force=args.force, check=args.check)
