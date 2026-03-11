# Handover: LinkedIn Post Review System

## Context

You are the autonomous operator of the ClinicPro LinkedIn Engine for Dr Ryo Eguchi.
Read AGENTS.md fully before proceeding. This prompt hands over a new system designed
in a separate session. Your first task is to produce an implementation plan and present
it in chat for approval before touching any files.

---

## What was designed

A semi-automated post review and improvement workflow. After each LinkedIn post has
been live for 48 hours, this system:

1. Scrapes live metrics from the published post's analytics page (Playwright)
2. Checks whether our 6 Golden Hour pre-engagement comments received replies
3. Scores performance against benchmarks for a small NZ primary care personal profile
4. Identifies what drove or killed reach (hook, structure, topic, Golden Hour quality)
5. Proposes specific, testable updates — either to knowledge files (knowledge updates)
   or to system behaviour (system updates)
6. Presents all proposed updates to Dr Ryo in bulk for approve/reject before applying

---

## Files to implement

Six files have been designed and are attached to this conversation.

| File | Destination in repo |
|---|---|
| `agents/analyst.py` | `agents/analyst.py` |
| `scripts/collect_analytics.py` | `scripts/collect_analytics.py` |
| `scripts/analyse_performance.py` | `scripts/analyse_performance.py` |
| `.cursor/skills/linkedin-post-review` | `.cursor/skills/linkedin-post-review` |
| `knowledge/performance_history.md` | `knowledge/performance_history.md` |
| `AGENTS_updates.md` | Apply to `AGENTS.md` then delete |

---

## Key design decisions to understand before planning

**Analytics page navigation:**
LinkedIn analytics are on a dedicated URL (`/posts/<slug>/analytics/`), not a modal.
`collect_analytics.py` navigates there directly and falls back to clicking "View analytics"
if redirected. Selectors are expected to break every 2-4 weeks — the script detects
this with a `selector_stale` flag when all metrics return zero.

**Headed mode required:**
`tools/browser.get_browser_context()` must use headed mode (headless=False).
LinkedIn's fingerprinting detects headless Chromium. Verify this in `tools/browser.py`
before implementing — if it is currently headless, flag this as a required change.

**Saves and sends are free metrics:**
Both became available on personal profile posts in September 2025 without Premium.
Both are included in analytics collection and scoring.

**Proposed update types:**
The system produces two categories of proposed update in `proposed_updates.json`:
- Knowledge updates: rule changes to markdown files, applied via str_replace
- System updates: behavioural changes to scripts, agents, or skill files, requiring
  Cursor agent mode with a read-first / plan-first / approve-then-act protocol

**Update caps:**
Maximum 5 total updates per review, with a maximum of 2 system updates.

**System update threshold:**
The analyst only raises system updates when the same gap appears across at least
2 reviews, or when a single review shows a complete mechanism failure.

---

## System update protocol (critical — add to AGENTS.md)

When implementing an approved system update, Cursor must follow this protocol:

1. Read all files in the `read_before_planning` list in the update entry
2. Read AGENTS.md, all files in `.cursor/skills/`, and all files in `agents/`
3. Reason about which layer of the system is the best place to make the change
4. Produce an implementation plan in chat stating which layer was chosen and why
   the other layers were ruled out
5. Wait for Dr Ryo's explicit approval before touching any files
6. Announce every file change before applying it
7. After implementation, confirm the verification condition in the update entry was met
8. Update `knowledge/performance_history.md`: move the system update row from
   "Open System Updates" to "Implemented System Updates"

This protocol applies to every system update without exception, regardless of size.

---

## Your task before touching any files

Read every attached file carefully. Then produce an implementation plan in chat covering:

1. **Dependency check** — does anything in the new files import from modules that do
   not exist yet? List any missing dependencies. Check `config/model_config.json` for
   missing agent entries ("analyst" — confirm "picker" also exists).

2. **Integration check** — do the new scripts follow the same patterns as existing
   scripts (argparse, sys.path, dotenv, ROOT, session folder contract)? Flag deviations.

3. **Browser layer check** — `collect_analytics.py` requires headed mode. Check
   `tools/browser.py`. If `get_browser_context()` uses headless=True, flag this as
   a required change and include it in the implementation plan.

4. **AGENTS.md update plan** — list the exact sections in AGENTS.md that need
   updating, based on `AGENTS_updates.md`, plus the new "System Update Protocol"
   section described above.

5. **Execution order** — in what order should the files be added to avoid import
   errors or broken references during rollout?

6. **Risks or gaps** — anything in the design that needs clarification or a small
   fix before implementation.

Present the plan clearly in chat. Wait for approval before making any changes.

---

## Implementation rules (apply after approval)

- Announce every file change in chat before applying it
- Use NZ English spelling in all content (no em dashes)
- Never scatter agent logic into tools/ or script logic into agents/
- After all files are in place, add a reminder at the end of the next
  linkedin-post-create session: "Remember to run the 48-hour review: 'review post [session_id]'"
- Update AGENTS.md last, after all other files are confirmed in place
- Do not commit to git until Dr Ryo explicitly requests it

---

## One manual step required after implementation

Add `"analyst"` to `config/model_config.json` using the same format as existing entries.
Confirm whether `"picker"` already exists — if not, add it too.
Suggested model for both: same as `"architect"` (check current config).

---

## Definition of done

- [ ] All 6 files in place in repo
- [ ] `config/model_config.json` updated with analyst (and picker if missing)
- [ ] AGENTS.md updated with all additions from `AGENTS_updates.md`
- [ ] AGENTS.md includes new "System Update Protocol" section
- [ ] `AGENTS_updates.md` deleted from repo root
- [ ] `tools/browser.py` confirmed to use headed mode (headless=False)
- [ ] Skill triggers correctly in Cursor chat ("review post [session_id]")
- [ ] No import errors: `python scripts/collect_analytics.py --help`
- [ ] No import errors: `python scripts/analyse_performance.py --help`
