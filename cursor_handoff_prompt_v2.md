# Cursor IDE Handoff Prompt: ClinicPro LinkedIn Engine
**Version:** 2.0  
**Date:** February 2026  
**Target:** Cursor IDE AI Agent (built-in model)  
**Repo state:** Greenfield (nothing exists yet)

---

## Your Mission

Scaffold and fully implement the ClinicPro LinkedIn Engine from scratch. This is an autonomous LinkedIn content system for Dr Ryo Eguchi, a practising Auckland GP and solo founder of ClinicPro. Your output must be a working, runnable repository with zero placeholder files. Every file you generate must be complete and functional.

This is a self-improving system. The `/knowledge/` directory is the system's strategic memory and must be kept current as the system learns. See `AGENTS.md` for the full self-improvement protocol.

Read this entire document before writing a single line of code.

---

## Initialisation Protocol (Mandatory)

Before every run of the main workflow, the entry node must trigger Plan-and-Solve (PS+) prompting with this exact phrase:

> "Let's first understand the problem, extract relevant variables and their corresponding numerals, and make a plan."

This is non-negotiable. It prevents premature drafting and grounds the agent squad in the current session's context.

---

## Repository Structure to Scaffold

Create the following directory and file structure in the current directory. Every file listed must be generated with complete, working content — no stubs, no TODOs.

```
clinicpro-linkedin-agent/
├── AGENTS.md                   # Root-level agent operating instructions [create first]
├── .cursorrules                # Cursor-specific repo rules
├── .env.example                # Environment variable template
├── requirements.txt            # Full Python dependency list
├── main.py                     # Workflow entry point
├── config/
│   ├── model_config.json       # Claude model assignments per agent
│   └── playwright_settings.py  # Headed mode and bot-detection bypass settings
├── knowledge/                  # WAT Workflows layer — Markdown SOPs and strategy
│   ├── clinicpro_strategy.md
│   ├── voice_profile.md
│   ├── algorithm_sop.md
│   ├── nz_health_context.md
│   ├── hashtag_library.md
│   └── dehallucination_triggers.md
├── agents/                     # WAT Agents layer — individual node logic
│   ├── researcher.py
│   ├── scout.py
│   ├── architect.py
│   └── strategist.py
├── graph/                      # LangGraph orchestration
│   ├── state.py
│   ├── workflow.py
│   └── persistence.py
├── tools/                      # WAT Tools layer — single-purpose Python scripts
│   ├── browser.py
│   └── search.py
├── auth/
│   └── .gitkeep                # LinkedIn session files live here — never commit
├── scripts/
│   └── login.py                # Manual LinkedIn session refresh script
└── outputs/
    └── .gitkeep                # Per-session outputs — never commit
```

---

## File Specifications

### `AGENTS.md` (create this first, before any other file)

Place the provided `AGENTS.md` content at the root of the repository. This file governs how you (Cursor) behave throughout the entire scaffolding and all future sessions. Read it immediately after creating it and apply its rules for the rest of this implementation.

The `AGENTS.md` file will be provided as a separate document alongside this handoff prompt. Do not invent its content — use the provided version exactly.

---

### `.cursorrules`

Write this as a self-instruction document. It must reference `AGENTS.md` as the authoritative source and include:

- Read `AGENTS.md` at the start of every session before taking any action
- Always check `/tools/` before creating a new utility script
- Always check `/knowledge/` before making any assumption about NZ health context, voice, or algorithmic rules
- The WAT Framework governs this repo — full rules are in `AGENTS.md`
- `graph/state.py` is the single source of truth for all data flowing between nodes
- All generated content must use New Zealand English spelling
- Never use an em dash in any generated content — use a comma, full stop, or rewrite the sentence

---

### `.env.example`

Include the following keys with descriptive comments and no real values:

