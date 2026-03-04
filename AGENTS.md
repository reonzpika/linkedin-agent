# AGENTS.md — ClinicPro LinkedIn Engine
**Stewarded by:** Cursor IDE AI Agent  
**Owner:** Dr Ryo Eguchi, ClinicPro  
**Last updated:** 2026-03-01  
**Status:** Living document — update this file whenever the system improves

---

## What This Repo Does

This is an autonomous LinkedIn content engine for Dr Ryo Eguchi, a practising Auckland GP and solo founder of ClinicPro. It researches NZ primary care topics, scouts LinkedIn engagement targets, drafts posts in Dr Ryo's "Insider GP" voice, and executes the Golden Hour posting protocol via Playwright.

The system is **chat-first**: the only user interface is Cursor chat. The linkedin-post-create skill prompts for topic/URL, runs scripts (plan, research, scout, draft), and presents each output in chat for approval or edit before proceeding. The only required human interaction is approval (or edit) at each step; execution is scheduled after draft approval.

**You are not just a code assistant. You are the autonomous operator of this system.** Read every file in `/knowledge/` before acting. Improve the system every time feedback is received.

---

## WAT Framework (How This Repo Is Organised)

This repo follows the WAT Framework. Before creating any new file, check whether it belongs to an existing layer.

| Layer | Directory / File | Purpose |
|---|---|---|
| Workflows | `/knowledge/` | Markdown SOPs, strategy, voice rules, NZ health context |
| Agents | `/agents/` | Agent logic (researcher, scout, architect, strategist); called by scripts with state dicts |
| Tools | `/tools/` | Browser, search, Crawl4AI, executor (Golden Hour posting) |
| Scripts | `/scripts/` | plan_from_url, research, scout, pick_targets, draft, assemble_session_state; run from chat skill |
| Outputs | `/outputs/` | Per-session folders (session folder contract above); never committed to git |
| Auth | `/auth/` | LinkedIn session files, never committed to git |
| Config | `config/model_config.json` | Model per agent (planner, researcher, architect, etc.); `requirements.txt` for packages |
| Temporary | `/temporary/` | approved.json, pending_posts.json for scheduling |
| Graph | `/graph/` | **Deprecated.** Legacy LangGraph; chat-first flow uses scripts and session folder |

**Rules:**
- Always check `/tools/` before writing a new utility script
- Always check `/knowledge/` before making any assumption about NZ health context, voice, strategy, or algorithmic rules
- Never scatter agent logic into `/tools/` or graph logic into `/agents/`
- Never create files outside this structure without flagging the reason in chat

---

## Session folder (chat-first flow)

Per-run handoff lives under `outputs/<session_id>/` (session_id = `YYYY-MM-DD_<slug>`). Scripts read and write these files; the skill orchestrates in chat.

| File | Written by | Purpose / shape |
|------|------------|-----------------|
| `input.json` | Skill (from chat) | `topic`, `url` (optional), `pillar_preference`, `angle`, `created_at` |
| `plan.json` | `scripts/plan_from_url.py` then user edit in chat | `plan` (text), `pillar`, `angle`, `summary_from_url` (if URL given) |
| `research.md` | `scripts/research.py` | Research summary (markdown) |
| `research_meta.json` | `scripts/research.py` | `target_urls`, `pillar` |
| `engagement.json` | `scripts/scout.py` (targets), optionally `scripts/pick_targets.py` (reduce to 6), then `scripts/draft.py` (comments) | `scout_targets`, `comments_list` |
| `draft_final.md` | `scripts/draft.py` | Post body only |
| `draft_meta.json` | `scripts/draft.py` | `first_comment`, `hashtags` |
| `session_state.json` | Assembly step (skill or `scripts/assemble_session_state.py`) | Dict for executor: `scout_targets`, `comments_list`, `post_draft`, `first_comment` |

Before execution, assembly builds `session_state.json` from the other session files so `execute_post.py` can read one file and run the Golden Hour protocol.

---

## Chat-Based Orchestration

