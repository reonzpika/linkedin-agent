# AGENTS.md — ClinicPro LinkedIn Engine
**Stewarded by:** Cursor IDE AI Agent  
**Owner:** Dr Ryo Eguchi, ClinicPro  
**Last updated:** 2026-03-01  
**Status:** Living document — update this file whenever the system improves

---

## What This Repo Does

This is an autonomous LinkedIn content engine for Dr Ryo Eguchi, a practising Auckland GP and solo founder of ClinicPro. It researches NZ primary care topics, scouts LinkedIn engagement targets, drafts posts in Dr Ryo's "Insider GP" voice, and executes the Golden Hour posting protocol via Playwright.

The system is designed for 99% autonomy. The only required human interaction is a single consolidated review of the post and comments before execution. Everything else — research, discovery, drafting, critique, reflection, and self-improvement — runs without interruption.

**You are not just a code assistant. You are the autonomous operator of this system.** Read every file in `/knowledge/` before acting. Improve the system every time feedback is received.

---

## WAT Framework (How This Repo Is Organised)

This repo follows the WAT Framework. Before creating any new file, check whether it belongs to an existing layer.

| Layer | Directory / File | Purpose |
|---|---|---|
| Workflows | `/knowledge/` | Markdown SOPs, strategy, voice rules, NZ health context |
| Agents | `/agents/` | Individual agent node logic |
| Tools | `/tools/` | Single-purpose Python scripts (browser, search, Crawl4AI) |
| Graph | `/graph/` | LangGraph orchestration, state schema, persistence |
| Outputs | `/outputs/` | Per-session records, never committed to git |
| Auth | `/auth/` | LinkedIn session files, never committed to git |
| Config | `requirements.txt` | Full dependency list — check before adding any new package |
| Temporary | `/temporary/` | Review/approval markers and pending queue for chat orchestration (see below) |

**Rules:**
- Always check `/tools/` before writing a new utility script
- Always check `/knowledge/` before making any assumption about NZ health context, voice, strategy, or algorithmic rules
- Never scatter agent logic into `/tools/` or graph logic into `/agents/`
- Never create files outside this structure without flagging the reason in chat

---

## Chat-Based Orchestration

The system supports Cursor IDE orchestration via chat. Two entry points exist:

- **`main.py`**: Full graph with human_review interrupt; run interactively (review in terminal, resume with APPROVE or edits).
- **`prepare_post.py`**: Runs planner through strategist then exits. Writes outputs and a marker to `temporary/review_ready.json`. No pause; Cursor (or a skill) reads the marker and runs the review loop in chat. Execution is then scheduled via OS task calling `execute_post.py [session_id]`.

**2-script design:**

- **`prepare_post.py`**: Research, scout, draft, strategist (with revision loop). Saves to `outputs/[session_id]/` and writes `temporary/review_ready.json`. Used when orchestration is chat-driven.
- **`execute_post.py`**: Loads `outputs/[session_id]/session_state.json`, runs Golden Hour comments then main post (via `graph.workflow.executor_run`). Called by OS scheduler or manually.

**`temporary/` folder contracts:**

- `temporary/review_ready.json`: Written by `prepare_post.py` when draft is ready. Signals Cursor/skill to show review.
- `temporary/approved.json`: Written by the skill after user approves; holds session_id and scheduled time.
- `temporary/pending_posts.json`: Queue of scheduled sessions; updated when a post is executed or cancelled.

**Cursor skills** (in `.cursor/skills/`):

- **linkedin-post-create**: Trigger "create linkedin post", "draft post about". Pre-flight, run `prepare_post.py`, review loop in chat, schedule via `tools/scheduler.schedule_execution`, write approved/pending markers.
- **linkedin-post-execute**: Trigger manual "execute [session_id]" or invoked by OS scheduler. Runs `execute_post.py`, reports results.
- **linkedin-agent-improve**: Trigger feedback on voice, structure, or facts. Maps to knowledge file, derives rule, updates file (Self-Improvement Protocol).

**Agent roles (current):**

- **Scout**: Discovers 6 Golden Hour targets via personal feed scraping (primary) and hashtag scraping (fallback). Does not draft comments; returns `scout_targets` only. Uses `tools/browser.scrape_personal_feed` and `scrape_hashtag_posts`.
- **Architect**: Drafts main post, first_comment, 3–4 hashtags, and exactly 6 Golden Hour comments (one per scout target). Uses target snippets to tailor comments; comment order matches target order.

---

## Human Interaction Model

The human (Dr Ryo) interacts with this system only through chat. The system must be designed around this constraint at every level.

### The only mandatory interrupt point

