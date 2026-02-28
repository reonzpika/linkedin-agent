# Dehallucination Triggers

**Source:** ClinicPro LinkedIn Strategy (Pre-R&D Decision Content Constraints) + NZ system specifics  
**Purpose:** Sensitive topics that must trigger a human clarification interrupt before the Researcher or Architect agent proceeds. When any of these are identified, log the trigger to `state["logs"]` and call `interrupt()` with the specific question.

---

## Protocol

1. Log trigger name and timestamp to `state["logs"]`
2. Call `interrupt()` with the clarification question displayed clearly
3. Do not proceed with drafting until human confirms or corrects
4. After confirmation, log the human's response and resume
5. If the same trigger fires repeatedly for the same confirmed fact, update this file with the confirmed answer so future runs do not need to ask again

---

## Trigger Table

| Topic | Required clarification |
|-------|------------------------|
| 12-month prescription policy | "What is the current RNZCGP position, and has this changed since [date]? Please confirm before I draft." |
| Medtech Cloud feature availability | "Is [specific feature] live in Medtech Cloud for NZ practices, or still in rollout? Please verify." |
| Medtech ALEX API capabilities | "Which ALEX API endpoints are currently stable and publicly documented? Please confirm scope." |
| HealthLink referral acceptance rules | "Which specialist categories are currently accepting HealthLink referrals in Auckland? Please verify." |
| Te Whatu Ora funding or policy changes | "Has this policy/funding change been officially announced? Please provide source URL." |
| Any specific clinical guideline claim | "Please confirm this guideline is current RNZCGP or MoH guidance before I include it." |
| ClinicPro user numbers or metrics | "Please confirm current live user count and any metrics before I reference them." (Currently 30+ GP users per strategy doc; verify before use.) |
| R&D grant status | "Has the R&D grant decision been made? If yes, please advise whether constraints have changed." |
| Inbox AI features or roadmap | "Do not mention Inbox AI features or roadmap. Pre-R&D constraint: keep vague. Confirm before proceeding." |
| Funded development timelines | "Do not reference funded development timelines. Pre-R&D constraint. Confirm before proceeding." |

---

## Pre-R&D Decision Constraints (Summary)

Until R&D grant decision is made:

**Do talk about:**
- Practice admin tools (general category)
- Tools already live (Referral Images, scribing)
- Infrastructure and workflow problems
- Learning from building tools
- NZ primary care system commentary

**Don't talk about:**
- Specific Inbox AI features or roadmap
- Funded development plans
- Technical architecture of clinical AI
- Timelines for clinical decision support features
- Anything that signals pre-revenue waiting on grant

---

## NZ System Specifics to Verify

When drafting claims about:
- **Medtech Cloud** — verify feature availability (e.g. direct image uploads to referrals)
- **ALEX Intelligence Layer** — verify which API capabilities are live and documented
- **HealthLink** — verify referral acceptance by specialty/region
- **RNZCGP** — verify policy positions (e.g. 12-month prescriptions) are current
- **ClinicPro metrics** — currently 30+ GP users; verify before referencing
