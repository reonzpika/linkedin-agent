---
name: linkedin-agent-improve
description: Applies Self-Improvement Protocol to update knowledge files from user feedback on draft quality, voice, structure, or agent behaviour. Use when the user gives corrective feedback on a draft (e.g. "Hook is too weak", "Sounds too marketing-y", "That's not how PHOs work", "Comments are too long") or on voice, structure, or facts.
---

# LinkedIn Agent Self-Improvement Skill

**Trigger:** User gives feedback on draft quality, voice, structure, or agent behaviour (e.g. "Hook is too weak", "Sounds too marketing-y", "That's not how PHOs work", "Comments are too long").

**Description:** Maps feedback to the correct knowledge file and updates it using the Self-Improvement Protocol in AGENTS.md.

---

## Detection triggers

Activate when the user says things like:

- "Hook is too weak"
- "Sounds too marketing-y"
- "That's not how PHOs work"
- "Don't mention [X] in posts"
- "Comments are too long"
- Any corrective feedback during review

---

## Protocol

### 1. Identify feedback tier

Map feedback to a knowledge file using the table in AGENTS.md:

| Feedback type   | Target file                    |
|-----------------|--------------------------------|
| Voice/tone      | `knowledge/voice_profile.md`   |
| Post structure  | `knowledge/voice_profile.md` + `algorithm_sop.md` |
| Content pillar  | `knowledge/clinicpro_strategy.md` |
| Algorithm rules | `knowledge/algorithm_sop.md`   |
| NZ health facts | `knowledge/nz_health_context.md` |
| Agent behaviour | Relevant file in `agents/`     |
| Playwright/tools| Relevant file in `tools/`      |
| Dehallucination | `knowledge/dehallucination_triggers.md` |

### 2. Derive a specific rule

Turn feedback into a testable constraint, not a vague instruction.

**Weak:** "Be more specific in hooks."

**Strong:** "Hook must open with a named NZ clinical system or workflow step and anchor to either (a) a specific named event (launch, rollout, policy change) or (b) a scoped national claim with a concrete number; never with a rhetorical question or statistic without context."

### 3. Update the file

1. Announce in chat **before** updating:

   ```
   Updating knowledge/voice_profile.md: Adding rule that hooks must open with specific clinical observation. Applying now.
   ```

2. Append the rule to the appropriate section in the file.
3. If updating an agent file, also update AGENTS.md if behaviour changes.
4. Do not ask for approval (follow AGENTS.md protocol).

### 4. Apply to current session

If still in the drafting phase, re-run Architect with the updated rule so the next draft reflects it.

---

## Strategic changes

If the proposed update would:

- Alter public positioning
- Contradict an existing pillar
- Remove a constraint (rather than add one)

Then: Flag in chat and wait for approval before updating.

---

## Examples

- **Feedback:** "Hook is too generic"  
  **Action:** Update `voice_profile.md` with specific hook requirements, announce, re-run Architect if applicable.

- **Feedback:** "That PHO structure is wrong"  
  **Action:** Update `nz_health_context.md` with correct info, announce, continue.

- **Feedback:** "Don't mention user numbers in Building in Public posts"  
  **Action:** Flag as strategic change, wait for approval.

---

## Success criteria

- Feedback correctly mapped to file.
- Rule is specific and testable.
- Update announced before applied.
- User sees the effect in the next draft where relevant.
- System does not repeat the same mistake.
