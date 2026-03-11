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


# Posting slots: (weekday, hour, minute) for main post time NZST. 0=Mon, 1=Tue, 2=Wed, 3=Thu.
POST_SLOTS = [(1, 10, 0), (2, 12, 0), (3, 9, 0)]  # Tue 10am, Wed 12pm, Thu 9am
EXECUTOR_MINUTES_BEFORE = 20


def get_next_available_slot() -> datetime:
    """
    Find next available slot: Tue 10am, Wed 12pm, or Thu 9am NZST.
    Returns the soonest slot that is in the future and not already scheduled.
    Executor runs 20 minutes before main post (Golden Hour comments first).

    Returns:
        datetime for executor run time (20 min before main post)
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

    candidates = []
    for day, hour, minute in POST_SLOTS:
        main_time = get_next_slot_datetime(day, hour, minute)
        exec_time = main_time - timedelta(minutes=EXECUTOR_MINUTES_BEFORE)
        if _slot_timestamp(exec_time) not in scheduled_ts and exec_time > now:
            candidates.append(exec_time)

    if not candidates:
        # All three this week are taken or past; use next week's earliest
        for day, hour, minute in POST_SLOTS:
            main_time = get_next_slot_datetime(day, hour, minute) + timedelta(days=7)
            exec_time = main_time - timedelta(minutes=EXECUTOR_MINUTES_BEFORE)
            if _slot_timestamp(exec_time) not in scheduled_ts:
                candidates.append(exec_time)

    return min(candidates) if candidates else (
        get_next_slot_datetime(1, 10, 0) - timedelta(minutes=EXECUTOR_MINUTES_BEFORE)
    )


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
        main_post_time = scheduled_for + timedelta(minutes=EXECUTOR_MINUTES_BEFORE)
        for post in registry["scheduled_posts"]:
            if post.get("session_id") == session_id:
                post["scheduled_for"] = scheduled_for.isoformat()
                post["main_post_time"] = main_post_time.isoformat()
                post["status"] = "scheduled"
                post["updated_at"] = datetime.now(nz_tz).isoformat()
                break
    else:
        main_post_time = scheduled_for + timedelta(minutes=EXECUTOR_MINUTES_BEFORE)
        registry.setdefault("scheduled_posts", []).append(
            {
                "session_id": session_id,
                "scheduled_for": scheduled_for.isoformat(),
                "main_post_time": main_post_time.isoformat(),
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
