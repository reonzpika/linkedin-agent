# Dr Ryo Eguchi — LinkedIn Visual Brand Design Language
**Version:** 1.0
**Date:** March 2026
**Purpose:** Governs all LinkedIn image generation. Read by image_architect agent before building any prompt. Every decision is locked unless explicitly revised in this file.

---

## Identity

**Who:** Dr Ryo Eguchi — practising NZ GP and solo founder of ClinicPro.
**Persona:** Brilliant doctor who codes. Insider translator of NZ primary care infrastructure.
**Visual register:** Precise, warm, slightly unusual. Clinical authority meets technical thinking. Never corporate. Never generic health-blue. Never startup gradient.
**No face in images.** The visual language carries the persona without the person.

---

## Colour Palette (LOCKED — never deviate)

| Role | Name | Hex | Usage |
|---|---|---|---|
| Signature accent | Coral | `#E05C3A` | Header block background, accent bars |
| Primary text | Charcoal | `#1C1C1E` | All body text, headlines on light bg |
| Page background | Off-white | `#F8F5F0` | All slide/image backgrounds |
| Support | Warm grey | `#8A8580` | Captions, secondary labels, dividers |
| Alternate surface | Pale cream | `#EDEAE3` | Callout boxes, alternate slide bg |
| Annotation emphasis | Dark coral | `#B84A2E` | Underlines, arrow strokes, circles |

**Rules:**
- Coral is the ONLY bright colour. One coral element per slide maximum.
- Never use: blue, teal, purple, green, gradients.
- Never use pure white (`#FFFFFF`) — always off-white (`#F8F5F0`).
- Dark mode: never.

---

## Typography

| Role | Font | Weight | Size |
|---|---|---|---|
| Accent block headline | Kalam | Bold 700 | 36–48px carousel; 52–64px header |
| Body headline | DM Sans | SemiBold 600 | 20–24px |
| Body text | DM Sans | Regular 400 | 15–17px |
| Captions/labels | DM Sans | Regular 400 | 11–13px |
| Handwritten callouts | Kalam | Regular 400 | 14–18px |

**Rules:**
- Kalam: accent block headline + handwritten annotations ONLY.
- DM Sans: everything else.
- Text on coral: always off-white (`#F8F5F0`).
- Text on off-white: always charcoal (`#1C1C1E`).
- Left-aligned everywhere. Never centred body text.

---

## Layout — The Annotated Document Grid

Every slide is structured like a clinical document annotated by hand.

**Canvas:** 1080×1080px square (carousels), 1200×628px (single post header).
**Margins:** 48px all sides.

```
┌─────────────────────────────────┐
│  ZONE A: CORAL BLOCK (180–220px)│  Full-width, no side margins
│  Headline in Kalam Bold         │
│  "Dr Ryo E." small label        │
├─────────────────────────────────┤
│                                 │
│  ZONE B: BODY CONTENT           │  48px side margins
│  Text, diagrams, annotations    │
│                                 │
├─────────────────────────────────┤
│  "ClinicPro" — bottom right     │  Zone C: 36px tall
└─────────────────────────────────┘
```

**Zone A (coral block):**
- Background: `#E05C3A` full width, touches canvas edges, no rounded corners.
- Headline: Kalam Bold, `#F8F5F0`, 36–48px.
- Name label: "Dr Ryo E." DM Sans Regular 12px `#F8F5F0`, bottom-right of block.

**Zone B (body):**
- Background: `#F8F5F0`.
- Optional faint horizontal rules at 32px intervals, colour `#E8E4DC`.

**Zone C (footer):**
- "ClinicPro" DM Sans Regular 11px `#8A8580`, 24px from right, 16px from bottom.

---

## Annotation System

Annotations make the visual feel like a GP annotated the document by hand.

**Types:**
1. **Underline** — wavy/irregular, `#B84A2E`, 2px, just below text baseline.
2. **Arrow callout** — single line, small arrowhead, slight curve, from Kalam label to element.
3. **Bracket** — vertical bracket grouping items, Kalam label to the right.
4. **Circle emphasis** — rough circle around a term, `#B84A2E`, 2px, slightly imperfect.

**Rules:**
- Maximum 2–3 annotations per slide.
- Annotations must reference real content — never decorative.
- Feel added after the main content, not designed in.

---

## Diagram and Illustration Style

When a slide needs a visual explanation:
- Line weight: 1.5–2px, slightly variable (hand-drawn feel).
- Lines: charcoal `#1C1C1E` for structure; dark coral `#B84A2E` for emphasis.
- Fills: pale cream `#EDEAE3`. Never solid dark fills, never gradients.
- Shapes: slightly imperfect rectangles, ~4px corner radius.
- Labels: DM Sans SemiBold for boxes; Kalam Regular for annotations.
- Arrows: single-line, hand-drawn style, simple arrowhead.
- No drop shadows. No glows. No 3D effects. No icon library icons.
- Layout: text left 40%, diagram right 60%.