**Chat is the only interface.** Do not run any script until the user has provided at least topic or URL. The skill must prompt for basic info (topic, URL, optional pillar and angle), create the session folder, and write `input.json` before running `scripts/plan_from_url.py`. Run the full post-creation flow via the linkedin-post-create skill **in Agent mode** so that plan and draft approval gates are respected.

**Entry points:**

- **linkedin-post-create** (skill): Only way to start a new post. Prompts for topic/URL and optional pillar/angle; creates session folder and `input.json`; runs `scripts/plan_from_url.py` → present plan in chat → after approval, runs `scripts/research.py` → present research → runs `scripts/scout.py` then, if more than 6 targets, `scripts/pick_targets.py` then `scripts/draft.py` → present draft in chat → after approval, runs `scripts/assemble_session_state.py` then schedules via `tools/scheduler.schedule_execution`. Session state is written so `execute_post.py` can run later.
- **execute_post.py**: Loads `outputs/[session_id]/session_state.json`, runs Golden Hour via `tools/executor.executor_run`. Called by OS scheduler or manually (linkedin-post-execute skill).
- **main.py** / **prepare_post.py**: Deprecated. Use the skill and scripts instead.

**Scripts** (run from repo root with `--session-dir outputs/<session_id>`):

- `scripts/plan_from_url.py`: Reads input.json, optionally fetches URL; Claude (planner) produces plan.json.
- `scripts/research.py`: Reads input + plan; runs Researcher agent; writes research.md, research_meta.json. On dehallucination, writes research_dehallucination.txt and exits non-zero.
- `scripts/scout.py`: Runs Scout agent; writes engagement.json (scout_targets only, up to 30).
- `scripts/pick_targets.py`: When scout_targets > 6, runs Picker (Claude) to choose best 6; overwrites scout_targets in engagement.json. Run after scout, before draft.
- `scripts/draft.py`: Runs Architect then Strategist; writes draft_final.md, draft_meta.json, updates engagement.json with comments_list. Optional `--revision-feedback` for regenerate pass.
- `scripts/assemble_session_state.py`: Builds session_state.json from session files for execute_post.py.

**Cursor skills** (in `.cursor/skills/`):

- **linkedin-post-create**: Trigger "create linkedin post", "draft post about". Orchestrates prompt → plan → research → scout → draft → review in chat → assemble → schedule. See skill file for phases.
- **linkedin-post-execute**: Manual "execute [session_id]" or invoked by scheduler. Runs `execute_post.py`, reports results. Requires session_state.json (assembled by linkedin-post-create).
- **linkedin-agent-improve**: Feedback on voice, structure, or facts. Maps to knowledge file, derives rule, updates file (Self-Improvement Protocol).

**Agent roles** (called by scripts with state dicts):

- **Scout**: Discovers 6 Golden Hour targets (personal feed + hashtag fallback). Returns scout_targets only. Uses `tools/browser.scrape_personal_feed` and `scrape_hashtag_posts`.
- **Architect**: Drafts post_draft, first_comment, hashtags, 6 comments. Uses voice_profile, algorithm_sop, hashtag_library; accepts optional revision_feedback in state.

---

## Human Interaction Model

The human (Dr Ryo) interacts with this system only through chat. Every script output (plan, research, draft) is presented in chat for approval or edit before the next step runs.

### Approval gates (in chat)

- **Plan**: After `plan_from_url.py`, present plan; user approves or edits plan.json. Do not run research until approved.
- **Research**: After `research.py`, present research summary; user may approve or skip to scout/draft.
- **Draft**: After `draft.py`, present post + hashtags + first comment + 6 Golden Hour comments; user approves, requests edits (skill updates files and shows diff), or asks to "Regenerate" (skill re-runs draft with `--revision-feedback`).
- **Scheduling**: After draft approval, skill runs assemble then schedule; user sees confirmation.

### Autonomous (no approval required)

- Running scripts when the user has approved the previous step
- Playwright selector fixes in `tools/browser.py` (announce in chat)
- Updating `/knowledge/` files from feedback (announce in chat first; see Self-Improvement Protocol)
- Writing to `/outputs/` and `temporary/`

### Require explicit approval

- Changes to core strategic positioning in `clinicpro_strategy.md`
- Installing new Python packages
- Modifying `.env.example` or new credentials
- Git commit or push

