---
name: linkedin-post-create
description: Chat-only LinkedIn post creation. Prompt for topic/URL, run plan script, show plan for approval, then research, scout, draft; review in chat; assemble and schedule. Use when the user says "create linkedin post", "draft post about [topic]", or "write about [URL/topic]".
---

# LinkedIn Post Creation Skill

**Trigger:** "create linkedin post", "draft post about", "write about [topic]"

**Description:** Chat is the only interface. Prompt for basic info, run scripts (plan, research, scout, draft), present each output in chat for approval or edit, then assemble and schedule. Do not run any script until the user has provided required info.

**How to run:** Start in **Agent mode**. Send topic and/or URL (e.g. "Create a linkedin post about [URL]"). The skill will present the plan and wait for your approval before running research. Do not use Plan mode to execute the full flow; that skips approval gates.

---

## Orchestration Protocol

### Phase 1: Gather input and create session

1. **Prompt in chat** (do not run tools until you have at least topic or URL):
   - "What topic or URL would you like to create a post about?"
   - Optional: "Which content pillar? (1: Infrastructure, 2: Building in Public, 3: Policy/Admin, or auto-detect?)"
   - Optional: "Any specific hook or angle you want highlighted?"

2. **Create session folder** (from repo root):
   - Use slug from topic (e.g. "Medtech ALEX" → `2026-03-03_medtech-alex`). Reuse logic from `main.py`: `output_dir_for_topic(topic)` or equivalent (YYYY-MM-DD_slug, collision suffix -2, -3 if exists).
   - Ensure `outputs/` exists; create `outputs/<session_id>/`.

3. **Write `input.json`** in the session folder:
```json
{
  "topic": "<user topic>",
  "url": "<optional URL>",
  "pillar_preference": "<optional 1|2|3|auto>",
  "angle": "<optional user angle>",
  "created_at": "<ISO timestamp>"
}
```
   - The plan script uses only one URL; if the user gives multiple source URLs, put the primary article URL in `url`. After planning, Phase 2 verification may correct the stored summary using all intended URLs.

4. Proceed to Phase 2 (run plan script). Do not run research or any other script until the plan is approved.

---

### Phase 2: Planning and plan approval

1. **Run the planning script:**
   - From repo root: `python scripts/plan_from_url.py --session-dir outputs/<session_id>`
   - If the script exits non-zero, show the error in chat and stop.

2. **Verify URL summary:** The plan script fetches a single URL from `input.json` and stores the raw page crawl in `plan.json` as `summary_from_url`. Crawl4AI returns full-page content; on many sites (e.g. HiNZ, healthnz.govt.nz) the DOM order puts navigation first, so the stored text can be site chrome (Sign In, menus, links) instead of the article body. After reading `plan.json`, check whether `summary_from_url` looks like article content. If it clearly looks like site navigation (e.g. starts with or is dominated by "Sign In", "Join", "Toggle navigation", "MENU", or long repeated link lists), do **not** present it as the source summary. Instead: (a) announce in chat that the fetched content appears to be site chrome rather than the article; (b) offer to fix it by fetching the correct URL(s) the user intended and updating `plan.json` with a short summary from those URLs, or ask the user to confirm the correct source URL(s) and re-run plan. If the user provided multiple URLs, use the primary one in `input.json` for the script; for the stored summary, derive a brief summary from all intended URLs and set `summary_from_url` in `plan.json` to that (so downstream and the user see the right sources).

3. **Read `plan.json`** from the session folder. Present in chat:
```
Execution plan

Pillar: [pillar]
Angle: [angle]

Plan:
[plan text]

Approve this plan to continue to research, or paste your edits (I'll update plan.json and then continue).
```

4. **Handle user response:**
   - **Approve:** Continue to Phase 3 (research).
   - **Edit:** Update `plan.json` with the user's changes (e.g. replace `plan`, `angle`, or `pillar` as appropriate), then continue to Phase 3.
   - Do **not** run Phase 3 (research) until the user has explicitly approved or you have applied their edits to plan.json.

---

### Phase 3: Research

1. Run: `python scripts/research.py --session-dir outputs/<session_id>` (from repo root).
2. If the script exits non-zero: check for `research_dehallucination.txt` in the session folder. If present: read that file and show the question in chat. Ask the user to paste their answer. Write the user's answer to `research_dehallucination_answer.txt` in the **session folder** (same folder as research.md). Re-run: `python scripts/research.py --session-dir outputs/<session_id>`. The researcher will read the answer file and continue. Otherwise show the script error and stop.
3. Read `research.md` (and optionally `research_meta.json`) from the session folder. Present a short summary in chat; user may approve or skip to next step.
4. Proceed to Phase 4 (scout and draft).

