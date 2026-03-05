---
name: linkedin-post-create
description: Chat-only LinkedIn post creation. Prompt for topic/URL, run plan script, show plan for approval, then research, scout, draft; review in chat; assemble and schedule.
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

4. Proceed to Phase 2 (run plan script). Do not run research or any other script until the plan is approved.

---

### Phase 2: Planning and plan approval

1. **Run the planning script:**
   - From repo root: `python scripts/plan_from_url.py --session-dir outputs/<session_id>`
   - If the script exits non-zero, show the error in chat and stop.

2. **Read `plan.json`** from the session folder. Present in chat:
```
Execution plan

Pillar: [pillar]
Angle: [angle]

Plan:
[plan text]

Approve this plan to continue to research, or paste your edits (I'll update plan.json and then continue).
```

3. **Handle user response:**
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

### Phase 4: Scout and draft, then review

1. Run: `python scripts/scout.py --session-dir outputs/<session_id>` (from repo root). If Scout finds fewer than 6 targets, mention it in chat and still proceed.
2. **If Scout found more than 6 targets:** Read `engagement.json` and present the **full list** in chat (numbered: name, short snippet, post_url). Say: "Scout found N targets above. Reply 'pick 6' to run the picker, or tell me which 6 you want (e.g. by index)." **Do not run pick_targets.py until the user has replied.** After the user confirms (e.g. "pick 6" or "use indices 0, 2, 5, 7, 10, 12"), run: `python scripts/pick_targets.py --session-dir outputs/<session_id>`. If the user specified indices, you may need to set scout_targets to those entries and skip pick_targets, or document that pick_targets is for "pick 6" and manual choice requires editing engagement.json.
3. Run: `python scripts/draft.py --session-dir outputs/<session_id>` (from repo root). If the user had requested "Regenerate" with feedback, run with `--revision-feedback "<text>"` instead.
4. Read from the session folder: `draft_final.md`, `draft_meta.json`, `engagement.json`. Format review in chat:
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
- "Approve" to schedule or execute (per plan)
- Request specific changes (I'll edit and show diff)
- "Regenerate" to run Architect again
- "Show other targets" to see the full scout list (scout_targets_all in engagement.json) and pick a different 6, then re-run draft for new comments
```

5. **STOP and wait for user response.** Do **not** run Phase 5 (assemble, schedule, or execute) until the user has explicitly approved in chat (e.g. "Approve", "yes", "go ahead", "schedule it", "execute now"). If the plan says "execute now", that means after approval the user wants immediate execution; it does **not** mean you may skip this approval step.
6. Handle user response:
   - **Approve:** Move to Phase 5 (assembly and scheduling or execute now, per user/plan).
   - **Edit request:** Apply changes to `draft_final.md`, `draft_meta.json`, and/or `engagement.json`, show diff, ask "Approve these changes?"
   - **Regenerate:** Re-run draft script with `--revision-feedback "<user feedback>"`, then return to step 3 (show draft again).
   - **Show other targets:** If `engagement.json` has `scout_targets_all`, present that full list (numbered) in chat and ask which 6 indices to use. Update `scout_targets` to those 6 entries, then re-run `draft.py` to generate new comments for the new 6; return to step 4 (show draft again).

---

### Phase 5: Assembly and scheduling

**Only after the user has explicitly approved the draft in chat:**

1. **Assemble session state:** Run `python scripts/assemble_session_state.py --session-dir outputs/<session_id>` (from repo root). This writes `session_state.json` so `execute_post.py` can run later. If the script fails, show the error and stop.

2. Calculate next available Tue/Thu 8:00am NZST slot and create OS scheduled task:
```python
   from tools.scheduler import schedule_execution_auto_slot
   from tools.schedule_manager import get_schedule_summary
   
   result = schedule_execution_auto_slot(session_id)
   
   if not result["success"]:
       print(f"Scheduling failed: {result['error']}")
       print(f"To execute manually at Golden Hour, run:")
       print(f"python execute_post.py {session_id}")
```

4. Write `temporary/approved.json` using values from result: `scheduled_for` (main post time, 8:00am NZST), and `executor_runs_at` (7:40am NZST) from `schedule_execution_auto_slot`. Include `session_id`, `approved_at` (now ISO), `scheduled_for`.

5. Append to `temporary/pending_posts.json` with `session_id`, `scheduled_for` from result, `status`: "scheduled".

6. Confirm in chat with schedule summary:
```
   Approved and scheduled

   Comments: {result["executor_runs_at"]} NZST (7:40am)
   Main post: {result["scheduled_for"]} NZST (8:00am)
   Session: {session_id}

   {get_schedule_summary()}

   Golden Hour protocol will run automatically:
   * 7:40am - Post 6 pre-engagement comments
   * Wait 20 minutes
   * 8:00am - Post main content + first comment
```

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
- **Timeout (5 min):** Check terminal output, show last 20 lines to user, offer to continue waiting or abort.

---

## Success criteria

- User approves draft with minimal edits (≤3 requests).
- Scheduling succeeds OR user clearly knows how to execute manually.
- User understands when post will go live.
- No exposed credentials or raw errors in chat.