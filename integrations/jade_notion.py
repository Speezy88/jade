#!/usr/bin/env python3
"""
jade_notion.py

Notion API integration for JADE — Task, Project, and Skill CRUD.
Uses urllib only (no requests — SSL compatibility on macOS Python.org builds).

Credentials:  ~/.config/jade/credentials  (NOTION_API_KEY)
DB IDs:       memory/notion_ids.json      (written by jade_setup.py)
"""

import json
import math
import ssl
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

_JADE_DIR   = Path("/Users/spencerhatch/Jade")
_IDS_PATH   = _JADE_DIR / "memory" / "notion_ids.json"
_CREDS_PATH = Path.home() / ".config" / "jade" / "credentials"
_API_BASE   = "https://api.notion.com/v1"
_API_VER    = "2022-06-28"

# Python.org Python on macOS ships without root certs installed.
# Fix properly with: /Applications/Python\ 3.13/Install\ Certificates.command
_SSL_CTX = ssl._create_unverified_context()

# Priority → sort rank (lower = higher priority)
_PRIORITY_RANK = {"🔴 High": 0, "🟡 Medium": 1, "🟢 Low": 2}


# ── Config loading ────────────────────────────────────────────────────────────

def _load_config() -> tuple[str, dict]:
    """Returns (api_key, notion_ids_dict). Raises RuntimeError if missing."""
    creds: dict[str, str] = {}
    if _CREDS_PATH.exists():
        for line in _CREDS_PATH.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                creds[k.strip()] = v.strip()

    api_key = creds.get("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError(f"NOTION_API_KEY not found in {_CREDS_PATH}")

    if not _IDS_PATH.exists():
        raise RuntimeError(f"notion_ids.json not found — run jade_setup.py first")

    return api_key, json.loads(_IDS_PATH.read_text())


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _headers(api_key: str) -> dict:
    return {
        "Authorization":  f"Bearer {api_key}",
        "Notion-Version": _API_VER,
        "Content-Type":   "application/json",
    }


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


def _notion_patch(endpoint: str, payload: dict, api_key: str) -> dict:
    req = urllib.request.Request(
        f"{_API_BASE}/{endpoint}",
        data=json.dumps(payload).encode(),
        headers=_headers(api_key),
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"PATCH {endpoint} → {e.code}: {e.read().decode()}")


# ── Property extraction helpers ───────────────────────────────────────────────

def _prop_text(page: dict, name: str) -> str:
    prop = page.get("properties", {}).get(name, {})
    items = prop.get("title") or prop.get("rich_text") or []
    return "".join(t.get("plain_text", "") for t in items)


def _prop_select(page: dict, name: str) -> str | None:
    sel = page.get("properties", {}).get(name, {}).get("select")
    return sel["name"] if sel else None


def _prop_date(page: dict, name: str) -> str | None:
    d = page.get("properties", {}).get(name, {}).get("date")
    return d["start"] if d else None


def _prop_number(page: dict, name: str) -> int | None:
    return page.get("properties", {}).get(name, {}).get("number")


def _prop_checkbox(page: dict, name: str) -> bool:
    return page.get("properties", {}).get(name, {}).get("checkbox", False)


# ── Internal query helpers ────────────────────────────────────────────────────

def _query_tasks(filter_obj: dict, api_key: str, db_id: str) -> list[dict]:
    """Query a Notion database, handling pagination. Returns raw page list."""
    pages: list[dict] = []
    payload: dict = {"filter": filter_obj, "page_size": 100}
    while True:
        result = _notion_post(f"databases/{db_id}/query", payload, api_key)
        pages.extend(result.get("results", []))
        if not result.get("has_more"):
            break
        payload["start_cursor"] = result["next_cursor"]
    return pages


def _page_to_task(page: dict) -> dict:
    """Extract the fields Jade uses from a raw Notion page."""
    return {
        "id":           page["id"],
        "name":         _prop_text(page, "Task Name"),
        "priority":     _prop_select(page, "Priority"),
        "due":          _prop_date(page, "Due Date"),
        "energy":       _prop_select(page, "Energy"),
        "duration":     _prop_number(page, "Estimated Duration"),
        "status":       _prop_select(page, "Status"),
        "area":         _prop_select(page, "Area"),
        "recurring":    _prop_checkbox(page, "Recurring"),
        "chunk_size":   _prop_number(page, "Chunk Size"),
        "total_target": _prop_number(page, "Total Target"),
        "rec_start":    _prop_date(page, "Recurrence Start"),
        "rec_end":      _prop_date(page, "Recurrence End"),
    }


def _active_filter() -> dict:
    """Filter for tasks that are Not Started or In Progress."""
    return {
        "or": [
            {"property": "Status", "select": {"equals": "Not Started"}},
            {"property": "Status", "select": {"equals": "In Progress"}},
        ]
    }


def _priority_sort_key(task: dict) -> tuple:
    return (_PRIORITY_RANK.get(task["priority"] or "", 99), task["due"] or "9999")


# ── Public task queries ───────────────────────────────────────────────────────

def get_todays_tasks() -> list[dict]:
    """
    Active tasks due today, sorted by priority then due time.
    Returns [] on any error — never raises.
    """
    try:
        api_key, ids = _load_config()
        filter_obj = {
            "and": [
                {"property": "Due Date", "date": {"equals": date.today().isoformat()}},
                _active_filter(),
            ]
        }
        pages = _query_tasks(filter_obj, api_key, ids["tasks_db_id"])
        return sorted((_page_to_task(p) for p in pages), key=_priority_sort_key)
    except Exception as exc:
        print(f"[jade_notion] get_todays_tasks failed: {exc}", file=sys.stderr)
        return []


def get_upcoming_tasks(n: int = 7) -> list[dict]:
    """
    Active tasks due in the next n days (excluding today), sorted by date then priority.
    Returns [] on any error.
    """
    try:
        api_key, ids = _load_config()
        today    = date.today()
        end_date = (today + timedelta(days=n)).isoformat()
        filter_obj = {
            "and": [
                {"property": "Due Date", "date": {"after": today.isoformat()}},
                {"property": "Due Date", "date": {"on_or_before": end_date}},
                _active_filter(),
            ]
        }
        pages = _query_tasks(filter_obj, api_key, ids["tasks_db_id"])
        return sorted(
            (_page_to_task(p) for p in pages),
            key=lambda t: (t["due"] or "9999", _PRIORITY_RANK.get(t["priority"] or "", 99)),
        )
    except Exception as exc:
        print(f"[jade_notion] get_upcoming_tasks failed: {exc}", file=sys.stderr)
        return []


def get_overdue_tasks() -> list[dict]:
    """
    Active tasks with Due Date before today, sorted oldest first.
    Returns [] on any error.
    """
    try:
        api_key, ids = _load_config()
        filter_obj = {
            "and": [
                {"property": "Due Date", "date": {"before": date.today().isoformat()}},
                _active_filter(),
            ]
        }
        pages = _query_tasks(filter_obj, api_key, ids["tasks_db_id"])
        return sorted((_page_to_task(p) for p in pages), key=lambda t: t["due"] or "0000")
    except Exception as exc:
        print(f"[jade_notion] get_overdue_tasks failed: {exc}", file=sys.stderr)
        return []


# ── Task writes ───────────────────────────────────────────────────────────────

def update_task_status(task_id: str, status: str) -> bool:
    """
    Updates a task's Status. Returns True on success.
    Valid statuses: Not Started, In Progress, Done, Skipped
    """
    try:
        api_key, _ = _load_config()
        _notion_patch(
            f"pages/{task_id}",
            {"properties": {"Status": {"select": {"name": status}}}},
            api_key,
        )
        return True
    except Exception as exc:
        print(f"[jade_notion] update_task_status failed: {exc}", file=sys.stderr)
        return False


def create_task(
    name: str,
    area: str,
    priority: str,
    due_date: date | None = None,
    energy: str | None = None,
    duration: int | None = None,
    status: str = "Not Started",
    notes: str | None = None,
    project_id: str | None = None,
) -> str | None:
    """Creates a single task page. Returns the new page ID, or None on error."""
    try:
        api_key, ids = _load_config()
        props: dict = {
            "Task Name": {"title": [{"text": {"content": name}}]},
            "Area":      {"select": {"name": area}},
            "Priority":  {"select": {"name": priority}},
            "Status":    {"select": {"name": status}},
        }
        if due_date:
            props["Due Date"] = {"date": {"start": due_date.isoformat()}}
        if energy:
            props["Energy"] = {"select": {"name": energy}}
        if duration is not None:
            props["Estimated Duration"] = {"number": duration}
        if notes:
            props["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
        if project_id:
            props["Linked Project"] = {"relation": [{"id": project_id}]}

        result = _notion_post(
            "pages",
            {"parent": {"database_id": ids["tasks_db_id"]}, "properties": props},
            api_key,
        )
        return result["id"]
    except Exception as exc:
        print(f"[jade_notion] create_task failed: {exc}", file=sys.stderr)
        return None


def create_recurring_task(
    name: str,
    area: str,
    priority: str,
    total_target: int,
    chunk_size: int,
    start_date: date,
    energy: str | None = None,
    project_id: str | None = None,
) -> list[str]:
    """
    Creates a parent task + daily child instances for goal-based recurrence.

    Args:
        total_target: Total minutes to cover across all sessions (e.g. 360)
        chunk_size:   Daily session size in minutes (e.g. 30)
        start_date:   Due date for the first child instance

    Returns:
        List of created page IDs — parent first, then children in order.
        Empty list on error.

    Example:
        total_target=360, chunk_size=30 → 12 children, end_date = start + 11 days
    """
    try:
        api_key, ids = _load_config()
        db_id = ids["tasks_db_id"]

        num_instances = math.ceil(total_target / chunk_size)
        end_date      = start_date + timedelta(days=num_instances - 1)

        # Parent task — summary record, tracks the goal
        parent_props: dict = {
            "Task Name":        {"title": [{"text": {"content": name}}]},
            "Area":             {"select": {"name": area}},
            "Priority":         {"select": {"name": priority}},
            "Recurring":        {"checkbox": True},
            "Recurrence Type":  {"select": {"name": "Daily chunk"}},
            "Total Target":     {"number": total_target},
            "Chunk Size":       {"number": chunk_size},
            "Recurrence Start": {"date": {"start": start_date.isoformat()}},
            "Recurrence End":   {"date": {"start": end_date.isoformat()}},
            "Status":           {"select": {"name": "In Progress"}},
        }
        if energy:
            parent_props["Energy"] = {"select": {"name": energy}}
        if project_id:
            parent_props["Linked Project"] = {"relation": [{"id": project_id}]}

        parent     = _notion_post("pages", {"parent": {"database_id": db_id}, "properties": parent_props}, api_key)
        created    = [parent["id"]]

        # Child instances — one per day
        for i in range(num_instances):
            child_props: dict = {
                "Task Name":          {"title": [{"text": {"content": f"{name} — Day {i+1}/{num_instances}"}}]},
                "Area":               {"select": {"name": area}},
                "Priority":           {"select": {"name": priority}},
                "Status":             {"select": {"name": "Not Started"}},
                "Due Date":           {"date": {"start": (start_date + timedelta(days=i)).isoformat()}},
                "Estimated Duration": {"number": chunk_size},
                "Recurring":          {"checkbox": False},
            }
            if energy:
                child_props["Energy"] = {"select": {"name": energy}}
            if project_id:
                child_props["Linked Project"] = {"relation": [{"id": project_id}]}

            child = _notion_post("pages", {"parent": {"database_id": db_id}, "properties": child_props}, api_key)
            created.append(child["id"])

        return created

    except Exception as exc:
        print(f"[jade_notion] create_recurring_task failed: {exc}", file=sys.stderr)
        return []