---

### Phase 4: Scout (pause) then picker and draft, then review

**Scout runtime and user availability:** The scout script can take **2 minutes or longer** (feed scroll + pinned company pages). It may hit chat or terminal timeouts while still running in the background. The user may be away; when they return, scout may have already finished and written `engagement.json`. Always verify engagement (read `engagement.json`, confirm `scout_targets` and optionally `scout_targets_pinned`) before treating scout as done. If the file is missing or empty, tell the user: "Scout may still be running or may have failed. Check that `engagement.json` exists and has targets, then say 'proceed' when ready."

---

#### Phase 4a: Scout only (then STOP)

1. Run: `python scripts/scout.py --session-dir outputs/<session_id>` (from repo root). Expect 2+ minutes; the command may time out in chat while the script continues.
2. After the run (or when the user returns): read `outputs/<session_id>/engagement.json`. If missing or no `scout_targets`, tell the user scout may still be running or have failed and to check the file, then wait for "proceed". If the file has content, continue to step 3.
3. Present **scout summary** in chat:
   - "[M] feed targets" (length of `scout_targets`). If fewer than 6 total (feed + pinned), say so and that we will still proceed.
   - If `scout_targets_pinned` is present: "Plus [P] pinned: [name] ([post_url])" (e.g. "Plus 1 pinned: Health Informatics New Zealand (HiNZ) (https://...)")."
4. **STOP.** Say: "Scout finished. Say **proceed** (or *continue* / *pick and draft*) when you want to run the picker (if needed) and draft." Do **not** run pick_targets.py or draft.py until the user says proceed, continue, pick and draft, or equivalent.

---

#### Phase 4b: After user says "proceed" – Picker and draft, then review

1. **Picker when needed:** Let N = 6 - len(scout_targets_pinned). If len(scout_targets) > N: Read `engagement.json` and present the **feed list** (scout_targets) in chat (numbered: name, short snippet, post_url). Say: "Scout found [M] feed targets above (plus [P] pinned). Reply 'pick 6' to run the picker, or tell me which [N] you want (e.g. by index)." Do **not** run pick_targets.py until the user replies. After they confirm (e.g. "pick 6" or "use indices 0, 2, 5, 7, 10"), run: `python scripts/pick_targets.py --session-dir outputs/<session_id>`. If len(scout_targets) <= N, skip picker and go to step 2.
2. Run: `python scripts/draft.py --session-dir outputs/<session_id>` (from repo root). If the user had requested "Regenerate" with feedback, run with `--revision-feedback "<text>"` instead. **Warning:** draft.py overwrites `draft_final.md`. If the user has already approved or edited the draft in a previous turn, do **not** re-run draft.py unless they explicitly ask to "Regenerate"; otherwise their edits will be lost.
3. Read from the session folder: `draft_final.md`, `draft_meta.json`, `engagement.json`. Format review in chat:
```
📝 Draft ready for review

POST:
[post_draft with line breaks preserved]

HASHTAGS: [list]
SUGGESTED MENTIONS: [list or "None"]
FIRST COMMENT: [first_comment]

**About suggested mentions:**
- Architect suggests mentions only when post directly discusses that entity's work
- You can accept, reject, or modify these before approving
- Mentions will NOT be auto-inserted into the post; you decide if/where to add them
- LinkedIn algorithm penalises >3 tags per post; use sparingly

GOLDEN HOUR COMMENTS (6):
1. [target.name] → [comment text]
   Link: [target.post_url]
2. ...

What would you like to do?
- "Approve", "proceed", "schedule for me", or "schedule" to run assembly and schedule for the next slot (Phase 5)
- "Execute now" to run assembly then post comments and main post immediately (no OS schedule)
- Request specific changes (I'll edit and show diff)
- "Regenerate" to run Architect again
- "Show other targets" to see the full scout list (scout_targets_all in engagement.json) and pick a different 6, then re-run draft for new comments
```

