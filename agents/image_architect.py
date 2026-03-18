"""
Image Architect: reads draft_final.md, plan.json, and the brand design language spec,
then produces a structured list of per-slide Nano Banana Pro prompts for a LinkedIn carousel.
Called by scripts/generate_images.py.
"""

import json
import re
from pathlib import Path

from graph.state import LinkedInContext

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"


def _build_slide_prompt(
    slide_number: int,
    total_slides: int,
    zone_a_headline: str,
    zone_b_description: str,
    pillar: str,
    post_hook: str,
) -> str:
    """
    Build a single Nano Banana Pro prompt for one carousel slide.
    Embeds the full brand spec inline so the model has all context.
    """

    pillar_mood = {
        "pillar_1": (
            "Technical schematic mood. Use flow diagram or system map elements. "
            "Annotation density: high — multiple callouts, arrows pointing to key terms."
        ),
        "pillar_2": (
            "Iterative, behind-the-scenes mood. Use numbered list or before/after layout. "
            "Annotation density: medium — 1–2 annotations per slide."
        ),
        "pillar_3": (
            "Document analysis mood. Stark typography, key quote or numbered argument. "
            "Annotation density: low — one underline or circle only."
        ),
    }.get(pillar, "Technical schematic mood.")

    if slide_number == 1:
        zone_b_instruction = (
            "Zone B is typographic layout only — no illustration, no diagram, no figures. "
            "Use only text: one subtitle line in DM Sans SemiBold (max 8 words) framing the argument, "
            "and optionally one Kalam annotation (max 3 words) as a teaser. Generous white space. "
            "This slide stops the scroll; it does not explain the content."
        )
    else:
        zone_b_instruction = (
            "Draw Zone B as a dense hand-drawn editorial illustration that fills the available space completely. "
            "Every element must be labelled with legible text. Include at least one simple line-art figure (GP silhouette, patient, server, or building — drawn in 3–4 strokes, no shading). "
            "Style: medical textbook sketch meets tech whiteboard. Clean charcoal ink lines (1.5–2px, slightly imperfect), dark-coral annotations, off-white background. No empty areas. No gradients. No drop shadows."
        )

    return f"""Generate a LinkedIn carousel slide ({slide_number} of {total_slides}) in the Dr Ryo Eguchi brand system.

BRAND SYSTEM (apply exactly):
- Canvas: 2048×2048px square (2K resolution)
- Background (Zone B): off-white #F8F5F0
- Header block (Zone A): full-width coral #E05C3A rectangle, 180–220px tall, touches all three canvas edges (top, left, right), no rounded corners
  - Headline text in Kalam Bold, colour #F8F5F0: "{zone_a_headline}"
  - Small label reading only the words: "Dr Ryo E." — positioned bottom-right inside the coral block, small sans-serif text in off-white. Do not render any font name, pixel size, or hex code as visible text.
- Body zone (Zone B): off-white #F8F5F0. Leave a clear margin on the left and right (roughly 5% of canvas width). Do not render any margin measurements as visible text.
- Footer: the word "ClinicPro" must always appear in the bottom-right corner of every slide, small and unobtrusive in warm grey. This element is mandatory and must be present in every generation — do not omit it under any circumstances.
- Typography: Kalam Bold for the Zone A headline only; DM Sans for all Zone B text
- No pure white, no blue, no teal, no green, no purple, no gradients, no drop shadows, no 3D effects

ZONE B CONTENT:
{zone_b_instruction}

{zone_b_description}

ANNOTATIONS (hand-drawn style, feel added after):
- Use 2–3 of: wavy underline in dark coral #B84A2E beneath a key phrase; curved arrow from a Kalam label to a content element; rough circle around one key term
- Strokes 1.5–2px, slightly imperfect — not CAD-precise

PILLAR MOOD:
{pillar_mood}

SLIDE CONTEXT:
- Post topic: {post_hook}
- Slide {slide_number} of {total_slides}
- Maintain exact same coral block height, DM Sans body text size, and footer position as all other slides in this series

OUTPUT: A single polished slide image. No mock-up device frame. No outer border. Image fills the canvas edge to edge.

CRITICAL: Do not render any of the following as visible text in the image: font names (DM Sans, Kalam), pixel measurements (48px, 12px, 11px), hex colour codes (#E05C3A, #F8F5F0, #1C1C1E, #8A8580, #B84A2E), or margin/spacing numbers. These are styling instructions for you, not content to display."""