```
# Anthropic API (used by all agents)
ANTHROPIC_API_KEY=

# Search APIs (use either Tavily or Serper — Tavily preferred)
TAVILY_API_KEY=
SERPER_API_KEY=

# Firecrawl (used for full-page content fetching and agent-based research)
FIRECRAWL_API_KEY=

# Redis (for LangGraph checkpointer and session persistence)
REDIS_URL=

# LangSmith (optional — enables observability and trace debugging)
# Leave blank to run without tracing. System will not crash if absent.
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=clinicpro-linkedin-agent

# LinkedIn Authentication
# Primary: path to saved Playwright session file (preferred — avoids bot detection)
LINKEDIN_SESSION_PATH=./auth/linkedin_session.json
# Fallback: credentials used only when session file is missing or expired
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=
```

---

### `requirements.txt`

Generate a complete, pinned `requirements.txt` with the following dependencies. Use the most recent stable versions available at time of implementation:

```
# Core orchestration
langgraph
langchain-anthropic
langchain-core

# Search and web fetching
tavily-python
firecrawl-py

# Browser automation
playwright

# Persistence
redis
langgraph-checkpoint-redis

# Observability (optional — used when LANGSMITH_API_KEY is present)
langsmith

# Utilities
python-dotenv
loguru

# Code quality
black
mypy
```

After generating this file, run `pip install -r requirements.txt` to verify all packages resolve correctly. If any package name has changed, find the correct current name and update the file before proceeding.

---

### `config/model_config.json`

Assign Claude models to each agent node:

```json
{
  "researcher": {
    "model": "claude-3-5-sonnet-20241022",
    "reason": "High reasoning required for NZ health policy synthesis"
  },
  "scout": {
    "model": "claude-3-5-haiku-20241022",
    "reason": "Lower-cost data processing for LinkedIn discovery tasks"
  },
  "architect": {
    "model": "claude-3-5-sonnet-20241022",
    "reason": "High-quality writing required for voice-accurate drafting"
  },
  "strategist": {
    "model": "claude-3-5-sonnet-20241022",
    "reason": "Reflection and critique require strongest reasoning capability"
  }
}
```

---

### `config/playwright_settings.py`

Configure Playwright for LinkedIn automation. Key requirements:

- Headed mode only — never use headless mode with LinkedIn (triggers bot detection)
- Session file authentication: check for `LINKEDIN_SESSION_PATH` first; fall back to credential login only if session file is absent or expired
- Set a realistic user agent string (recent Chrome on macOS)
- Add randomised delays between actions (500-1500ms) to simulate human behaviour
- Set viewport to 1280x800
- Export a `get_browser_context()` function that returns an authenticated Playwright context

---

### `graph/state.py`

Define the shared `TypedDict` "LinkedIn Context" — the cognitive kernel passed between all nodes. This is the most critical file in the repo.

```python
from typing import TypedDict, Annotated, List, Optional
import operator

class LinkedInContext(TypedDict):
    # Input
    raw_input: str                             # URL or clinical topic provided by human

    # Research phase
    research_summary: str                      # Synthesised findings from Researcher agent
    target_urls: List[str]                     # URLs grounding the research

    # Discovery phase
    scout_targets: List[dict]                  # 5-6 LinkedIn accounts for Golden Hour engagement
                                               # Each dict: {name, url, post_url, rationale}

    # Drafting phase
    post_draft: str                            # Main LinkedIn post (150-300 words)
    comments_list: List[str]                   # 6 pre-engagement comments for Golden Hour
    first_comment: str                         # Link/URL to go in first post comment

    # Metadata
    pillar: str                                # "pillar_1", "pillar_2", or "pillar_3"
    hashtags: List[str]                        # 3-4 approved hashtags for this post

    # Memory reducers
    logs: Annotated[List[str], operator.add]   # Append-only execution log

    # Control flow
    revision_count: int                        # Tracks Reflexion loop iterations (max 2)
    human_approved: bool                       # Set to True after HITL interrupt
    error_state: Optional[str]                 # Populated on failure for interrupt handover
```

`operator.add` is the reducer for `logs` only — all other fields use last-write-wins. Add inline comments explaining each field's purpose.

