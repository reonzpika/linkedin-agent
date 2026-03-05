"""
LinkedIn Post Execution Script.
Reads approved state from outputs/[session_id], executes Golden Hour posting.
Called by OS scheduler or manually: python execute_post.py [session_id]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import os

os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> None:
    if len(sys.argv) < 2:
        print("Error: No session_id provided")
        sys.exit(1)

    argv = sys.argv[1:]
    main_post_only = "--main-post-only" in argv
    comments_then_schedule = "--comments-then-schedule" in argv
    if main_post_only:
        argv = [a for a in argv if a != "--main-post-only"]
    if comments_then_schedule:
        argv = [a for a in argv if a != "--comments-then-schedule"]
    session_id = argv[0] if argv else None
    if not session_id:
        print("Error: No session_id provided")
        sys.exit(1)

    output_dir = ROOT / "outputs" / session_id

    if not output_dir.exists():
        print(f"Error: Output directory not found: {output_dir}")
        sys.exit(1)

    state_file = output_dir / "session_state.json"
    if not state_file.exists():
        print(f"Error: session_state.json not found in {output_dir}")
        sys.exit(1)

    state = json.loads(state_file.read_text(encoding="utf-8"))

    from tools.executor import (
        executor_run,
        executor_run_comments_only,
        executor_run_main_post_only,
    )
    from tools.browser import get_browser_context

    context = get_browser_context()
    try:
        if comments_then_schedule:
            print("Posting 6 Golden Hour comments, then scheduling main post in 20 minutes...")
            result = executor_run_comments_only(state, context)
            (output_dir / "execution_results.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            from tools.scheduler import schedule_main_post_in_minutes

            sched = schedule_main_post_in_minutes(session_id, 20)
            if not sched.get("success"):
                print(f"Warning: could not schedule main post: {sched.get('error')}")
                print(f"Run manually in 20 minutes: python execute_post.py {session_id} --main-post-only")
            else:
                print(f"6 comments posted. Main post scheduled for {sched.get('run_at', '~20 min')}. Safe to close this terminal.")
            context.close()
            sys.exit(0)
        if main_post_only:
            print("Running main post and first comment only (no Golden Hour comments)")
            result = executor_run_main_post_only(state, context)
        else:
            result = executor_run(state, context)

        (output_dir / "execution_results.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )

        temp_dir = ROOT / "temporary"
        pending_file = temp_dir / "pending_posts.json"
        if pending_file.exists():
            pending = json.loads(pending_file.read_text(encoding="utf-8"))
            pending["posts"] = [
                p for p in pending.get("posts", []) if p.get("session_id") != session_id
            ]
            pending_file.write_text(json.dumps(pending, indent=2), encoding="utf-8")

        try:
            from tools.schedule_manager import mark_post_executed

            mark_post_executed(session_id)
        except Exception as e:
            print(f"Warning: Could not update schedule registry: {e}")

        print(f"Execution completed for {session_id}")
        sys.exit(0)
    except RuntimeError as e:
        print(f"Execution failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Execution failed: {e}")
        sys.exit(1)
    finally:
        context.close()


if __name__ == "__main__":
    main()