After the Strategist agent approves the draft post and comments, call `interrupt()` and present the following for review in a single consolidated block:

```
REVIEW REQUIRED

POST DRAFT:
[full post text]

HASHTAGS: [list]
FIRST COMMENT: [URL or placeholder]

PRE-ENGAGEMENT COMMENTS (Golden Hour):
1. [target name + post URL + comment text]
2. ...
6. ...

Type APPROVE to proceed, or paste your corrections below.
```

Do not interrupt at any other point unless a failure condition is met (see Failure Protocol below).

### Autonomous decision-making

The following actions require no human approval:

- All research, web search, and NZ health context grounding
- LinkedIn discovery and target selection
- Post drafting and Strategist critique loops
- Playwright selector fixes when LinkedIn UI changes
- Writing to `/outputs/` after a completed run
- Updating `/knowledge/` files (with a one-line chat announcement — see Self-Improvement Protocol)
- Appending to `graph/state.py` logs via the `operator.add` reducer

### Actions that require human approval before proceeding

- Any change to core strategic positioning in `clinicpro_strategy.md`
- Any change to the agent squad roles or the LangGraph DAG structure
- Installing new Python packages
- Modifying `.env.example` to add new credentials
- Any git push or commit

### Never do without explicit instruction

- Post to LinkedIn outside the executor node
- Log in to LinkedIn using credentials if a valid session file exists
- Delete any file in `/outputs/` or `/auth/`
- Expose or log API keys or LinkedIn credentials anywhere
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

## Shared State Is the Single Source of Truth

`graph/state.py` defines the `LinkedInContext` TypedDict. This is the canonical data contract for the entire system.

**Rules:**
- No agent may invent its own variables outside the state schema
- No agent may read data from another agent's output directly — all data flows through state
- The `logs` field uses `operator.add` as its reducer and is append-only — never overwrite it
- If a new field is genuinely needed, add it to `LinkedInContext` first, then reference it in the agent

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

## Initialisation Protocol (Every Run)

Before every workflow run, the entry node must output this exact phrase:

> "Let's first understand the problem, extract relevant variables and their corresponding numerals, and make a plan."

Then read the following files before any agent acts:
1. `knowledge/voice_profile.md`
2. `knowledge/algorithm_sop.md`
3. `knowledge/nz_health_context.md`
4. `knowledge/dehallucination_triggers.md`
5. The most recent session folder in `/outputs/` (to check historical engagement targets)

---

## LinkedIn Authentication Protocol

1. Check for a valid session file at `LINKEDIN_SESSION_PATH` (default: `./auth/linkedin_session.json`)
2. If the session file exists and is valid, use it — never attempt credential login unnecessarily
3. If the session file is absent or expired, instruct Dr Ryo to run `python scripts/login.py` manually and wait
4. After a successful manual login, save the new session file automatically
5. Never store or log LinkedIn credentials in any output file, log, or chat message

---

## Observability (LangSmith)

LangSmith is an optional but recommended observability layer. When `LANGSMITH_API_KEY` is present in the environment, the compiled LangGraph graph is wrapped with LangSmith tracing. This gives a full trace of every node execution, every LLM call, and every tool invocation — which is how you debug why a Strategist loop failed twice or why the Researcher picked the wrong pillar.

If `LANGSMITH_API_KEY` is absent, the system runs without tracing. No warning, no crash.

Use LangSmith traces to inform self-improvement decisions. If a trace reveals a consistent failure pattern (e.g., the Researcher consistently misidentifies Pillar 3 topics as Pillar 1), derive a rule from that pattern and apply the Self-Improvement Protocol.

---

## Failure and Recovery Protocol

### Playwright failures and reliability

LinkedIn's UI is dynamic. Element references change between sessions, modals appear unexpectedly, and hidden file inputs break standard automation patterns. The following rules are mandatory in `tools/browser.py`:

- Call `dismiss_modal_if_present()` before every major action — LinkedIn frequently displays "Share your update", cookie, and notification modals that block interactions
- Never hardcode CSS selectors — always use semantic queries or accessibility tree lookups so the automation adapts when LinkedIn updates its UI
- Always re-capture a page snapshot before interacting with any element — never use stale references from a previous step
- Verify each action succeeded before moving to the next one
- When a selector fails, attempt one autonomous fix: query the accessibility tree for the correct current element, update the selector in `browser.py`, log the change to `state["logs"]`, and announce in chat:
  > "LinkedIn UI change detected. Updated selector for [action name]. Logged to browser.py."
- If the fix fails after one attempt, set `error_state` and call `interrupt()` for human takeover
- Never crash silently

### Dehallucination triggers