---

### `graph/workflow.py`

Define the LangGraph DAG. The pipeline must follow this sequence:

**Node order:**
1. `planner` — PS+ initialisation, identifies pillar and plan
2. `researcher` — web search via Tavily and full-page fetching via Firecrawl, grounded in NZ context
3. `scout` — LinkedIn discovery for Golden Hour targets (Playwright, headed mode)
4. `architect` — drafts post and 6 pre-engagement comments
5. `strategist` — critiques draft against guardrails; loops back to architect if revision needed (max 2 loops)
6. `human_review` — `interrupt()` point; pauses for consolidated human review
7. `executor` — posts pre-engagement comments via Playwright, then schedules main post

**Interrupt behaviour:**
- After `strategist` approves the draft, call `interrupt()` before `executor`
- Expose the full state as a mutable object so the human can edit `post_draft`, `comments_list`, and `first_comment` in the Cursor chat before resuming
- If Playwright fails at any point in `scout` or `executor`, set `error_state` and call `interrupt()` for human takeover rather than crashing

**LangSmith tracing:**
- At graph compilation, check whether `LANGSMITH_API_KEY` is present in the environment
- If present, wrap the compiled graph with LangSmith tracing using `langsmith.wrappers` or equivalent current API, with project name from `LANGSMITH_PROJECT`
- If absent, compile and run without tracing — no warning, no crash

**Handoff protocol:**
- Between nodes, pass only the final `<SOLUTION>` output — not the full reasoning trace — to prevent context window saturation
- Log every node transition to `state["logs"]` with a timestamp

---

### `graph/persistence.py`

Integrate Redis as the LangGraph checkpointer:

- Use `langgraph.checkpoint.redis.RedisSaver` (or equivalent current API)
- Read `REDIS_URL` from environment
- Snapshot state after every node completion
- Export a `get_checkpointer()` function used by `workflow.py`
- Include a `resume_from_checkpoint(thread_id: str)` utility for Time Travel Debugging

---

### `agents/researcher.py`

**Identity:** NZ Health Researcher — specialist in NZ primary care infrastructure and policy.

**Responsibilities:**
- Read `/knowledge/nz_health_context.md` via filesystem before any search
- Execute NZ-contextualised web search using `search_nz_health()` from `tools/search.py`
- For deeper policy or infrastructure content, call `fetch_page_content()` to retrieve full-page Markdown via Firecrawl
- For complex multi-source research queries, use `research_with_agent()` which invokes Firecrawl's `/agent` endpoint with a natural language prompt (e.g., "Find the current RNZCGP position on 12-month prescriptions and return the key points")
- Synthesise findings into `research_summary` (max 300 words)
- Populate `target_urls` with 3-5 source URLs
- Identify the correct content pillar based on topic
- Consult `/knowledge/dehallucination_triggers.md` before finalising any clinical or policy claim — call `interrupt()` if the topic is flagged

**Handoff output format:**
```
<SOLUTION>
pillar: pillar_1
research_summary: [300 words max]
target_urls: [list]
</SOLUTION>
```

---

### `agents/scout.py`

**Identity:** LinkedIn Scout — growth hacker focused on Golden Hour engagement.

**Responsibilities:**
- Use `search_linkedin_topic()` from `tools/search.py` for initial target discovery (Serper API, lower overhead than Playwright)
- Use Playwright headed mode via `tools/browser.py` to verify and access specific post URLs
- Before selecting targets, read all `engagement.json` files in `/outputs/` to avoid repeating the same accounts within a 4-week window
- Target audience priority: NZ GPs, practice managers, PHO staff, Medtech NZ, RNZCGP
- Populate `scout_targets` with name, LinkedIn URL, specific post URL, and rationale
- Draft 6 pre-engagement comments in Dr Ryo's voice (see `/knowledge/voice_profile.md`)
- Comments must be 2-3 sentences, substantive, and reference a specific point from the target post

