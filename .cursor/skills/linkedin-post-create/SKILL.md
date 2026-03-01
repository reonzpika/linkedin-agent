---
name: linkedin-post-create
description: Orchestrates LinkedIn post creation from topic to scheduled execution. Run prepare_post.py, show review in chat, handle approval or edits, then schedule via OS task.
---

# LinkedIn Post Creation Skill

**Trigger:** "create linkedin post", "draft post about", "write about [topic]"

**Description:** Orchestrates the full post creation workflow: pre-flight questions, research, drafting, review loop, and scheduling.

---

## Orchestration Protocol

### Phase 1: Pre-flight (Plan mode)

Ask 2–3 clarifying questions before running the workflow:

1. **Pillar preference:** "Which content pillar does this fit? (1: Infrastructure, 2: Building in Public, 3: Policy/Admin, or auto-detect?)"
2. **Specific angle:** "Any specific hook or observation you want highlighted?"

If the user provides no topic, ask: "What topic would you like to create a post about?"

Show execution plan:
```
Plan: I'll research NZ primary care context, scout 6 Golden Hour targets from your feed, draft post + comments, and schedule for next Golden Hour (8am NZST tomorrow). Approve?
```

Wait for approval before proceeding.

---

### Phase 2: Execute workflow

1. Run in background terminal: `python prepare_post.py "[topic]"`

2. **Poll for completion** (Cursor cannot auto-detect file creation):
```python
   import time
   from pathlib import Path
   
   marker_file = Path("temporary/review_ready.json")
   timeout = 300  # 5 minutes
   elapsed = 0
   
   while not marker_file.exists() and elapsed < timeout:
       time.sleep(3)  # Check every 3 seconds
       elapsed += 3
   
   if not marker_file.exists():
       # Timeout - check terminal output for errors
       print("ERROR: Script timed out after 5 minutes. Check terminal output.")
       # Abort workflow
```

3. When `review_ready.json` appears, read it to get the session folder path, then proceed to Phase 3.

**Implementation note:** Use bash_tool or Python execution to run the polling loop. Show progress in chat every 30 seconds: "Still preparing... (elapsed: 30s, 60s, etc.)"

---

### Phase 3: Review loop

When `review_ready.json` appears:

1. Read `temporary/review_ready.json` to get `output_dir` path.
2. Read outputs from the session folder:
   - `draft_final.md` for post text
   - `engagement.json` for targets and comments
3. Format review in chat:
```
📝 Draft ready for review

POST:
[post_draft with line breaks preserved]

HASHTAGS: [list]
FIRST COMMENT: [first_comment]

GOLDEN HOUR COMMENTS (6):
1. [target.name] → [comment text]
   Link: [target.post_url]
2. ...

What would you like to do?
- "Approve" to schedule
- Request specific changes (I'll edit and show diff)
- "Regenerate" to run Architect again
```

3. Handle user response:
   - **Approve:** Move to Phase 4.
   - **Edit request:** Apply changes to `draft_final.md` and `engagement.json`, show diff, ask "Approve these changes?"
   - **Regenerate:** Re-run Architect with feedback, return to review.

---

### Phase 4: Scheduling

After approval:

1. Calculate next Golden Hour (8:00am NZST; tomorrow if after 8am today):
```python
   from datetime import datetime, timedelta
   import pytz
   
   nz_tz = pytz.timezone('Pacific/Auckland')
   now = datetime.now(nz_tz)
   
   # Next 8am NZST
   if now.hour < 8:
       exec_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
   else:
       exec_time = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
```

2. Create OS scheduled task:
```python
   from tools.scheduler import schedule_execution
   
   result = schedule_execution(session_id, exec_time)
   
   if not result["success"]:
       # Show error, offer manual execution
       print(f"⚠️  Scheduling failed: {result['error']}")
       print(f"To execute manually at Golden Hour, run:")
       print(f"python execute_post.py {session_id}")
```

3. Write `temporary/approved.json`:
```json
   {
     "session_id": "2026-03-01_medtech-alex",
     "approved_at": "2026-03-01T17:30:00Z",
     "scheduled_for": "2026-03-02T08:00:00+13:00"
   }
```

4. Append to `temporary/pending_posts.json`:
```json
   {
     "posts": [
       {
         "session_id": "2026-03-01_medtech-alex",
         "scheduled_for": "2026-03-02T08:00:00+13:00",
         "status": "scheduled"
       }
     ]
   }
```

5. Confirm in chat:
```
   ✓ Approved and scheduled
   Post will go live: Tomorrow 8:00am NZST
   Session: 2026-03-01_medtech-alex
   
   I'll execute the Golden Hour protocol automatically.
```

---

### Phase 5: Learning from feedback

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