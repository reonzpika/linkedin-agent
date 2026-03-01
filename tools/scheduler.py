"""
Cross-platform OS scheduling for LinkedIn post execution.
"""

import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def schedule_execution(session_id: str, execution_time: datetime) -> dict:
    """
    Schedule execute_post.py to run at execution_time using OS scheduler.
    Returns {success: bool, task_id: str, error: str}. Never raises.
    """
    script_path = Path(__file__).resolve().parent.parent / "execute_post.py"
    python_exe = sys.executable
    system = platform.system()

    try:
        if system == "Windows":
            task_name = f"LinkedInPost_{session_id.replace('-', '_')[:50]}"
            date_str = execution_time.strftime("%Y-%m-%d")
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
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return {"success": True, "task_id": task_name, "error": ""}
            return {
                "success": False,
                "task_id": "",
                "error": result.stderr or result.stdout or "unknown",
            }

        if system in ("Darwin", "Linux"):
            time_str = execution_time.strftime("%H:%M %Y-%m-%d")
            cmd = (
                f'echo "{python_exe} {script_path} {session_id}" | at {time_str}'
            )
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                job_id = (
                    result.stderr.split()[-1]
                    if result.stderr
                    else "unknown"
                )
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