**Constraint:** Never tag more than 1-3 people per comment. Never comment generically.

---

### `agents/architect.py`

**Identity:** Content Architect — technical writer specialising in the "Insider GP" voice.

**Responsibilities:**
- Read `/knowledge/voice_profile.md` and `/knowledge/algorithm_sop.md` before drafting
- Draft the main LinkedIn post using the 2025 algorithm structure:
  1. Hook (1-2 sentences — specific clinical observation or bold statement)
  2. Systemic point (1-2 paragraphs)
  3. Insider take (1 paragraph — conclusion, not a question)
- Word count: 150-300 words (hard limit)
- Select 3-4 hashtags from `/knowledge/hashtag_library.md`
- Draft the `first_comment` content (outbound URLs go here, never in post body)
- Apply all banned terms and structural rules from voice profile

**Hard rules:**
- No outbound links in post body
- No open-ended questions at the end
- No mention of ClinicPro R&D roadmap or Inbox AI features
- No third-person references to ClinicPro
- Maximum 4 hashtags

---

### `agents/strategist.py`

**Identity:** ClinicPro Strategist — Reflector and Evaluator node.

**Responsibilities:**
- Critique the draft against the following guardrails:
  - Word count within 150-300 words
  - No outbound links in post body
  - Hashtag count 3-4 maximum
  - No banned terms (see voice profile)
  - No disclosure of Inbox AI features or R&D roadmap
  - Correct pillar voice applied
  - Ends with a take, not a question
  - No third-person ClinicPro references
- If any guardrail fails, return draft to `architect` with specific revision instructions (logged to `logs`)
- Maximum 2 revision loops — if draft still fails after 2 loops, flag in `logs` and pass to human review with failure notes
- If all guardrails pass, approve and pass to `human_review`

---

### `tools/browser.py`

Playwright automation scripts for LinkedIn. This file must implement robust modal and UI-change handling based on known LinkedIn automation failure patterns.

**`dismiss_modal_if_present(page) -> None`**
- Checks the page accessibility tree for any modal, overlay, or dialog (e.g., "Share your update", cookie banners, notification prompts)
- If found, dismisses it before returning
- Must be called before every major action in all other functions

**`get_browser_context()`**
- Checks for valid session file at `LINKEDIN_SESSION_PATH` first — never attempt credential login if session file exists and is valid
- Falls back to credential login using `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` only if session is absent or expired
- After credential login, saves new session to `LINKEDIN_SESSION_PATH` automatically
- Returns authenticated Playwright browser context

**`post_comment(context, post_url: str, comment_text: str) -> dict`**
- Navigates to `post_url`
- Re-captures page snapshot before interacting with any element (never use stale references)
- Calls `dismiss_modal_if_present()` before attempting to open comment box
- Uses semantic queries and accessibility tree lookups — never hardcode CSS selectors
- Verifies comment box is open before typing
- Posts `comment_text`
- Verifies comment appeared in the thread before returning success
- Adds randomised delay (500-1500ms) before and after action
- Returns `{"success": True, "post_url": post_url}` or `{"success": False, "error": str}`

**`schedule_post(context, post_text: str, first_comment: str, scheduled_time: str) -> dict`**
- Navigates to LinkedIn post composer
- Calls `dismiss_modal_if_present()` before each interaction step
- Re-captures page snapshot before each element interaction
- Enters `post_text` into composer
- Schedules post for `scheduled_time` (ISO format)
- After post goes live, posts `first_comment` as the first reply
- Returns `{"success": True, "post_url": str}` or `{"success": False, "error": str}`

**Error handling:**
- On any Playwright exception, attempt one autonomous fix (update selector using accessibility tree, retry once with a 2-second delay)
- If the fix succeeds, log the change with a description of what changed to `state["logs"]` and announce in chat
- If the fix fails after one attempt, set `error_state` in LangGraph state and call `interrupt()` for human takeover
- Never crash silently

---

### `tools/search.py`

Search and content fetching tools. Export the following four functions:

