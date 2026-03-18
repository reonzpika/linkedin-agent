---
name: linkedin-image-generate
description: Generates LinkedIn carousel images for an approved post session using Nano Banana Pro (Gemini 2.5 Flash Image). Use when the user says "generate images", "create carousel images", "make slides for [session_id]", or when triggered automatically after draft approval in linkedin-post-create. Requires GOOGLE_GENAI_API_KEY in .env.
---

# LinkedIn Image Generation Skill

**Trigger:** "generate images", "create carousel images", "make slides", or automatically after draft approval in linkedin-post-create Phase 4b.

**Description:** Reads approved draft_final.md and plan.json from the session folder, runs Image Architect to build per-slide prompts, calls Gemini 2.5 Flash Image (Nano Banana Pro) API, saves PNGs to outputs/<session_id>/images/, and presents results for approval.

**Prerequisite:** draft_final.md must exist and be approved. GOOGLE_GENAI_API_KEY must be set in .env.

---

## Flow

### Step 1: Identify session

If the user names a session ID, use it. Otherwise, check the most recent session in outputs/ that has draft_final.md but no images_manifest.json.

Confirm with the user:
> "I'll generate carousel images for **[session_id]**. This will create 8 slides using the Dr Ryo Eguchi brand system (coral header, off-white body, Kalam/DM Sans fonts). Confirm to proceed."

Wait for confirmation before running the script.

---

### Step 2: Check prerequisites

1. Verify `GOOGLE_GENAI_API_KEY` is set in .env. If missing, tell the user:
   > "GOOGLE_GENAI_API_KEY is not set. Get a key from https://aistudio.google.com/app/apikey and add it to .env as: GOOGLE_GENAI_API_KEY=your_key_here"
   Then stop.

2. Check that `draft_final.md` exists in the session folder. If missing, tell the user to run the linkedin-post-create skill first.

3. Check that `google-genai` and `pillow` are installed:
   ```bash
   python -c "from google import genai; from PIL import Image; print('OK')"
   ```
   If not installed, run:
   ```bash
   pip install google-genai pillow
   ```

---

### Step 3: Run image generation

Run from repo root:
```bash
python scripts/generate_images.py --session-dir outputs/<session_id>
```

This takes 2–4 minutes for 8 slides (API calls are sequential with brief delays).

**While running, tell the user:**
> "Generating 8 slides — this takes about 2–4 minutes. Slide 1 is generated first and used as the style reference for slides 2–8 to ensure visual consistency."

If the script exits non-zero, show the error and offer to retry failed slides:
```bash
python scripts/generate_images.py --session-dir outputs/<session_id> --slides <failed_numbers>
```

---

### Step 4: Present results

After the script completes, read `outputs/<session_id>/images_manifest.json` and present:

```
Images generated for [session_id]

Slides:
  Slide 1: [zone_a_headline] — [status]
  Slide 2: [zone_a_headline] — [status]
  ...
  Slide 8: [zone_a_headline] — [status]

Images saved to: outputs/[session_id]/images/

What would you like to do?
- "Approve images" to proceed to assembly
- "Regenerate slide N" to redo a specific slide (e.g. "regenerate slide 3")
- "Regenerate all" to start fresh (use --no-reference flag)
- "Skip images" to proceed to assembly without images
```

---

### Step 5: Handle regeneration requests

If the user asks to regenerate specific slides:
```bash
python scripts/generate_images.py --session-dir outputs/<session_id> --slides <N,M>
```

If the user asks to regenerate all (style reset):
```bash
python scripts/generate_images.py --session-dir outputs/<session_id> --no-reference
```

After regeneration, return to Step 4 and show updated results.

---

### Step 6: Compile carousel PDF

Once the user approves the images, compile the PDF before proceeding to assembly:

```bash
python scripts/generate_images.py --session-dir outputs/<session_id> --compile-pdf
```

This reads the existing manifest and stitches approved slides into `outputs/<session_id>/images/carousel.pdf`. It does not regenerate any images.

If compilation succeeds, confirm in chat:
> "Carousel PDF compiled: outputs/[session_id]/images/carousel.pdf — ready for upload to LinkedIn."

If compilation fails, tell the user and offer to retry. The PDF step failing does not block assembly — the user can compile manually later.

### Step 7: Proceed to assembly

Continue with Phase 5 of linkedin-post-create (assemble_session_state.py + scheduling).

---

## Notes on the brand system

The brand system is defined in `knowledge/brand_design_language.md`. Key elements:
- **Coral `#E05C3A`** header block: full-width, no side margins, 180–220px tall
- **Headline** in Kalam Bold on coral, plus "Dr Ryo E." small label
- **Off-white `#F8F5F0`** body zone with 48px margins
- **"ClinicPro"** footer label, bottom-right, DM Sans Regular 11px warm grey
- **Annotations**: hand-drawn underlines/arrows/circles in dark coral `#B84A2E`
- **Never**: blue, gradients, dark mode, drop shadows, pure white

Slide 1 is always generated first without a reference image. Once slide 1 exists, it is attached as a reference image for slides 2–8 to maintain visual consistency across the series.

---

## Error handling

- **API key missing:** Tell user to set GOOGLE_GENAI_API_KEY and stop.
- **Quota exceeded:** Tell user they've hit Gemini API rate limits; suggest waiting 60 seconds and retrying failed slides.
- **All slides failed:** Check that GOOGLE_GENAI_API_KEY is valid at aistudio.google.com.
- **Some slides failed:** Retry with `--slides` flag for specific slides only.
- **Pillow not installed:** Run `pip install pillow` and retry.

---

## What this skill does NOT do

- Does not post images to LinkedIn (assembly handles that via PDF carousel upload).
- Does not modify the post text.
- Does not require Playwright or LinkedIn session.
