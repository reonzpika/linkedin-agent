# NZ Health Context (Factual Reference)

**Source:** ClinicPro LinkedIn Strategy  
**Purpose:** NZ-specific factual reference for research and drafting. Not strategy; use for grounding claims and avoiding US/UK terminology.

---

## Key Organisations

### RNZCGP
Royal New Zealand College of General Practitioners. Sets GP training standards, issues policy positions (e.g. 12-month prescriptions). Website: rnzcgp.org.nz

### PHO (Primary Health Organisation)
Funded by Te Whatu Ora to manage GP practice enrolments and population health. Key PHOs:
- **ProCare** (Auckland)
- **Pinnacle** (Waikato)
- **Waitematā PHO**
- **Pegasus Health** (Canterbury)

### Te Whatu Ora
Health New Zealand. The national health authority post-2022 restructure (replaced DHBs).

### Medtech
Dominant NZ GP practice management system. Products:
- **Medtech32** (legacy)
- **Medtech Evolution** (current)
- **Medtech Cloud** (SaaS migration in progress)

### HealthLink
NZ's primary secure clinical messaging network. Used for specialist referrals, lab results, and inter-practice communication.

### Medtech ALEX Intelligence Layer
Medtech's API platform enabling third-party integrations. Enables gathering provider inbox results; a significant recent development for builders like ClinicPro. Recent API updates finally allow gathering provider inbox results.

---

## Key NZ-Specific Policy and Infrastructure Context

### 12-month prescriptions
RNZCGP policy allowing longer repeat prescription intervals for stable chronic conditions. Creates admin workflow implications for practices.

### Medtech Cloud migration
Ongoing migration of practices from on-premise Medtech32 to cloud-hosted Medtech Evolution. Creates workflow friction during transition (e.g. clinical photo handling gaps).

### Clinical photo referral gap
Medtech Cloud does not support direct image uploads to referrals yet. Requires manual workarounds: resize manually, upload to referral as attachment, hope it doesn't bounce for file size, then chase up when specialist says they can't open it. Adds approximately 30 minutes per referral. The last-mile problem of actually getting clinical content where it needs to go hasn't been solved yet.

### HealthLink and specialist referral friction
The gap between what HealthLink says it supports and what specialists actually accept. Not all specialist categories accept HealthLink referrals; rules vary by region and specialty.

### PHO communications fragmentation
Information overload and fragmented practice information scattered across multiple systems with no way to search or be alerted when things change.

---

## Practice Context

### Sunnynook Medical Centre
Dr Ryo Eguchi's current practice location (Auckland). Used when referencing specific clinical context.

---

## Infrastructure Post Examples (Structure Reference)

**Example (Pillar 1):**
```
I tried to send a clinical photo to dermatology yesterday. 
Medtech Cloud doesn't support direct image uploads to referrals yet.

So the workaround is: resize manually, upload to referral as attachment, hope it doesn't bounce for file size, then chase up when specialist says they can't open it.

This is the gap nobody talks about when discussing "seamless cloud migration." The technical upgrade is real. The workflow friction is also real. And GPs just absorb it as normal.

Medtech's new ALEX Intelligence Layer could change this; their recent API updates finally allow gathering provider inbox results, which is a huge step. But the last-mile problem of actually getting clinical content where it needs to go hasn't been solved yet.

Until then, it's manual workarounds. Every referral.
```

---

## What to Avoid

- Do not use US health system terminology (EMR, EHR, PCP, insurance billing)
- Do not assume NHS or Australian MBS context
- Always ground policy references in RNZCGP or Te Whatu Ora sources, not generic international guidelines
- Always use Firecrawl's `fetch_page_content()` or `research_with_agent()` to verify NZ-specific claims before including them; do not rely on training knowledge for current policy details