**`search_nz_health(query: str, max_results: int = 5) -> list[dict]`**
- Calls Tavily API with NZ-contextualised query
- Filters results to prefer `.govt.nz`, `rnzcgp.org.nz`, `medtech.co.nz`, and NZ news domains
- Returns list of `{title, url, snippet}` dicts

**`search_linkedin_topic(query: str) -> list[dict]`**
- Calls Serper API with `site:linkedin.com` scoped search
- Used by Scout agent for initial target discovery without Playwright overhead
- Returns list of `{title, url, snippet}` dicts

**`fetch_page_content(url: str) -> str`**
- Calls Firecrawl's scrape endpoint for the given URL
- Returns clean Markdown of the full page content
- Used by Researcher when a search result needs deeper reading (e.g., full RNZCGP policy page, Medtech changelog)
- On failure, returns an empty string and logs the error — does not crash

**`research_with_agent(prompt: str) -> str`**
- Calls Firecrawl's `/agent` endpoint with a natural language prompt
- Used by Researcher for complex multi-source queries where search-then-fetch would require multiple chained calls (e.g., "Find the current RNZCGP position on 12-month prescriptions and summarise the key points for a GP audience")
- Returns the agent's synthesised response as a string
- On failure, falls back to `search_nz_health()` with extracted keywords from the prompt

---

### `scripts/login.py`

A standalone script Dr Ryo runs manually when the LinkedIn session expires.

Behaviour:
1. Launches a visible Playwright browser (headed mode)
2. Navigates to `linkedin.com/login`
3. Prompts the user to log in manually in the browser window
4. Waits for user to press Enter in the terminal after logging in
5. Saves the authenticated session to `LINKEDIN_SESSION_PATH`
6. Prints confirmation and closes browser

Include a clear docstring explaining: what this script does, when to run it (session file missing or expired), and how long a session typically stays valid.

---

### `main.py`

Entry point. Must:

1. Load environment variables from `.env`
2. Initialise Redis checkpointer via `graph/persistence.py`
3. Compile the LangGraph workflow from `graph/workflow.py` (with LangSmith tracing if `LANGSMITH_API_KEY` is present)
4. Accept either a URL or a clinical topic string as input (CLI argument or prompted input)
5. Trigger PS+ initialisation phrase
6. Run the workflow, streaming node outputs to stdout using `loguru`
7. On `interrupt()`, pause and display the current draft state clearly in the terminal for human review
8. Accept human edits to `post_draft`, `comments_list`, and `first_comment` before resuming
9. Save final session outputs to `outputs/YYYY-MM-DD_[topic-slug]/` with:
   - `research.md`
   - `plan.md`
   - `draft_final.md`
   - `engagement.json`
   - `session_state.json`

---

### `knowledge/clinicpro_strategy.md`

Document the three content pillars with full detail for agent reference:

**Pillar 1: NZ Primary Care Infrastructure (40% of posts)**
Focus on the unsexy plumbing of GP practice — Medtech APIs, HealthLink, cloud migrations, clinical software gaps. No other NZ GP is talking about this with real technical understanding. Example angles: Medtech ALEX Intelligence Layer, Medtech Cloud migration friction, HealthLink referral gaps, clinical photo workflow failures.

**Pillar 2: Building a Clinical Tool as a Practising GP (30% of posts)**
Inside view of identifying a problem in clinic and building software to fix it. "Building in public" done with clinical credibility. Example angles: GP feedback that changed a feature, the difference between what GPs say they want and what they use, technical learning from the build. Pre-R&D decision constraint: keep Inbox AI development vague, focus on live features only (Referral Images, scribing).

**Pillar 3: Honest Takes on NZ Health Policy and Admin Burden (30% of posts)**
Specific, clear positions on things GPs are thinking about but nobody says plainly. Grounded in clinical experience, not abstract policy. Example angles: 12-month prescriptions policy impact, admin burden and GP workforce shortages, why NZ general practice resists digital tools, PHO communications fragmentation.