def run(state: LinkedInContext) -> dict:
    """
    Generate per-slide prompt structs for carousel image generation.
    Returns state update with:
    - image_prompts: list of {slide_number, zone_a_headline, zone_b_description, prompt, filename}
    - image_slide_count: int
    """
    post_draft = state.get("post_draft") or ""
    pillar = state.get("pillar") or "pillar_1"
    raw_input = state.get("raw_input") or ""
    plan = state.get("plan") or ""

    # Read brand design language for reference
    brand_path = KNOWLEDGE / "brand_design_language.md"
    brand_spec = brand_path.read_text(encoding="utf-8") if brand_path.exists() else ""

    # Extract post hook (first ~140 chars)
    lines = [l.strip() for l in post_draft.split("\n") if l.strip()]
    post_hook = lines[0][:140] if lines else raw_input[:140]

    from agents._llm import invoke

    system = f"""You are the Image Architect for Dr Ryo Eguchi's LinkedIn carousel system.
Given a LinkedIn post draft and content pillar, produce a structured 8-slide carousel plan.
Each slide needs:
1. A Zone A headline (short, punchy — 5–10 words max, written in Kalam Bold on coral)
2. A Zone B description (what goes in the body zone — text, diagram, or both)

Brand spec summary:
{brand_spec[:2000]}

RULES for Zone A headlines:
- Slide 1: the main post hook or a reframed version (not a question)
- Slide 1 Zone B is typographic only — no diagrams, no arrows, no boxes, no figures. One subtitle line (max 8 words) framing the argument, optionally one Kalam annotation (max 3 words) as a teaser. Generous white space. This slide stops the scroll; it does not explain the content.
- Slides 2–7: one concrete point per slide — short labels, not sentences
- Slide 8: "The bottom line" or equivalent

RULES for Zone B descriptions — write as an illustration brief, not a layout spec:
- Describe what is DRAWN, not how it is laid out. Name every box, figure, arrow, and label verbatim.
- Zone B must feel visually FULL. No large empty areas. Every diagram element has text inside it or a label beside it. Draw only the elements explicitly named in the Zone B description. Do not add additional diagram boxes, flowcharts, system maps, arrows, or text labels that are not listed in the description — any unlisted element is an error, not helpful elaboration.
- Text rendering rule: all text strings rendered inside Zone B — labels, captions, Kalam annotations — must be 3 words or fewer. Longer thoughts must be split into two separate short labels placed near each other. Never write a caption longer than 3 words as a single string. This is not a stylistic preference — longer strings render with garbled or invented characters; short strings render accurately.
- Always include at least one person figure when the content involves human roles (clinician, patient, admin, founder). Draw every person in the Akira Toriyama Dr Slump register: thick confident outline (2–3px, variable weight as if drawn with a felt-tip pen), slightly enlarged head (roughly 1/3 of figure height), two dot eyes with expression carried by dot angle, single curved mouth line, simplified rounded torso, tapered limb lines, three or four stubby fingers. No stethoscopes, no white coats, no profession props; pose and context identify the person. Use Toriyama-style motion marks freely: small radiating lines for surprise, speed lines for movement, a small teardrop sweat drop beside the head for stress. No shading, no fills; pure contour line on off-white. Every figure across all slides must feel like it belongs to the same visual universe: consistent outline weight, consistent head-to-body ratio, consistent face construction. Non-human elements (servers, buildings, smartphones, documents) may be drawn with slightly more detail but in the same thick-outline economical style. The figure's total height must not exceed 35% of Zone B's available height. The figure is a narrator alongside the diagram, not the subject of the slide — keep it to one side, smaller than the central diagram element.
- Style anchor: "hand-drawn editorial illustration — medical textbook sketch meets tech whiteboard." Clean ink lines, 1.5–2px, slightly imperfect. No shading. No gradients. Charcoal lines with dark-coral annotations on off-white.
- For Pillar 1 (infrastructure): draw a flow diagram with named boxes, arrows, and a GP or system figure. Every box must contain text. Include at least one Kalam annotation label naming a friction point or insight.
- For Pillar 2 (building in public): draw a before/after split or a numbered process with small figures at each step. Label every step verbatim.
- For Pillar 3 (policy): draw a large typographic pull-quote in DM Sans Bold occupying the left half, with a simple supporting diagram on the right (a bar, a split path, or a labelled comparison). One Kalam annotation naming the implication.
- Name all Kalam annotation text verbatim in the description (e.g. 'Kalam label: "unchanged since fax machines"').
- Specify curved arrow directions explicitly (e.g. "a bold curved dark-coral arrow sweeps from bottom-left upward to the central oval").
- Arrows are always smooth single-stroke lines with a small solid arrowhead. Never use x marks, cross symbols, or broken lines to indicate conflict or barriers — describe what the arrow connects, not what it means. If the concept requires showing a blocked path, use a horizontal bar or wall shape, never an x.

Output a JSON array (no markdown fence) of exactly 8 objects:
[
  {{
    "slide_number": 1,
    "zone_a_headline": "...",
    "zone_b_description": "..."
  }},
  ...
]"""

    user = f"""Post draft:
{post_draft[:1500]}

Pillar: {pillar}
Topic: {raw_input}
Plan: {plan[:500]}"""

    out = invoke("image_architect", system, user)

    slides = []
    try:
        json_match = re.search(r"\[[\s\S]*\]", out)
        if json_match:
            slides = json.loads(json_match.group(0))
    except (json.JSONDecodeError, ValueError):
        slides = []

    # Fallback: build minimal 8-slide plan from post draft
    if not slides or len(slides) < 2:
        words = post_draft.split()
        chunks = []
        for i in range(0, min(len(words), 56), 7):
            chunks.append(" ".join(words[i : i + 7]))
        while len(chunks) < 7:
            chunks.append(f"Point {len(chunks) + 1}")
        slides = [
            {"slide_number": 1, "zone_a_headline": post_hook[:60], "zone_b_description": "Opening context paragraph, 2–3 sentences from the post intro."},
        ] + [
            {"slide_number": i + 2, "zone_a_headline": chunks[i], "zone_b_description": f"Point {i + 1}: {chunks[i]}. Body text explains in 2–3 sentences."}
            for i in range(6)
        ] + [
            {"slide_number": 8, "zone_a_headline": "The bottom line", "zone_b_description": "Conclusion: 2–3 sentence summary of the key insight. No open question."},
        ]

    total = len(slides)
    image_prompts = []
    for s in slides:
        n = s.get("slide_number", len(image_prompts) + 1)
        headline = (s.get("zone_a_headline") or "").strip()
        zone_b = (s.get("zone_b_description") or "").strip()
        prompt = _build_slide_prompt(n, total, headline, zone_b, pillar, post_hook)
        image_prompts.append({
            "slide_number": n,
            "zone_a_headline": headline,
            "zone_b_description": zone_b,
            "prompt": prompt,
            "filename": f"slide_{n:02d}.png",
        })

    return {
        "image_prompts": image_prompts,
        "image_slide_count": len(image_prompts),
    }
