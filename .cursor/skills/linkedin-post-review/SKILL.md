---
name: linkedin-post-review
description: Runs the 48-hour post performance review workflow. Collects analytics from a published post, runs the Analyst, presents performance report and proposed knowledge/system updates for approval. Use when the user says "review post", "analyse performance", "how did the post do", "48 hour review", "what worked", "what failed", "post review", "check the analytics", or "review [session_id]".
---

# Skill: linkedin-post-review

## Trigger phrases

Activate this skill when Dr Ryo says any of:
- "review post"
- "analyse performance"
- "how did the post do"
- "review [session_id]"
- "48 hour review"
- "what worked"
- "what failed"
- "post review"
- "check the analytics"

---

## Overview

This skill runs the 48-hour post performance review workflow for the ClinicPro
LinkedIn Engine. It collects metrics from a published post, scores performance
against benchmarks for a small NZ primary care account, and proposes updates
to knowledge files (knowledge updates) or system behaviour (system updates).
All proposed updates require Dr Ryo's explicit approval before anything is changed.

---

## Phase 1 — Identify session

If Dr Ryo names a session ID (e.g. "review 2026-03-10_burnout"), use it directly.
If not, check `outputs/` for the most recently published session by reading
`execution_results.json` in each folder and selecting the most recent with a
`main_post` entry and a valid (non-feed) post URL.

Confirm the session with Dr Ryo before proceeding:
> "I'll run the 48-hour review for **[session_id]**. Is that the right post?"

Wait for confirmation.

---

## Phase 2 — Collect analytics

Run:
```
python scripts/collect_analytics.py --session-dir outputs/[session_id]
```

Parse the output and present a brief summary in chat:
> "Analytics collected:
> Impressions: X | Reactions: X | Comments: X | Reposts: X
> Saves: X | Sends: X | Profile views: X | Followers: X
> Golden Hour: X/6 replies | X impressions | X likes"

### Error handling

**Session expired / redirected to login:**
Run `python scripts/login.py` first, then retry.

**Post URL missing or generic (/feed/):**
Ask Dr Ryo to paste the direct post URL. Then add it manually to
`execution_results.json` under the `main_post` result as `"post_url": "<url>"`.

**SELECTOR_STALE warning (all zeros):**
Make one attempt to fix by trying the direct analytics URL manually in the browser
to confirm the page structure. If the selectors have changed, do not retry endlessly.
Proceed with zeros and note the issue in the report. The analyst will flag a system
update automatically if this is a recurring pattern.

---

## Phase 3 — Analyse performance

Run:
```
python scripts/analyse_performance.py --session-dir outputs/[session_id]
```

---

## Phase 4 — Present report and proposed updates

Display the full contents of `outputs/[session_id]/performance_report.md` in chat.

Then present the proposed updates in two clearly labelled sections. Use the
numbered list from `proposed_updates.json` — knowledge and system updates share
one continuous number sequence.

### Knowledge updates (items N)

Present as:
> **Update [N] — Knowledge — `[file]`**
> Section: [section]
> Rationale: [rationale]
> Confidence: [confidence]
> Current rule: [current_rule]
> Proposed rule: [proposed_rule]

### System updates (items N)

Present as:
> **Update [N] — System — `[file]`** _(requires Cursor agent mode)_
> What: [what]
> Why: [why]
> Outcome: [outcome]
> Confidence: [confidence]
> Scope: [scope]
> Reversibility: [reversibility]
> Dependencies: [dependencies]
> Verification: [verification]

After presenting all updates, ask:
> "Type **APPROVE ALL**, **REJECT ALL**, or list the numbers you want to approve
> (e.g. 1 3). Knowledge updates will be applied immediately via str_replace.
> System updates will trigger a read-first / plan-first workflow in Cursor agent mode."

---

## Phase 5 — Apply approved updates

Wait for Dr Ryo's approval response before touching any files.

### Applying knowledge updates

For each approved knowledge update:
1. Announce the change in chat: "Applying update [N] to `[file]`..."
2. Use `str_replace` to replace `current_rule` with `proposed_rule` in the target file
3. Confirm: "Update [N] applied."

If `current_rule` is empty (new rule), append `proposed_rule` to the appropriate
section in the file rather than using str_replace.

### Applying system updates

For each approved system update, switch to Cursor agent mode and follow the
`cursor_instruction` field in the update entry exactly:

1. Read all files listed in `read_before_planning` in order
2. Reason about which layer of the system is the best place to make the change —
   consider AGENTS.md, all skill files, all agents, and the specific file named
3. Produce an implementation plan in chat stating:
   - Which layer you chose
   - Why you ruled out the other layers
   - The exact changes you intend to make and to which files
4. Wait for Dr Ryo's approval of the implementation plan before making any changes
5. Announce every file change before applying it
6. After implementation, ask Dr Ryo to confirm the verification condition was met
7. Once confirmed, update the Open System Updates table in
   `knowledge/performance_history.md`:
   - Move the row from Open to Implemented
   - Record the session ID it was implemented in

---

## Phase 6 — Schedule reminder

After all approved updates are applied, check `schedule_registry.json` for the
next scheduled post. If one is within 48 hours, remind Dr Ryo:
> "Next post is scheduled for [date/time]. Remember to run the 48-hour review
> after it publishes: 'review post [next_session_id]'"

---

## System update protocol (reference)

System updates follow a read-first, plan-first, approve-then-act pattern.
Cursor must never implement a system update without first presenting a plan
and receiving explicit approval. This applies even if the change seems small.

The full protocol is defined in the `cursor_instruction` field of each system
update entry in `proposed_updates.json`. It is also documented in AGENTS.md
under "System Update Protocol".