### Never do without explicit instruction

- Post to LinkedIn outside `tools/executor.executor_run` (called by execute_post.py after approval)
- Log in to LinkedIn if a valid session file exists
- Delete files in `/outputs/` or `/auth/`
- Expose or log API keys or credentials
- Mention Inbox AI features, ClinicPro R&D roadmap, or funded development timelines in any draft

---

## Self-Improvement Protocol

This is the most important section. The system must improve itself based on feedback. Do not keep a passive log. Update the system file that governs the behaviour that was corrected.

### When Dr Ryo gives feedback or a correction

1. Identify which tier the feedback belongs to (see table below)
2. Derive a clear, specific rule from the feedback
3. Announce the change in chat with one line before applying it:
   > "Updating `voice_profile.md`: adding rule that hooks must open with a specific clinical observation, not a statistic. Applying now."
4. Update the relevant file immediately — do not wait for approval
5. Apply the updated rule to the current session if drafting is still in progress

### Feedback tiers and target files

| Feedback type | Examples | Update target |
|---|---|---|
| Voice or tone | "Too generic", "sounds like a press release", "passive voice", "hook is weak" | `knowledge/voice_profile.md` |
| Post structure | "Too long", "ended with a question again", "systemic point is buried" | `knowledge/voice_profile.md` + `knowledge/algorithm_sop.md` |
| Content pillar direction | "Stop framing this as a GP problem, it is a practice manager problem", "don't mention user numbers in Pillar 2" | `knowledge/clinicpro_strategy.md` |
| Algorithmic rules | "Golden Hour comments are too long", "hashtags wrong again" | `knowledge/algorithm_sop.md` |
| NZ health facts | "That policy changed", "that is not how PHOs work in NZ" | `knowledge/nz_health_context.md` |
| Agent behaviour | "Strategist is approving posts that are too salesy", "Researcher is using US health terminology" | The relevant file in `/agents/` |
| Playwright or tooling | "That selector broke again", "search results are not NZ-specific enough" | The relevant file in `/tools/` |
| Dehallucination gaps | "You should have asked me before stating that", "that clinical claim was wrong" | `knowledge/dehallucination_triggers.md` |

### Keep AGENTS.md current

When you update any `/knowledge/` or `/agents/` file as a result of feedback, check whether `AGENTS.md` also needs updating to reflect the new behaviour. The goal is that `AGENTS.md` always describes the current state of the system, not its original state. If a new protocol, constraint, or pattern is introduced anywhere in the repo, add a corresponding note to the relevant section of this file within the same session.

---

### Rule derivation standard

When deriving a rule from feedback, write it as a specific, testable constraint — not a vague instruction.

**Weak (do not write this):**
> Be more specific in hooks.

**Strong (write this):**
> Hook must open with a named NZ clinical system, workflow step, or infrastructure component (e.g. "Medtech Cloud", "HealthLink referral", "12-month prescription queue") — never with a rhetorical question or a statistic without clinical context.

### What counts as a strategic change requiring approval

If the proposed rule change would alter Dr Ryo's public positioning, contradict an existing pillar, or remove an existing constraint rather than add a new one, flag it in chat and wait for confirmation before applying.

---

## Shared State and Session Folder

**Session folder** (`outputs/<session_id>/`) is the handoff between steps. Scripts read and write the files listed in the Session folder table above. No script should invent new files without documenting them in AGENTS.md.

**Agents** (researcher, scout, architect, strategist) receive a state dict built from session files (and optional keys like revision_feedback). They return updates that the calling script merges and writes back to the session folder. For type reference, `graph/state.py` still defines `LinkedInContext`; agents may use it for type hints. No agent should invent state keys that are not written to or read from the session folder (or passed explicitly by the script).

---

## Knowledge Directory Rules

`/knowledge/` is the system's strategic memory. Agents read it before acting. Cursor updates it when the system improves.