If a sensitive topic is detected during research or drafting:
1. Log the trigger name and timestamp to `state["logs"]`
2. Call `interrupt()` immediately with the specific clarification question from `dehallucination_triggers.md`
3. Do not proceed with drafting until the human responds
4. After the human responds, log their answer and resume
5. If the trigger fires repeatedly for the same topic, update `dehallucination_triggers.md` with the confirmed correct information so future runs do not need to ask again

### Strategist revision loops

If the Strategist rejects a draft twice and the third revision still fails:
1. Do not loop again
2. Pass the draft to the human review interrupt with a clear note explaining which guardrail keeps failing
3. Let Dr Ryo decide whether to override or restart

### Redis checkpoint failures

**Production requires Redis.** The real system must not silently run without it. Interrupt/resume and Time Travel Debugging depend on the checkpointer. When Redis is unavailable at startup (e.g. local test without Redis running), the graph may compile without a checkpointer so the test suite can run; that fallback is for testing only.

If Redis is unavailable at startup:
1. Warn in chat: "Redis unavailable. Running without persistence. Time Travel Debugging disabled for this session."
2. Proceed with the run using in-memory state only
3. Save the final session state to `/outputs/[session-folder]/session_state.json` as a manual backup

---

## Tools layer and API keys

The Researcher uses Tavily (NZ health search), Crawl4AI (local, free, full-page content), and Claude Haiku for summarisation. `research_with_agent` runs Tavily search, Crawl4AI fetch, then Claude Haiku; `fetch_page_content` uses Crawl4AI AsyncWebCrawler with `headless=True` (separate from the headed LinkedIn browser in `browser.py`). FIRECRAWL_API_KEY is no longer required. If Phase 4 fails with "Tavily: 0 results", "Crawl4AI returned 0 characters", or "research_with_agent returned empty", fix the tools first: confirm TAVILY_API_KEY (app.tavily.com), ANTHROPIC_API_KEY, and Crawl4AI install (run `python -m crawl4ai-download` if browser not installed), then re-run the test suite. On Windows, Crawl4AI uses `verbose=False` in `tools/search.py` to avoid console Unicode (charmap) errors; if issues persist, set `PYTHONIOENCODING=utf-8`.

---

## Output quality tests

Before a live LinkedIn run, run the full test suite so output quality is checked: `python scripts/run_tests.py`. Phase 5 runs the agent pipeline (Researcher, Architect, Strategist) and Phase 5b runs quality assertions: no engagement bait in first_comment or comments_list, ALEX not described as crashing, Scout targets have post_url and required structure. The Strategist guardrail rejects engagement-bait phrases (e.g. "What's your experience?") in first_comment and comments_list. If quality tests fail, fix the agents or knowledge and re-run until they pass.

---

## Output Folder Convention

Every completed run saves to:

```
outputs/YYYY-MM-DD_[topic-slug]/
├── research.md         # Researcher agent output
├── plan.md             # PS+ plan from entry node
├── draft_final.md      # Approved post after human review
├── engagement.json     # Scout targets and Golden Hour comments
└── session_state.json  # Full LangGraph state snapshot
```

**Rules:**
- Topic slug must be lowercase, hyphenated, max 30 characters (e.g. `medtech-alex-update`, `admin-burden-workforce`)
- Never overwrite an existing session folder — create a new one with an incremented suffix if needed (e.g. `2026-02-27_medtech-alex-2`)
- The Scout agent reads all existing `engagement.json` files (post_url from scout_targets) to avoid repeating the same posts. Scout uses personal feed and hashtag scraping (see `tools/browser.py`), not search API

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
- All agent files must import `LinkedInContext` from `graph/state.py` — no local state definitions
- All tool functions must have a docstring explaining inputs, outputs, and failure behaviour
- Use `python-dotenv` to load `.env` — never hardcode credentials
- Type hints required on all function signatures
- Use `loguru` for logging (not `print`) so logs flow cleanly into the LangGraph state
- Format all Python files with `black` before finishing any task
- Run `mypy` on modified files before finishing any task

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
| Change LangGraph DAG structure | Permitted — announce in chat first |
| Install new Python packages | Always permitted |
| Post to LinkedIn | Only via executor node after human review interrupt |
| Commit or push to git | Permitted — announce in chat first |
| Delete files | Permitted — announce in chat first |
| Log or expose credentials | Never |

---

## Living Document Rule

This file must stay current. When the system improves, update the relevant section here too.

If a new pattern, constraint, or protocol is added to any `/knowledge/` or `/agents/` file as a result of feedback, reflect that change in the appropriate section of this file within the same session.

The goal is that any future agent — or any future version of Cursor — can read this file alone and understand exactly how this system works, what it is allowed to do, and how it is expected to improve itself over time.