Target audience priority:
- Primary: NZ GPs, practice managers, receptionists, PHO practice support staff
- Secondary: Health IT professionals, Medtech staff, digital health founders, PHO leadership, RNZCGP staff
- Tertiary: Investors, potential hires, consulting clients

---

### `knowledge/voice_profile.md`

The "Insider GP" voice profile:

**Voice characteristics:**
- First-person always (never third-person references to ClinicPro or Dr Ryo)
- Direct, problem-focused, conversational
- Clinical credibility through specificity (name exact systems, exact friction points)
- Translator positioning: explains what technical developments mean for daily GP practice
- No marketing fluff, no hedging, no corporate tone

**Banned terms (never use in any draft):**
- "innovative" / "innovation"
- "disruptive" / "disruption"
- "solutions"
- "seamless"
- "game-changer"
- "excited to announce"
- "thrilled"
- "leveraging"
- Any variation of "what do you think?" or open engagement-bait questions

**Structural rules:**
- Hook must open with a named NZ clinical system, workflow step, or infrastructure component (e.g., "Medtech Cloud", "HealthLink referral", "12-month prescription queue") — never with a rhetorical question or a statistic without clinical context
- No open-ended questions at the end of posts
- End with Dr Ryo's take or conclusion
- 150-300 words (hard limit)
- No outbound links in post body — first comment only

**Pre-R&D decision constraints:**
- Do not mention Inbox AI features or roadmap
- Do not mention specific clinical AI architecture
- Do not reference funded development timelines
- Keep admin tools framing vague until grant decision is made
- Only reference features that are live: Referral Images workflow, scribing

**Positive framing rule:** When discussing industry developments (e.g., Medtech ALEX Intelligence Layer), acknowledge genuine progress before naming the remaining gap. This signals Dr Ryo is an informed insider, not a complainer.

---

### `knowledge/algorithm_sop.md`

2025 LinkedIn Algorithm Standard Operating Procedure:

**Post structure:**
- Hook → Systemic point → Insider take
- 150-300 words optimal
- No outbound links in post body (30% reach reduction penalty)
- Links go in first comment only
- No engagement-bait questions
- LinkedIn's 2025 algorithm tracks "consumption rate" — posts that hold attention outperform posts with high initial likes but low read-through

**Hashtags:**
- 3-4 per post maximum (5+ gets penalised — research shows 68% reach reduction)
- Consistent set: `#NewZealandGP`, `#PrimaryHealthCare`, `#MedtechNZ`
- Add one context-specific tag per post (see hashtag library)
- No generic tags like `#Innovation` or `#AI`

**Tagging:**
- 1-3 tags per post maximum
- Only tag when legitimately relevant (discussing their platform, policy, or work)
- Never tag to generate engagement — algorithm flags this as spam in 2025

**Timing:**
- Post Tuesday to Thursday, 8-10am NZST
- Be available for 15-20 minutes post-publication to respond to early comments

**Golden Hour Protocol:**
- 15-20 minutes before publishing: post 5-6 substantive comments on target audience posts (warms up the algorithm)
- Immediately after publishing: respond to every comment within the first hour
- First comment (posted after main post goes live): place any outbound URLs here
- Comments over 15 words carry 2.5x more algorithmic weight than shorter interactions

