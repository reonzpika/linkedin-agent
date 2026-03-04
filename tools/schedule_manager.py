"""
Schedule management for LinkedIn posting.
Tracks all scheduled posts, finds next available slot, prevents conflicts.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytz

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_FILE = ROOT / "temporary" / "schedule_registry.json"


def _ensure_schedule_file() -> None:
    """Create schedule_registry.json if it doesn't exist."""
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SCHEDULE_FILE.exists():
        SCHEDULE_FILE.write_text(
            json.dumps({"scheduled_posts": []}, indent=2),
            encoding="utf-8",
        )


def _slot_timestamp(dt: datetime) -> float:
    """Normalise datetime to timestamp for timezone-safe comparison."""
    if dt.tzinfo is None:
        return dt.timestamp()
    return dt.astimezone(pytz.UTC).timestamp()


def get_next_available_slot() -> datetime:
    """
    Find next available Tuesday or Thursday at 8:00am NZST.

    Strategy:
    - Posts twice weekly: Tuesday and Thursday at 8am NZST
    - Comments post at 7:40am (so executor runs at 7:40am)
    - Check schedule registry to avoid conflicts

    Returns:
        datetime for 7:40am NZST (executor run time, 20min before main post)
    """
    from tools.scheduler import get_next_slot_datetime

    nz_tz = pytz.timezone("Pacific/Auckland")
    now = datetime.now(nz_tz)

    _ensure_schedule_file()
    registry = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    scheduled_ts = {
        _slot_timestamp(datetime.fromisoformat(p["scheduled_for"]))
        for p in registry.get("scheduled_posts", [])
        if p.get("status") == "scheduled"
    }

    # Check next Tuesday 8am
    next_tue = get_next_slot_datetime(1, 8, 0)  # 1 = Tuesday
    tue_exec_time = next_tue.replace(hour=7, minute=40)  # Executor runs 20min early

    if _slot_timestamp(tue_exec_time) not in scheduled_ts and tue_exec_time > now:
        return tue_exec_time

    # Check next Thursday 8am
    next_thu = get_next_slot_datetime(3, 8, 0)  # 3 = Thursday
    thu_exec_time = next_thu.replace(hour=7, minute=40)

    if _slot_timestamp(thu_exec_time) not in scheduled_ts and thu_exec_time > now:
        return thu_exec_time

    # Both this week's slots are taken or passed, check next week Tuesday
    next_week_tue = next_tue + timedelta(days=7)
    next_week_tue_exec = next_week_tue.replace(hour=7, minute=40)

    if _slot_timestamp(next_week_tue_exec) not in scheduled_ts:
        return next_week_tue_exec

    # Fallback: next week Thursday (should never conflict unless heavily scheduled)
    next_week_thu = next_thu + timedelta(days=7)
    return next_week_thu.replace(hour=7, minute=40)


def register_scheduled_post(session_id: str, scheduled_for: datetime) -> None:
    """
    Add a post to the schedule registry.

    Args:
        session_id: Session folder name (e.g. "2026-03-05_medtech-alex")
        scheduled_for: Executor run time (7:40am NZST, 20min before main post)
    """
    _ensure_schedule_file()
    registry = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))

    existing = [
        p
        for p in registry.get("scheduled_posts", [])
        if p.get("session_id") == session_id
    ]

    nz_tz = pytz.timezone("Pacific/Auckland")
    if existing:
        for post in registry["scheduled_posts"]:
            if post.get("session_id") == session_id:
                post["scheduled_for"] = scheduled_for.isoformat()
                post["status"] = "scheduled"
                post["updated_at"] = datetime.now(nz_tz).isoformat()
                break
    else:
        registry.setdefault("scheduled_posts", []).append(
            {
                "session_id": session_id,
                "scheduled_for": scheduled_for.isoformat(),
                "main_post_time": scheduled_for.replace(hour=8, minute=0).isoformat(),
                "status": "scheduled",
                "created_at": datetime.now(nz_tz).isoformat(),
            }
        )

    SCHEDULE_FILE.write_text(
        json.dumps(registry, indent=2),
        encoding="utf-8",
    )


def mark_post_executed(session_id: str) -> None:
    """Mark a scheduled post as executed."""
    _ensure_schedule_file()
    registry = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    nz_tz = pytz.timezone("Pacific/Auckland")

    for post in registry.get("scheduled_posts", []):
        if post.get("session_id") == session_id:
            post["status"] = "executed"
            post["executed_at"] = datetime.now(nz_tz).isoformat()
            break

    SCHEDULE_FILE.write_text(
        json.dumps(registry, indent=2),
        encoding="utf-8",
    )


def get_schedule_summary() -> str:
    """
    Return human-readable schedule summary for chat display.

    Returns:
        Formatted string showing upcoming scheduled posts
    """
    _ensure_schedule_file()
    registry = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))

    scheduled = [
        p for p in registry.get("scheduled_posts", []) if p.get("status") == "scheduled"
    ]

    if not scheduled:
        return "No posts currently scheduled."

    scheduled.sort(key=lambda p: p.get("scheduled_for", ""))

    lines = ["Scheduled posts:"]
    for post in scheduled[:5]:
        main_post_time = datetime.fromisoformat(post["main_post_time"])
        session_id = post.get("session_id", "unknown")
        lines.append(
            f"  * {main_post_time.strftime('%a %d %b, %I:%M%p')} NZST - {session_id}"
        )

    return "\n".join(lines)