| File | Purpose | Who reads it | Who may update it |
|---|---|---|---|
| `clinicpro_strategy.md` | Three content pillars, audience priorities, 90-day plan | Researcher, Architect | Cursor (strategic changes require approval) |
| `voice_profile.md` | Insider GP voice rules, banned terms, structural rules, pre-R&D constraints | Architect, Strategist | Cursor (announce in chat first) |
| `algorithm_sop.md` | 2025 LinkedIn algorithm rules, Golden Hour protocol, hashtag limits | Architect, Strategist, Scout | Cursor (announce in chat first) |
| `nz_health_context.md` | NZ health system glossary, PHO structures, Medtech context | Researcher | Cursor (announce in chat first) |
| `hashtag_library.md` | Approved hashtags and tagging rules | Architect | Cursor (announce in chat first) |
| `dehallucination_triggers.md` | Sensitive topics requiring human clarification before drafting | Researcher, Architect | Cursor (announce in chat first) |

**Rules:**
- Agents may extend and append to knowledge files freely
- Agents must never contradict an existing rule without flagging it as a strategic change
- If a knowledge file conflicts with a user instruction given in chat, the chat instruction wins for the current session — then update the knowledge file to reflect the correction permanently

---

## Initialisation (When Starting a New Post)

Before running any script, the skill must prompt the user for basic info (topic and/or URL, optional pillar and angle) and write `input.json` in the session folder. Scripts assume the session folder and required files exist as per the Session folder table.

Agents (when invoked by scripts) read from `knowledge/` as needed: voice_profile, algorithm_sop, nz_health_context, dehallucination_triggers, clinicpro_strategy, hashtag_library. Scout reads existing `engagement.json` files under `outputs/` to avoid repeating targets.

---

## LinkedIn Authentication Protocol

1. Check for a valid session file at `LINKEDIN_SESSION_PATH` (default: `./auth/linkedin_session.json`)
2. If the session file exists and is valid, use it — never attempt credential login unnecessarily
3. If the session file is absent or expired, instruct Dr Ryo to run `python scripts/login.py` manually and wait
4. After a successful manual login, save the new session file automatically
5. Never store or log LinkedIn credentials in any output file, log, or chat message

---

## Observability (LangSmith)

Optional. When `LANGSMITH_API_KEY` is set, LangSmith can trace LLM calls if the scripts or agents are instrumented. If absent, the system runs without tracing. Use traces to debug script/agent behaviour and apply the Self-Improvement Protocol when patterns emerge.

---

## Failure and Recovery Protocol

### Playwright failures and reliability

LinkedIn's UI is dynamic. Element references change between sessions, modals appear unexpectedly, and hidden file inputs break standard automation patterns. The following rules are mandatory in `tools/browser.py`:

- Call `dismiss_modal_if_present()` before every major action — LinkedIn frequently displays "Share your update", cookie, and notification modals that block interactions
- Never hardcode CSS selectors — always use semantic queries or accessibility tree lookups so the automation adapts when LinkedIn updates its UI
- Always re-capture a page snapshot before interacting with any element — never use stale references from a previous step
- Verify each action succeeded before moving to the next one
- When a selector fails, attempt one autonomous fix: update the selector in `browser.py` and announce in chat: "LinkedIn UI change detected. Updated selector for [action name]."
- If the fix fails after one attempt, report the error in chat and stop; do not crash silently

### Dehallucination triggers

When `scripts/research.py` detects a sensitive topic, it writes the clarification question to `research_dehallucination.txt` and exits non-zero. The skill must show the question in chat and wait for the user's answer before re-running research (or proceeding with the answer recorded).

**When research.py exits with dehallucination:** The skill shows the contents of `research_dehallucination.txt` in chat. The user provides the answer in chat. The agent writes that answer to `research_dehallucination_answer.txt` in the session folder and re-runs `scripts/research.py --session-dir <path>`. No code change is required; the script and researcher already support reading the answer file.

If the same trigger recurs, update `dehallucination_triggers.md` with the confirmed correct information.

### Strategist revision loops

`scripts/draft.py` runs Architect then Strategist with up to two revision loops. If the draft still fails guardrails, the script still writes the latest draft to the session folder; the skill presents it in chat with a note so Dr Ryo can override or request "Regenerate" with feedback.

---

## Tools layer and API keys

