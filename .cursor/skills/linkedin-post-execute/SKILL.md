---
name: linkedin-post-execute
description: Executes Golden Hour posting for an approved session. Called by OS scheduler or manually with session_id.
---

# LinkedIn Post Execution Skill

**Trigger:** Internal (OS scheduler calling `execute_post.py`), or manual "execute [session_id]"

**Description:** Executes the Golden Hour posting protocol for an approved session.

---

## Execution protocol

### Invocation

Called by the OS scheduler at the designated time:

```bash
python execute_post.py [session_id]
```

Or manually in chat: "Execute 2026-03-01_medtech-alex"

---

### Process

1. Load session state from `outputs/[session_id]/session_state.json`. (This file is written by `scripts/assemble_session_state.py` when the user approves the draft in the linkedin-post-create skill; it must exist before execution.)
2. Optionally verify approval marker in `temporary/approved.json`.
3. Execute posting:
   - 6 Golden Hour comments to scout targets (in order).
   - Main post + first comment via schedule_post.
4. Save results to `outputs/[session_id]/execution_results.json`.
5. Remove session from `temporary/pending_posts.json`.

---

### Post-execution

If Cursor is open when execution completes:

- Read `outputs/[session_id]/execution_results.json`.
- Announce in chat:

```
Posted successfully at [time] NZST
Session: [session_id]
Results: 1 post + 6 comments

View outputs: outputs/[session_id]/
```

If any failures occurred:

- Show which actions failed.
- Offer to retry failed actions manually.
- Log to session logs.

---

## Error handling

- **Browser session expired:** Notify user to run `python scripts/login.py`.
- **Posting fails:** Save error details, notify user, offer manual retry.
- **Network issues:** Retry once, then abort and notify.

---

## Success criteria

- All actions execute without errors.
- Execution results saved.
- User notified when Cursor is open.
- Pending queue updated.