4. **STOP and wait for user response.** Do **not** run Phase 5 (assemble, schedule, or execute) until the user has explicitly approved in chat. Treat as approval any of: "Approve", "yes", "go ahead", "schedule it", "schedule", "schedule for me", "proceed", "proceed with the next phase", "next phase" (when the last substantive output was this draft). If the plan says "execute now", that means after approval the user wants immediate execution; it does **not** mean you may skip this approval step.
5. Handle user response:
   - **Approve (including "proceed", "schedule for me", "schedule", "next phase"):** Move to Phase 5. Run Phase 5 in full (assemble, then schedule_execution_auto_slot, write approved.json, append pending_posts.json, confirm). Do not skip scheduling unless the user explicitly said "execute now".
   - **Execute now:** Run Phase 5 step 1 (assemble) only, then run `execute_post.py` (or use --comments-then-schedule for 20 min gap); do not call schedule_execution_auto_slot.
   - **Edit request:** Apply changes as follows, then show a diff and ask "Approve these changes?":
     - Post body edits: update `draft_final.md`.
     - Hashtag, first comment, or mentions edits: update `draft_meta.json`.
     - **Golden Hour comment edits (any of the 6 comments):** update `comments_list` in `engagement.json` with the final approved text. This is mandatory — `engagement.json` is the source of truth for what gets posted and what `collect_analytics.py` later matches against. Never leave a stale `comments_list` in `engagement.json` after an edit.
   - **Regenerate:** Re-run draft script with `--revision-feedback "<user feedback>"`, then return to step 3 (show draft again).
   - **Show other targets:** If `engagement.json` has `scout_targets_all`, present that list (feed only, numbered) in chat. If there are pinned targets, ask which (6 - len(pinned)) indices to use; otherwise which 6. Set `scout_targets` to those chosen entries plus `scout_targets_pinned`, then re-run `draft.py` and return to step 3 (show draft again).

---

### Phase 5: Assembly and scheduling

**Only after the user has explicitly approved the draft in chat (see approval phrases in Phase 4b step 4).**

**Mandatory:** When the user has approved the draft, you MUST run Phase 5 in full: steps 1–7 below. Do not run only step 1 (assemble) and then wait. **Exception:** If the user said "execute now", run step 1 only, then run `python execute_post.py <session_id>` (or with --comments-then-schedule for the 20 min gap); skip steps 2–5 (no schedule_execution_auto_slot, no approved.json/pending_posts).

1. **Assemble session state:** Run `python scripts/assemble_session_state.py --session-dir outputs/<session_id>` (from repo root). This writes `session_state.json` so `execute_post.py` can run later. If the script fails, show the error and stop.

2. Calculate next available slot (Tue 10am, Wed 12pm, Thu 9am NZST) and create OS scheduled task:
```python
   from tools.scheduler import schedule_execution_auto_slot
   from tools.schedule_manager import get_schedule_summary
   
   result = schedule_execution_auto_slot(session_id)
   
   if not result["success"]:
       print(f"Scheduling failed: {result['error']}")
       print(f"To execute manually at Golden Hour, run:")
       print(f"python execute_post.py {session_id}")
```

4. Write `temporary/approved.json` using values from result: `scheduled_for` (main post time) and `executor_runs_at` (20 min before) from `schedule_execution_auto_slot`. Include `session_id`, `approved_at` (now ISO), `scheduled_for`.

5. Append to `temporary/pending_posts.json` with `session_id`, `scheduled_for` from result, `status`: "scheduled".

6. Confirm in chat with schedule summary:
```
   Approved and scheduled

   Comments: {result["executor_runs_at"]} NZST
   Main post: {result["scheduled_for"]} NZST
   Session: {session_id}

   {get_schedule_summary()}

   Golden Hour protocol will run automatically:
   * Executor runs (post 6 pre-engagement comments)
   * Wait 20 minutes
   * Main post + first comment published
```

7. Remind Dr Ryo: "Remember to run the 48-hour review after it publishes: 'review post [session_id]'"

---

### Phase 6: Learning from feedback

If the user requests changes during review:

1. Apply changes directly to files.
2. If a pattern is detected (user requests same type of change 2+ times), derive a testable rule.
3. Follow Self-Improvement Protocol from AGENTS.md:
   - Map feedback to knowledge file (voice → `voice_profile.md`, etc.)
   - Announce: "Updating [file]: [specific rule]. Applying now."
   - Update file immediately
   - Re-apply to current draft if still in review
4. Continue with review loop.

---

## Error handling

- **Script fails:** Show terminal error, offer to retry or abort.
- **Scheduling fails:** Warn user, show manual command: `python execute_post.py [session_id]`
- **No targets found:** Explain Scout found 0 targets; suggest: `python scripts/login.py` to refresh LinkedIn session.
- **Timeout (5 min):** Check terminal output, show last 20 lines to user. For **scout specifically**: the script often continues in the background. Ask the user to confirm whether `engagement.json` now exists and has targets. If yes, present the scout summary (Phase 4a step 3) and wait for "proceed"; then continue with Phase 4b. If no, offer to re-run scout or abort.

---

## Success criteria

- User approves draft with minimal edits (≤3 requests).
- Scheduling succeeds OR user clearly knows how to execute manually.
- User understands when post will go live.
- No exposed credentials or raw errors in chat.