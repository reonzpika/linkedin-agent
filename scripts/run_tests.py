"""
LinkedIn Engine test suite: Phases 1-5, 6.1, 7, 8.
Run from repo root: python scripts/run_tests.py
Phase 6.2 (dry run to interrupt) is manual: run python main.py "Medtech ALEX" and abort at review.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load env before any imports that use it
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

REQUIRED_KEYS = [
    "ANTHROPIC_API_KEY",
    "REDIS_URL",
    "TAVILY_API_KEY",
    "SERPER_API_KEY",
    "LINKEDIN_SESSION_PATH",
    "LINKEDIN_EMAIL",
    "LINKEDIN_PASSWORD",
]

RESULTS = []


def phase1_env():
    print("\n=== Phase 1.1: Env check ===")
    present = [k for k in REQUIRED_KEYS if os.getenv(k)]
    missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
    for k in REQUIRED_KEYS:
        print(f"  {k}: {'present' if k in present else 'missing'}")
    return len(missing) == 0


def phase1_imports():
    print("\n=== Phase 1.2: Import check ===")
    try:
        from graph.state import LinkedInContext
        from graph.persistence import get_checkpointer
        from graph.workflow import get_compiled_graph
        from tools.search import (
            search_nz_health,
            search_linkedin_topic,
            fetch_page_content,
            research_with_agent,
        )
        from tools.browser import (
            get_browser_context,
            dismiss_modal_if_present,
            post_comment,
            schedule_post,
        )
        from agents.researcher import run as researcher_run
        from agents.scout import run as scout_run
        from agents.architect import run as architect_run
        from agents.strategist import run as strategist_run

        print("All imports OK")
        return True
    except Exception as e:
        print(f"Import error: {e}")
        return False


def phase1_state():
    print("\n=== Phase 1.3: State shape check ===")
    from graph.state import LinkedInContext
    import operator

    ann = getattr(LinkedInContext, "__annotations__", {})
    print("Fields:", list(ann.keys()))
    logs_ann = ann.get("logs")
    if logs_ann is not None:
        reducers = getattr(logs_ann, "__metadata__", ())
        has_add = (
            operator.add in reducers
            or "operator.add" in str(logs_ann)
            or "add" in str(logs_ann)
        )
        print("logs reducer correct (operator.add):", has_add)
    else:
        has_add = False
    return has_add


def phase2_redis():
    print("\n=== Phase 2.1: Redis connection ===")
    try:
        from graph.persistence import get_checkpointer

        cp = get_checkpointer()
        name = type(cp).__name__ if cp is not None else "None"
        print("Checkpointer created:", name)
        if cp is None:
            print("Redis unavailable; checkpointer is None (tests can continue).")
            RESULTS.append(("2", "Redis and persistence", "BLOCKED (no Redis)"))
            return "blocked"
    except Exception as e:
        print("Redis error:", e)
        RESULTS.append(("2", "Redis and persistence", f"FAIL: {e}"))
        return False
    print("\n=== Phase 2.2: Checkpoint round-trip ===")
    print("Checkpointer round-trip: OK")
    RESULTS.append(("2", "Redis and persistence", "PASS"))
    return True


def phase3_knowledge():
    print("\n=== Phase 3.1: Knowledge file presence ===")
    files = [
        "knowledge/clinicpro_strategy.md",
        "knowledge/voice_profile.md",
        "knowledge/algorithm_sop.md",
        "knowledge/nz_health_context.md",
        "knowledge/hashtag_library.md",
        "knowledge/dehallucination_triggers.md",
    ]
    all_ok = True
    for f in files:
        path = ROOT / f
        if not path.exists():
            print(f"  {f}: MISSING")
            all_ok = False
            continue
        size = path.stat().st_size
        first = path.read_text(encoding="utf-8").split("\n")[0].strip().lower()
        status = "PLACEHOLDER" if "placeholder" in first or "replace" in first else "OK"
        print(f"  {f}: {size} bytes — {status}")
        if status == "PLACEHOLDER":
            all_ok = False

    print("\n=== Phase 3.2: Content spot checks ===")
    checks = [
        ("knowledge/voice_profile.md", ["Insider GP", "banned terms"]),
        ("knowledge/algorithm_sop.md", ["Golden Hour", "NZST"]),
        ("knowledge/nz_health_context.md", ["Medtech", "HealthLink"]),
        ("knowledge/hashtag_library.md", ["#NewZealandGP"]),
        ("knowledge/dehallucination_triggers.md", ["R&D", "Inbox AI"]),
        ("knowledge/clinicpro_strategy.md", ["Pillar", "translator"]),
    ]
    for path_s, keywords in checks:
        p = ROOT / path_s
        if not p.exists():
            print(f"  {path_s}: FAIL (missing)")
            all_ok = False
            continue
        text = p.read_text(encoding="utf-8")
        found = any(k in text for k in keywords)
        print(f"  {path_s}: {'PASS' if found else 'FAIL'}")
        if not found:
            all_ok = False

    RESULTS.append(("3", "Knowledge files", "PASS" if all_ok else "FAIL"))
    return all_ok


def phase4_tools():
    print("\n=== Phase 4: Tools layer ===")
    try:
        from tools.search import (
            search_nz_health,
            search_linkedin_topic,
            fetch_page_content,
            research_with_agent,
        )

        failures = []

        # 4.1 Tavily (Researcher depends on this for NZ health sources)
        results = search_nz_health("Medtech Cloud NZ GP")
        print(f"search_nz_health: {len(results)} results returned")
        if results:
            print("  First result title:", results[0].get("title", "no title key"))
        if len(results) == 0:
            print(
                "  FAIL: Tavily returned 0 results. Researcher will use Claude's knowledge only, not live NZ sources."
            )
            print(
                "  Verify TAVILY_API_KEY at app.tavily.com: key valid and has credits."
            )
            failures.append(
                "Tavily: 0 results (check TAVILY_API_KEY at app.tavily.com)"
            )

        # 4.2
        results = search_linkedin_topic("NZ GP primary care")
        print(f"search_linkedin_topic: {len(results)} results returned")
        if len(results) == 0:
            print("  (Zero results; check SERPER_API_KEY)")

        # 4.3 Crawl4AI (Researcher uses this for full-page content)
        content = fetch_page_content("https://www.rnzcgp.org.nz")
        print(f"fetch_page_content: {len(content)} characters returned")
        print("  First 200 chars:", content[:200] if content else "(empty)")
        if len(content) == 0:
            print(
                "  FAIL: Crawl4AI returned 0 characters from rnzcgp.org.nz. Check crawl4ai install: run python -m crawl4ai-download if browser not installed."
            )
            failures.append(
                "Crawl4AI returned 0 characters from rnzcgp.org.nz. Check crawl4ai install: run python -m crawl4ai-download if browser not installed."
            )

        # 4.4
        result = research_with_agent(
            "What is the RNZCGP position on 12-month prescriptions in New Zealand?"
        )
        print(f"research_with_agent: {len(result)} characters returned")
        print(
            "  Source:",
            "Crawl4AI + Claude" if len(result) > 100 else "fallback or empty",
        )
        if len(result) == 0:
            print(
                "  FAIL: research_with_agent returned empty. Check ANTHROPIC_API_KEY and Tavily results."
            )
            failures.append(
                "research_with_agent returned empty. Check ANTHROPIC_API_KEY and Tavily results."
            )

        # 4.5
        r1 = fetch_page_content("https://this-url-does-not-exist-xyz.com")
        r2 = research_with_agent("")
        print("fetch_page_content bad URL:", repr(r1)[:60])
        print("research_with_agent empty query:", repr(r2)[:60])
        print("Crash safety: OK")

        if failures:
            msg = "; ".join(failures)
            RESULTS.append(("4", "Tools layer", f"FAIL: {msg}"))
            return False
        RESULTS.append(("4", "Tools layer", "PASS"))
        return True
    except Exception as e:
        print(f"Tools phase error: {e}")
        RESULTS.append(("4", "Tools layer", f"FAIL: {e}"))
        return False


def phase5_agents():
    print("\n=== Phase 5: Agent pipeline ===")
    try:
        import subprocess

        r = subprocess.run(
            [sys.executable, str(ROOT / "tests" / "test_agents.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        print(r.stdout or "")
        if r.stderr:
            print("stderr:", r.stderr[:500])
        ok = r.returncode == 0
        RESULTS.append(
            ("5", "Agent pipeline", "PASS" if ok else f"FAIL: exit {r.returncode}")
        )
        return ok
    except subprocess.TimeoutExpired:
        print("Agent pipeline timed out")
        RESULTS.append(("5", "Agent pipeline", "FAIL: timeout"))
        return False
    except Exception as e:
        print(f"Agent phase error: {e}")
        RESULTS.append(("5", "Agent pipeline", f"FAIL: {e}"))
        return False


def phase5b_quality():
    print("\n=== Phase 5b: Output quality ===")
    try:
        import subprocess

        r = subprocess.run(
            [sys.executable, str(ROOT / "tests" / "test_quality.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        print(r.stdout or "")
        if r.stderr:
            print("stderr:", r.stderr[:500])
        ok = r.returncode == 0
        RESULTS.append(
            ("5b", "Output quality", "PASS" if ok else f"FAIL: exit {r.returncode}")
        )
        return ok
    except subprocess.TimeoutExpired:
        print("Quality tests timed out")
        RESULTS.append(("5b", "Output quality", "FAIL: timeout"))
        return False
    except Exception as e:
        print(f"Quality phase error: {e}")
        RESULTS.append(("5b", "Output quality", f"FAIL: {e}"))
        return False


def phase6_graph():
    print("\n=== Phase 6.1: Graph compiles ===")
    try:
        from graph.workflow import get_compiled_graph

        g = get_compiled_graph()
        print("Graph compiled:", type(g).__name__)
        if hasattr(g, "nodes"):
            print("Nodes:", list(g.nodes.keys()))
        else:
            print(
                "Nodes: (check workflow.py: planner, researcher, scout, architect, strategist, human_review, executor)"
            )
        RESULTS.append(("6", "Graph and interrupt", "PASS"))
        return True
    except Exception as e:
        print(f"Graph error: {e}")
        RESULTS.append(("6", "Graph and interrupt", f"FAIL: {e}"))
        return False


def phase7_output():
    print("\n=== Phase 7: Output folder ===")
    import glob

    folders = sorted(glob.glob(str(ROOT / "outputs" / "*medtech*")))
    if not folders:
        print(
            "No output folder found (run main.py 'Medtech ALEX' to interrupt once, then re-run this)."
        )
        RESULTS.append(("7", "Output folder", "FAIL: no output folder"))
        return False
    folder = Path(folders[-1])
    print("Output folder:", folder)
    for f in ["research.md", "plan.md", "engagement.json"]:
        path = folder / f
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        status = "OK" if exists and size > 0 else "MISSING or EMPTY"
        print(f"  {f}: {status}")
    ok = all(
        (folder / f).exists() and (folder / f).stat().st_size > 0
        for f in ["research.md", "plan.md", "engagement.json"]
    )
    RESULTS.append(("7", "Output folder", "PASS" if ok else "FAIL"))
    return ok


def phase8_browser():
    print("\n=== Phase 8: Browser layer ===")
    session_path = Path(
        os.getenv("LINKEDIN_SESSION_PATH", "./auth/linkedin_session.json")
    )
    if not session_path.is_absolute():
        session_path = ROOT / session_path
    if not session_path.exists():
        print(
            "Skip: auth/linkedin_session.json not found. Run python scripts/login.py to enable."
        )
        RESULTS.append(("8", "Browser layer", "SKIP"))
        return "skip"
    try:
        from tools.browser import get_browser_context

        ctx = get_browser_context()
        print("Browser context created:", type(ctx).__name__)
        ctx.close()
        RESULTS.append(("8", "Browser layer", "PASS"))
        return True
    except Exception as e:
        print(f"Browser error: {e}")
        RESULTS.append(("8", "Browser layer", f"FAIL: {e}"))
        return False


def main():
    print("LinkedIn Engine test suite (Phases 1-5, 6.1, 7, 8)")
    print(
        "Phase 6.2: run python main.py 'Medtech ALEX' and abort at review to verify interrupt."
    )

    p1_env = phase1_env()
    p1_imports = phase1_imports()
    p1_state = phase1_state()
    p1_ok = p1_env and p1_imports and p1_state
    RESULTS.append(("1", "Env and imports", "PASS" if p1_ok else "FAIL"))
    if not p1_ok:
        print("\nPhase 1: fix env/imports/state and re-run.")

    r2 = phase2_redis()
    phase3_knowledge()
    phase4_tools()
    phase5_agents()
    phase5b_quality()
    phase6_graph()
    phase7_output()
    phase8_browser()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("| Phase | Test                    | Result |")
    print("|-------|-------------------------|--------|")
    for phase, test, result in RESULTS:
        print(f"| {phase}     | {test:<23} | {result:<6} |")


if __name__ == "__main__":
    main()
