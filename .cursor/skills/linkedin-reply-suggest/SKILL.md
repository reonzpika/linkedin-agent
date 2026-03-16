---
name: linkedin-reply-suggest
description: Generates 2-3 LinkedIn comment reply options in Dr Ryo's Insider GP voice following the 2026 algorithm depth-score framework. Use when the user pastes a comment and asks for reply options, "suggest a reply", "how should I reply", or "reply options for this comment".
---

# LinkedIn Reply Suggest

**Trigger:** "suggest a reply", "reply options", "how should I reply to this comment", "reply options for this comment"

**Purpose:** Given a LinkedIn comment on your post, generate 2-3 reply options that maximise depth score (thoughtful threads, back-and-forth) and stay in Dr Ryo's Insider GP voice. Does not post; you copy and use one option (or edit) in LinkedIn.

---

## Flow

### Step 1: Gather inputs

- **Comment text** (required). If not in the message, ask: "Paste the comment you want to reply to."
- **Commenter's first name and role/context** (optional). If missing and not obvious, you can ask: "Commenter's first name or role? (Helps personalise the reply.)"
- **Post topic or brief summary** (optional). If the post topic is unclear from context, ask: "What was the post about? (One line is enough.)"

### Step 2: Read knowledge

Before generating replies, read:

- `knowledge/voice_profile.md` (voice rules, sentence length, banned patterns)
- `knowledge/algorithm_sop.md` (depth score, engagement)

### Step 3: Generate reply options

Produce **3 options** (or 2 if Option C does not apply). Each reply must use this structure:

1. **Acknowledge and validate:** Use their first name; reference their specific point (not generic praise).
2. **Add value:** One new detail, NZ example, metric, or clinical insight not already in your post.
3. **Loop back:** End with a genuine open question so they can reply and extend the thread.

**Angle per option:**

- **Option A:** Clinical or workflow angle (what this means for daily practice).
- **Option B:** Systemic or infrastructure angle (broader NZ health context or pattern).
- **Option C:** Building-in-public angle (what ClinicPro is seeing or learning). Only include if the post topic is relevant to ClinicPro; otherwise omit and give A and B only.

**Reply constraints:**

- Length: 2-4 sentences, approx 30-60 words total.
- Sentence length: 10-20 words per sentence; split if over 20.
- Active voice, first person, NZ English spelling.
- No em dashes; use comma, full stop, or rewrite.
- No dead-end openers: avoid "Thanks for sharing!", "Great point!", "Absolutely!".
- No hedging or corporate tone.
- Clinical specificity where relevant: name exact systems, workflows, or friction points.

**When the post or comment involves NZ health systems, shared records, or clinical workflows:** Read the relevant knowledge file (e.g. `knowledge/nz_health_context.md` or other knowledge) so replies are accurate; do not rely on the skill alone for domain facts.

### Step 4: Present in chat

Use this format:

```
**Option A (clinical/workflow):** [one-line angle label]
[reply text]

**Option B (systemic/infrastructure):** [one-line angle label]
[reply text]

**Option C (building-in-public):** [one-line angle label]
[reply text]
(Omit Option C if post topic is not ClinicPro-relevant.)

---
Tip: Reply within 60-90 minutes for maximum algorithm boost. After replying, consider liking or commenting on the commenter's recent activity to reinforce mutual visibility.
```

---

## What this skill does not do

- Does not post the reply to LinkedIn.
- Does not use a session folder or run scripts.
- Does not replace the Golden Hour comment workflow (that is pre-engagement on others' posts; this is for replies on your own post).
