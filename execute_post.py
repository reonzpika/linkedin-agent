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

    session_id = sys.argv[1]
    output_dir = ROOT / "outputs" / session_id

    if not output_dir.exists():
        print(f"Error: Output directory not found: {output_dir}")
        sys.exit(1)

    state_file = output_dir / "session_state.json"
    if not state_file.exists():
        print(f"Error: session_state.json not found in {output_dir}")
        sys.exit(1)

    state = json.loads(state_file.read_text(encoding="utf-8"))

    from tools.executor import executor_run
    from tools.browser import get_browser_context

    context = get_browser_context()
    try:
        result = executor_run(state, context)

        (output_dir / "execution_results.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )

        temp_dir = ROOT / "temporary"
        pending_file = temp_dir / "pending_posts.json"
        if pending_file.exists():
            pending = json.loads(pending_file.read_text(encoding="utf-8"))
            pending["posts"] = [
                p
                for p in pending.get("posts", [])
                if p.get("session_id") != session_id
            ]
            pending_file.write_text(
                json.dumps(pending, indent=2), encoding="utf-8"
            )

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