**Penalties to avoid:**
- Posting more than once per week (splits engagement)
- Posting and disappearing (kills algorithmic momentum)
- Engagement pods (algorithm detects coordinated activity)
- Overpromising features that do not exist
- Using third-party scheduling tools that post via API rather than browser (penalised by LinkedIn's Nexus algorithm in 2025)

---

### `knowledge/nz_health_context.md`

NZ Health Context Glossary for the Researcher agent:

**Key organisations:**
- **RNZCGP** — Royal New Zealand College of General Practitioners. Sets GP training standards, issues policy positions (e.g., 12-month prescriptions). Website: rnzcgp.org.nz
- **PHO** — Primary Health Organisation. Funded by Te Whatu Ora to manage GP practice enrolments and population health. Key PHOs: ProCare (Auckland), Pinnacle (Waikato), Waitematā PHO, Pegasus Health (Canterbury)
- **Te Whatu Ora** — Health New Zealand. The national health authority post-2022 restructure (replaced DHBs)
- **Medtech** — Dominant NZ GP practice management system. Products: Medtech32 (legacy), Medtech Evolution (current), Medtech Cloud (SaaS migration in progress)
- **HealthLink** — NZ's primary secure clinical messaging network. Used for specialist referrals, lab results, and inter-practice communication
- **Medtech ALEX Intelligence Layer** — Medtech's API platform enabling third-party integrations. Enables gathering provider inbox results — a significant recent development for builders like ClinicPro

**Key NZ-specific policy context:**
- **12-month prescriptions** — RNZCGP policy allowing longer repeat prescription intervals for stable chronic conditions. Creates admin workflow implications for practices
- **Medtech Cloud migration** — Ongoing migration of practices from on-premise Medtech32 to cloud-hosted Medtech Evolution. Creates workflow friction during transition (e.g., clinical photo handling gaps)
- **Clinical photo referral gap** — Medtech Cloud does not support direct image uploads to referrals. Requires manual workarounds that add approximately 30 minutes per referral

**What to avoid:**
- Do not use US health system terminology (EMR, EHR, PCP, insurance billing)
- Do not assume NHS or Australian MBS context
- Always ground policy references in RNZCGP or Te Whatu Ora sources, not generic international guidelines
- Always use Firecrawl's `fetch_page_content()` or `research_with_agent()` to verify NZ-specific claims before including them — do not rely on training knowledge for current policy details

---

### `knowledge/hashtag_library.md`

**Consistent set (include in every post):**
- `#NewZealandGP`
- `#PrimaryHealthCare`
- `#MedtechNZ`

**Context-specific tags (add one per post based on pillar):**
- Pillar 1 (Infrastructure): `#HealthTech`
- Pillar 2 (Building in public): `#DigitalHealth`
- Pillar 3 (Policy/Admin): `#GeneralPractice` or `#NZHealth`

**Approved tagging targets (only when legitimately relevant):**
- Medtech NZ — when discussing their platform or API updates
- RNZCGP — when discussing their policy positions
- ProCare / Pinnacle / Waitematā PHO — when discussing PHO-level developments
- Named GPs or practice managers — only when they gave direct feedback referenced in a building-in-public post

**Banned tags:**
- `#Innovation`
- `#AI`
- `#Healthcare` (too generic)
- `#Disruption`
- Any custom or invented hashtags

---

### `knowledge/dehallucination_triggers.md`

Sensitive topics that must trigger a human clarification interrupt before the Researcher or Architect agent proceeds. When any of these are identified, log the trigger to `state["logs"]` and call `interrupt()` with the specific question.

| Topic | Required clarification |
|---|---|
| 12-month prescription policy | "What is the current RNZCGP position, and has this changed since [date]? Please confirm before I draft." |
| Medtech Cloud feature availability | "Is [specific feature] live in Medtech Cloud for NZ practices, or still in rollout? Please verify." |
| Medtech ALEX API capabilities | "Which ALEX API endpoints are currently stable and publicly documented? Please confirm scope." |
| HealthLink referral acceptance rules | "Which specialist categories are currently accepting HealthLink referrals in Auckland? Please verify." |
| Te Whatu Ora funding or policy changes | "Has this policy/funding change been officially announced? Please provide source URL." |
| Any specific clinical guideline claim | "Please confirm this guideline is current RNZCGP or MoH guidance before I include it." |
| ClinicPro user numbers or metrics | "Please confirm current live user count and any metrics before I reference them." |
| R&D grant status | "Has the R&D grant decision been made? If yes, please advise whether constraints have changed." |

**Protocol:**
1. Log trigger name and timestamp to `state["logs"]`
2. Call `interrupt()` with the clarification question displayed clearly
3. Do not proceed with drafting until human confirms or corrects
4. After confirmation, log the human's response and resume
5. If the same trigger fires repeatedly for the same confirmed fact, update `dehallucination_triggers.md` with the confirmed answer so future runs do not need to ask again

---

## Implementation Sequence

Implement files in this exact order to respect dependencies:

1. `AGENTS.md` — read immediately after creating, apply its rules for all subsequent steps
2. `.env.example`, `requirements.txt`, and `config/` files
3. `graph/state.py` — all agents depend on this
4. `knowledge/` directory — all agents read these before acting
5. `tools/browser.py` and `tools/search.py`
6. `agents/researcher.py`, `agents/scout.py`, `agents/architect.py`, `agents/strategist.py`
7. `graph/persistence.py`
8. `graph/workflow.py`
9. `scripts/login.py`
10. `main.py`
11. `.cursorrules`

After scaffolding all files, run a dependency check to confirm all imports resolve correctly.

---

## Quality Checks Before Completing

- [ ] All imports across all Python files resolve without errors
- [ ] `requirements.txt` installs cleanly with no version conflicts
- [ ] `LinkedInContext` TypedDict is correctly imported by all agent and graph files
- [ ] `operator.add` reducer is correctly applied to `logs` field only
- [ ] `interrupt()` is called in exactly three places: after Strategist approval, on Playwright failure after one failed fix attempt, and on dehallucination trigger
- [ ] `dismiss_modal_if_present()` is called before every major Playwright action in `browser.py`
- [ ] No hardcoded CSS selectors anywhere in `browser.py` — semantic queries and accessibility tree lookups only
- [ ] `tools/search.py` exports all four functions: `search_nz_health`, `search_linkedin_topic`, `fetch_page_content`, `research_with_agent`
- [ ] LangSmith tracing initialises only when `LANGSMITH_API_KEY` is present — system runs cleanly without it
- [ ] No agent file makes assumptions about NZ health context without reading `nz_health_context.md` first
- [ ] `browser.py` session file check runs before credential login — never the other way around
- [ ] No outbound links appear in post body in any draft template or example
- [ ] Hashtag count enforcement (3-4 maximum) is implemented in `strategist.py` as a hard guardrail
- [ ] `outputs/` folder creation logic in `main.py` uses `YYYY-MM-DD_[topic-slug]` naming
- [ ] `scripts/login.py` contains a clear docstring explaining when to run it
- [ ] All generated content and code comments use New Zealand English spelling
- [ ] No em dashes anywhere in any generated file

---

## Source Documents for Knowledge Files

Use the following documents to populate all files in the `/knowledge/` directory. Do not invent content — use only what is in these documents.

### Document 1: ClinicPro LinkedIn Strategy
[paste full content of ClinicPro_LinkedIn_Strategy_Updated.md here]

### Document 2: LinkedIn Profile Optimisation Instructions
[paste full content of LinkedIn_Profile_Optimisation_Instructions.md here]

---

## What Success Looks Like

When a user runs `python main.py` and provides a topic (e.g., "Medtech ALEX Intelligence Layer"), the system must:

1. Print the PS+ initialisation phrase
2. Run Researcher — produce a grounded NZ-context research summary using Tavily search, Firecrawl page fetching, and/or Firecrawl agent queries
3. Run Scout — identify 5-6 real LinkedIn target accounts with specific post URLs and draft 6 pre-engagement comments
4. Run Architect — produce a 150-300 word post in Dr Ryo's voice with 3-4 hashtags and a first-comment URL placeholder
5. Run Strategist — critique and approve or revise (max 2 loops)
6. Pause at `interrupt()` — display full draft to human for review and editing
7. After human approval — execute Golden Hour comments via Playwright, then schedule the post
8. Save all outputs to `outputs/YYYY-MM-DD_medtech-alex/`

The human should only need to interact at one point: the consolidated review step. Everything else runs autonomously.