---

## Pillar Visual Modes

All three pillars use the same palette and type. Mood varies by annotation density.

| Pillar | Mood | Elements | Annotation density |
|---|---|---|---|
| Pillar 1 Infrastructure | Technical schematic | Flow diagrams, system maps, API workflows | High (multiple callouts) |
| Pillar 2 Building in Public | Iterative, behind-the-scenes | Numbered lists, timelines, before/after | Medium (1–2 per slide) |
| Pillar 3 Policy/Admin | Document analysis, clear position | Key quotes, numbered arguments, stark type | Low (one underline/circle) |

---

## Carousel Structure (8–10 slides optimal)

| Slide | Zone A headline content | Zone B content |
|---|---|---|
| 1 Cover | Main post headline | Subtitle or "X things" label |
| 2 Context | Short reframe | 2–3 sentence context |
| 3–7 Content | Point number + short label | Explanation + diagram/annotation |
| 8 Conclusion | "The bottom line" | 2–3 sentence conclusion |
| 9 Optional | Follow-on invitation | "Follow for NZ primary care commentary" |

**Rules:**
- Never repeat the same layout back-to-back.
- Zone A height must be consistent across all slides in a series.
- No dark slides or inverted slides within a series.

---

## What This System Is NOT

- Not Joshua Liu's system (no yellow, no casual marker font, no conference energy).
- Not generic health tech (no blue, no teal, no stock-photo doctors).
- Not startup aesthetic (no gradients, no dark mode, no geometric-sans everything).
- Not over-designed (annotations must feel hand-added, not designed in).

---

## Quick Reference for Prompts

```
PALETTE: bg=#F8F5F0 | accent=#E05C3A | text=#1C1C1E | grey=#8A8580 | emphasis=#B84A2E | cream=#EDEAE3
FONTS: Kalam Bold (accent headlines + annotations) | DM Sans (all body)
LAYOUT: Full-width coral header (headline + "Dr Ryo E." label) → off-white body → "ClinicPro" footer
ANNOTATIONS: Hand-drawn underlines/arrows/circles in dark coral — max 3 per slide
DIAGRAMS: Hand-drawn schematic, pale cream fills, no icon libraries, text-left diagram-right
NEVER: blue, gradients, dark mode, drop shadows, pure white, centred body text, 2+ fonts
```

---

## Character Illustration Style

**Reference:** Akira Toriyama: Dr Slump (1980–1984). Not Dragon Ball's action register; specifically Dr Slump's everyday-life, doodle-energy register.

**Why this reference:** Toriyama's Dr Slump figures are deceptively simple. Every character reads instantly, carries genuine personality, and belongs unmistakably to the same visual world as every other character, regardless of role. That cross-character consistency is exactly what is needed across carousel slides where figures may be clinicians, patients, practice managers, founders, or bureaucrats.

### Technical characteristics (apply to all person figures)

- **Outline:** Thick, confident, slightly variable stroke weight; not uniform. The outline does most of the visual work. Approximately 2–3px, with natural variation as if drawn with a felt-tip pen in one stroke.
- **Proportions:** Slightly enlarged head relative to body; not full chibi, but head is roughly 1/3 of total figure height. Bodies are simplified: torso as a rounded rectangle, limbs as tapered lines.
- **Faces:** Two dot eyes, a single curved line for mouth. Expression lives entirely in the *angle* of these marks: dots angled inward suggest worry; dots level suggest calm; a wide curved mouth suggests delight. No noses except a small bump line when facing sideways.
- **Hands:** Simplified: three or four stubby fingers, slightly rounded. No anatomical detail.
- **Motion marks:** Use Toriyama-style action marks freely: small radiating lines around a figure suggest surprise or emphasis; curved speed lines suggest movement; a sweat drop (small teardrop shape beside the head) suggests stress or awkwardness. These marks are part of the style, not decoration.
- **No shading:** Pure contour line only. No hatching, no grey fills, no drop shadows on figures. The off-white background shows through everywhere inside the outline.
- **Clothing:** Minimal suggestion only: a collar line, a pocket rectangle, a belt line. Never enough detail to identify profession from clothing alone. Gesture and context carry meaning, not costume.

### What to avoid

- Thin uniform 1px lines (looks like flat vector icon, not Toriyama)
- Anatomically correct proportions (too stiff, too generic)
- Stethoscopes, white coats, or any profession-specific props (rely on gesture instead)
- Fully rendered faces with noses, ears, hair detail (too much)
- Any shading, gradient, or fill on figure bodies
- Generic "clipart doctor" or "stock illustration person" register

### Consistency rule

Every person figure across all slides must feel like it belongs to the same visual universe. If slide 3 has a worried bureaucrat and slide 6 has a determined founder, both should look like they stepped out of the same Toriyama page. Achieve this through consistent outline weight, consistent head-to-body ratio, and consistent face construction; not through identical poses.