The Researcher uses Tavily (NZ health search), Crawl4AI (local, free, full-page content), and Claude Haiku for summarisation. `research_with_agent` runs Tavily search, Crawl4AI fetch, then Claude Haiku; `fetch_page_content` uses Crawl4AI AsyncWebCrawler with `headless=True` (separate from the headed LinkedIn browser in `browser.py`). FIRECRAWL_API_KEY is no longer required. If Phase 4 fails with "Tavily: 0 results", "Crawl4AI returned 0 characters", or "research_with_agent returned empty", fix the tools first: confirm TAVILY_API_KEY (app.tavily.com), ANTHROPIC_API_KEY, and Crawl4AI install (run `python -m crawl4ai-download` if browser not installed), then re-run the test suite. On Windows, Crawl4AI uses `verbose=False` in `tools/search.py` to avoid console Unicode (charmap) errors; if issues persist, set `PYTHONIOENCODING=utf-8`.

---

## Output quality tests

Before a live LinkedIn run, run the full test suite so output quality is checked: `python scripts/run_tests.py`. Phase 5 runs the agent pipeline (Researcher, Architect, Strategist) and Phase 5b runs quality assertions: no engagement bait in first_comment or comments_list, ALEX not described as crashing, Scout targets have post_url and required structure. The Strategist guardrail rejects engagement-bait phrases (e.g. "What's your experience?") in first_comment and comments_list. If quality tests fail, fix the agents or knowledge and re-run until they pass.

---

## Output Folder Convention

Session folder layout is defined in the **Session folder (chat-first flow)** table above. Key files: input.json, plan.json, research.md, research_meta.json, engagement.json, draft_final.md, draft_meta.json, session_state.json (after assembly).

**Rules:**
- Session id = `YYYY-MM-DD_<slug>`; slug lowercase, hyphenated, max 30 characters. Collision: use suffix -2, -3, etc.
- Never overwrite an existing session folder; create a new one with an incremented suffix if needed
- Scout reads all existing `engagement.json` files (post_url from scout_targets) to avoid repeating the same posts

---

## NZ English and Language Rules

All content generated by this system must use New Zealand English spelling and conventions. This applies to:

- All files in `/knowledge/`
- All drafted LinkedIn posts and comments
- All code comments and docstrings
- All chat announcements from Cursor

**Key spelling conventions:**
- "organise" not "organize"
- "analyse" not "analyze"
- "colour" not "color"
- "centre" not "center"
- "programme" not "program" (except when referring to software)
- "licence" (noun) vs "license" (verb)

**Never use an em dash (—) in any generated content.** Use a comma, a full stop, or rewrite the sentence instead.

---

## Code Style and Conventions

- Python 3.11+
- Agent files may import `LinkedInContext` from `graph/state.py` for type hints; scripts pass plain dicts
- All tool and script entry points must have docstrings (inputs, outputs, failure behaviour)
- Use `python-dotenv` to load `.env`; never hardcode credentials
- Type hints required on function signatures
- Format Python with `black`; run `mypy` on modified files before finishing

---

## Safety Boundaries Summary

| Action | Permission |
|---|---|
| Read any file in `/knowledge/` | Always permitted |
| Write to `/outputs/` | Always permitted |
| Update `/knowledge/` files (non-strategic) | Permitted — announce in chat first |
| Fix Playwright selectors autonomously | Permitted — announce in chat first |
| Run `black` and `mypy` | Always permitted |
| Update core strategic positioning | Permitted — announce in chat first |
| Change script or skill orchestration | Permitted — announce in chat first |
| Install new Python packages | Always permitted |
| Post to LinkedIn | Only via execute_post.py (tools/executor.executor_run) after draft approved in chat |
| Commit or push to git | Permitted — announce in chat first |
| Delete files | Permitted — announce in chat first |
| Log or expose credentials | Never |

---

## Living Document Rule

This file must stay current. When the system improves, update the relevant section here too.

If a new pattern, constraint, or protocol is added to any `/knowledge/` or `/agents/` file as a result of feedback, reflect that change in the appropriate section of this file within the same session.

The goal is that any future agent — or any future version of Cursor — can read this file alone and understand exactly how this system works, what it is allowed to do, and how it is expected to improve itself over time.
