"""
Cross-platform OS scheduling for LinkedIn post execution.
"""

import platform
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytz


def get_next_slot_datetime(
    day_of_week: int, hour: int = 8, minute: int = 0
) -> datetime:
    """
    Calculate next occurrence of day_of_week at hour:minute NZST.

    Args:
        day_of_week: 0=Monday, 1=Tuesday, 3=Thursday, 6=Sunday
        hour: Hour in 24h format (default: 8 for 8am)
        minute: Minute (default: 0)

    Returns:
        datetime in NZST timezone

    Example:
        get_next_slot_datetime(1, 8, 0)  # Next Tuesday 8:00am NZST
    """
    nz_tz = pytz.timezone("Pacific/Auckland")
    now = datetime.now(nz_tz)

    # Calculate days ahead to target day_of_week
    days_ahead = (day_of_week - now.weekday()) % 7

    # If target day is today but time has passed, schedule for next week
    target = now + timedelta(days=days_ahead)
    target = target.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        # Time has passed today, schedule for next week
        target = target + timedelta(days=7)

    return target


def schedule_execution(session_id: str, execution_time: datetime) -> dict:
    """
    Schedule execute_post.py to run at execution_time using OS scheduler.
    If execution_time is timezone-aware, it is converted to local time for the OS.
    Returns {success: bool, task_id: str, error: str}. Never raises.
    """
    if execution_time.tzinfo is not None:
        execution_time = execution_time.astimezone()
    script_path = Path(__file__).resolve().parent.parent / "execute_post.py"
    python_exe = sys.executable
    system = platform.system()

    try:
        if system == "Windows":
            task_name = f"LinkedInPost_{session_id.replace('-', '_')[:50]}"
            date_str = execution_time.strftime("%d/%m/%Y")
            time_str = execution_time.strftime("%H:%M")
            cmd_str = f'"{python_exe}" "{script_path}" {session_id}'
            cmd = [
                "schtasks",
                "/create",
                "/tn",
                task_name,
                "/tr",
                cmd_str,
                "/sc",
                "once",
                "/sd",
                date_str,
                "/st",
                time_str,
                "/f",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {"success": True, "task_id": task_name, "error": ""}
            return {
                "success": False,
                "task_id": "",
                "error": result.stderr or result.stdout or "unknown",
            }

        if system in ("Darwin", "Linux"):
            time_str = execution_time.strftime("%H:%M %Y-%m-%d")
            cmd = f'echo "{python_exe} {script_path} {session_id}" | at {time_str}'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                job_id = result.stderr.split()[-1] if result.stderr else "unknown"
                return {"success": True, "task_id": job_id, "error": ""}
            return {
                "success": False,
                "task_id": "",
                "error": result.stderr or result.stdout or "unknown",
            }

        return {
            "success": False,
            "task_id": "",
            "error": f"Unsupported OS: {system}",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "task_id": "", "error": "scheduler timeout"}
    except Exception as e:
        return {"success": False, "task_id": "", "error": str(e)}


def schedule_execution_with_flag(
    session_id: str, execution_time: datetime, flag: str
) -> dict:
    """
    Schedule execute_post.py with an extra CLI flag at execution_time.
    Used for --main-post-only (Phase 2 of two-phase execute now).
    Returns {success: bool, task_id: str, error: str, run_at: str (ISO)}. Never raises.
    """
    if execution_time.tzinfo is not None:
        execution_time = execution_time.astimezone()
    script_path = Path(__file__).resolve().parent.parent / "execute_post.py"
    python_exe = sys.executable
    system = platform.system()
    run_at_iso = execution_time.isoformat()

    try:
        if system == "Windows":
            task_name = f"LinkedInPostMain_{session_id.replace('-', '_')[:45]}"
            date_str = execution_time.strftime("%d/%m/%Y")
            time_str = execution_time.strftime("%H:%M")
            cmd_str = f'"{python_exe}" "{script_path}" {session_id} {flag}'
            cmd = [
                "schtasks",
                "/create",
                "/tn",
                task_name,
                "/tr",
                cmd_str,
                "/sc",
                "once",
                "/sd",
                date_str,
                "/st",
                time_str,
                "/f",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {
                    "success": True,
                    "task_id": task_name,
                    "error": "",
                    "run_at": run_at_iso,
                }
            return {
                "success": False,
                "task_id": "",
                "error": result.stderr or result.stdout or "unknown",
                "run_at": run_at_iso,
            }

        if system in ("Darwin", "Linux"):
            time_str = execution_time.strftime("%H:%M %Y-%m-%d")
            cmd = f'echo "{python_exe} {script_path} {session_id} {flag}" | at {time_str}'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                job_id = result.stderr.split()[-1] if result.stderr else "unknown"
                return {
                    "success": True,
                    "task_id": job_id,
                    "error": "",
                    "run_at": run_at_iso,
                }
            return {
                "success": False,
                "task_id": "",
                "error": result.stderr or result.stdout or "unknown",
                "run_at": run_at_iso,
            }

        return {
            "success": False,
            "task_id": "",
            "error": f"Unsupported OS: {system}",
            "run_at": run_at_iso,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "task_id": "", "error": "scheduler timeout", "run_at": run_at_iso}
    except Exception as e:
        return {"success": False, "task_id": "", "error": str(e), "run_at": run_at_iso}


def schedule_main_post_in_minutes(
    session_id: str, delay_minutes: int = 20
) -> dict:
    """
    Schedule execute_post.py --main-post-only to run in delay_minutes.
    Used for Phase 2 of two-phase "execute now" (comments posted, main post in 20 min).
    Returns {success: bool, task_id: str, error: str, run_at: str (ISO)}.
    """
    run_at = datetime.now().astimezone() + timedelta(minutes=delay_minutes)
    return schedule_execution_with_flag(session_id, run_at, "--main-post-only")


def schedule_execution_auto_slot(session_id: str) -> dict:
    """
    Schedule execute_post.py for next available Tue/Thu 8am NZST slot.
    Automatically finds next available slot and registers in schedule registry.

    Args:
        session_id: Session folder name

    Returns:
        {success: bool, task_id: str, scheduled_for: str (ISO), executor_runs_at: str (ISO), error: str}
    """
    from tools.schedule_manager import get_next_available_slot, register_scheduled_post

    try:
        exec_time = get_next_available_slot()
        register_scheduled_post(session_id, exec_time)
        result = schedule_execution(session_id, exec_time)

        if result.get("success"):
            main_post_time = exec_time.replace(hour=8, minute=0)
            result["scheduled_for"] = main_post_time.isoformat()
            result["executor_runs_at"] = exec_time.isoformat()

        return result

    except Exception as e:
        return {
            "success": False,
            "task_id": "",
            "scheduled_for": "",
            "executor_runs_at": "",
            "error": str(e),
        }
