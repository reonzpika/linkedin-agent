"""
LinkedIn carousel image generation script.
Reads plan.json, draft_final.md from session dir; runs Image Architect agent to build
per-slide prompts; calls gemini-3-pro-image-preview via laozhang.ai (requests, no SDK)
at 2K 1:1; saves PNG files to outputs/<session_id>/images/; writes images_manifest.json.

Run from repo root:
  python scripts/generate_images.py --session-dir outputs/<session_id>

Optional flags:
  --slides 1,3,5     Regenerate specific slides only (comma-separated, 1-indexed)
  --no-reference     Skip reference image attachment (first generation only)

Requires: LAOZHANG_API_KEY (sk-xxx) and LAOZHANG_API_URL in .env.
Depends: requests, Pillow.
"""

import argparse
import base64
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import requests
from loguru import logger

DEFAULT_LAOZHANG_URL = "https://api.laozhang.ai/v1beta/models/gemini-3-pro-image-preview:generateContent"
TIMEOUT_SEC = 180


def _get_api_config() -> dict:
    """Return API key and full endpoint URL for laozhang image API. Raises RuntimeError if key not set."""
    api_key = os.getenv("LAOZHANG_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "LAOZHANG_API_KEY not set. Add it to .env (sk-xxx format from laozhang.ai)."
        )
    url = (os.getenv("LAOZHANG_API_URL") or DEFAULT_LAOZHANG_URL).strip()
    if not url:
        raise RuntimeError("LAOZHANG_API_URL must be non-empty if set.")
    return {"api_key": api_key, "url": url}


def _generate_single_slide(
    config: dict,
    prompt: str,
    reference_image_path: Path | None = None,
    retries: int = 2,
) -> bytes | None:
    """
    Call gemini-3-pro-image-preview via laozhang.ai for one slide (requests, no SDK).
    Uses generationConfig aspectRatio 1:1, imageSize 2K. Reference image as base64 inline_data in parts.
    Response: result['candidates'][0]['content']['parts'][0]['inlineData']['data'].
    Returns PNG bytes or None on failure.
    """
    url = config["url"]
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    parts: list[dict] = []

    if reference_image_path and reference_image_path.exists():
        try:
            img_bytes = reference_image_path.read_bytes()
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
            ref_text = (
                "Reference image above shows the approved brand style. "
                "Maintain this exactly: same coral header block dimensions, "
                "same off-white background, same footer position, same font feel. "
                "Now generate a new slide with the following spec:\n\n"
            )
            parts.append({"text": ref_text + prompt})
        except Exception as e:
            logger.warning("Could not attach reference image: {}. Proceeding without.", e)
            parts = [{"text": prompt}]
    else:
        parts = [{"text": prompt}]

    # Explicit aspectRatio (1:1) and imageSize (2K): laozhang defaults could change; 2K then
    # downscale to 1080 gives sharper carousel slides than 1K native. imageConfig nested under
    # generationConfig per laozhang docs; if first run returns a payload error, check that first.
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": "1:1", "imageSize": "2K"},
        },
    }

    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT_SEC)
            resp.raise_for_status()
            result = resp.json()
            cands = result.get("candidates") or []
            if not cands:
                logger.warning("Slide generation returned no candidates (attempt {})", attempt + 1)
                continue
            content = cands[0].get("content") or {}
            resp_parts = content.get("parts") or []
            if not resp_parts:
                logger.warning("Slide generation returned no parts (attempt {})", attempt + 1)
                continue
            first_part = resp_parts[0]
            inline = first_part.get("inlineData")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
            logger.warning("Slide generation returned no image data (attempt {})", attempt + 1)
        except requests.RequestException as e:
            logger.warning("Slide generation failed (attempt {}): {}", attempt + 1, e)
        except (KeyError, TypeError) as e:
            logger.warning("Unexpected response shape (attempt {}): {}", attempt + 1, e)
        if attempt < retries:
            time.sleep(2 ** attempt)

    return None


def _save_image_bytes(image_bytes: bytes, output_path: Path) -> bool:
    """Save raw image bytes as PNG. Returns True on success."""
    try:
        from PIL import Image
        img = Image.open(BytesIO(image_bytes))
        # Ensure 2048×2048 for carousel slides (2K)
        if output_path.stem.startswith("slide_"):
            if img.size != (2048, 2048):
                img = img.resize((2048, 2048), Image.LANCZOS)
        img.save(str(output_path), "PNG")
        return True
    except ImportError:
        # Fallback: write raw bytes directly
        output_path.write_bytes(image_bytes)
        return True
    except Exception as e:
        logger.error("Could not save image to {}: {}", output_path, e)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate LinkedIn carousel images using Nano Banana Pro (gemini-3-pro-image-preview, 2K)."
    )
    parser.add_argument(
        "--session-dir",
        type=str,
        required=True,
        help="Path to session folder (e.g. outputs/2026-03-05_topic)",
    )
    parser.add_argument(
        "--slides",
        type=str,
        default="",
        help="Comma-separated slide numbers to regenerate (e.g. '1,3,5'). Default: all slides.",
    )
    parser.add_argument(
        "--no-reference",
        action="store_true",
        help="Skip reference image attachment (use for first generation or style reset).",
    )
    parser.add_argument(
        "--compile-pdf",
        action="store_true",
        help="After generating images, compile all slides into a single carousel.pdf in the session images directory.",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Run Image Architect to build slide plan and write images_plan.json, then exit without generating any images.",
    )
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.is_absolute():
        session_dir = ROOT / session_dir
    if not session_dir.exists():
        print(f"Error: Session directory not found: {session_dir}", file=sys.stderr)
        return 1

    # Required files
    draft_file = session_dir / "draft_final.md"
    plan_file = session_dir / "plan.json"
    input_file = session_dir / "input.json"
    if not draft_file.exists():
        print("Error: draft_final.md not found. Run draft.py first.", file=sys.stderr)
        return 1
    if not plan_file.exists():
        print("Error: plan.json not found. Run plan_from_url.py first.", file=sys.stderr)
        return 1

    post_draft = draft_file.read_text(encoding="utf-8")
    plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
    pillar = plan_data.get("pillar") or "pillar_1"
    raw_input = ""
    if input_file.exists():
        input_data = json.loads(input_file.read_text(encoding="utf-8"))
        raw_input = (input_data.get("topic") or input_data.get("url") or "").strip()

    # Output directory
    images_dir = session_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Parse slide filter
    slide_filter: set[int] = set()
    if args.slides:
        for s in args.slides.split(","):
            try:
                slide_filter.add(int(s.strip()))
            except ValueError:
                pass

    # Check for existing manifest (for partial regeneration)
    manifest_file = session_dir / "images_manifest.json"
    existing_manifest: list[dict] = []
    if manifest_file.exists():
        try:
            existing_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            existing_manifest = []

    # Plan file: written by --plan-only, read back on subsequent generation runs
    plan_output_file = session_dir / "images_plan.json"

    # Run Image Architect to build prompts (or load approved plan if it exists)
    if plan_output_file.exists() and not args.plan_only:
        print("Loading approved slide plan from images_plan.json...")
        try:
            saved_plan = json.loads(plan_output_file.read_text(encoding="utf-8"))
            image_prompts_raw: list[dict] = saved_plan.get("slides") or []
        except Exception:
            image_prompts_raw = []
        if image_prompts_raw:
            # Rebuild full prompts from the saved headlines/descriptions so edits are respected
            from agents.image_architect import _build_slide_prompt
            lines_hook = [l.strip() for l in post_draft.split("\n") if l.strip()]
            post_hook = lines_hook[0][:140] if lines_hook else raw_input[:140]
            total_saved = len(image_prompts_raw)
            image_prompts: list[dict] = []
            for s in image_prompts_raw:
                n = s.get("slide_number", len(image_prompts) + 1)
                headline = (s.get("zone_a_headline") or "").strip()
                zone_b = (s.get("zone_b_description") or "").strip()
                prompt = _build_slide_prompt(n, total_saved, headline, zone_b, pillar, post_hook)
                image_prompts.append({
                    "slide_number": n,
                    "zone_a_headline": headline,
                    "zone_b_description": zone_b,
                    "prompt": prompt,
                    "filename": f"slide_{n:02d}.png",
                })
            print(f"Loaded {len(image_prompts)} slides from approved plan.")
        else:
            image_prompts = []
    else:
        print("Building slide prompts via Image Architect...")
        from agents.image_architect import run as image_architect_run

        state = {
            "post_draft": post_draft,
            "pillar": pillar,
            "raw_input": raw_input,
            "plan": plan_data.get("plan") or "",
        }
        arch_result = image_architect_run(state)
        image_prompts = arch_result.get("image_prompts") or []

    if not image_prompts:
        print("Error: Image Architect produced no prompts.", file=sys.stderr)
        return 1

    # --plan-only: write images_plan.json and exit without generating images
    if args.plan_only:
        plan_data_out = {
            "slides": [
                {
                    "slide_number": p["slide_number"],
                    "zone_a_headline": p["zone_a_headline"],
                    "zone_b_description": p["zone_b_description"],
                }
                for p in image_prompts
            ]
        }
        plan_output_file.write_text(json.dumps(plan_data_out, indent=2), encoding="utf-8")
        print(f"\nSlide plan written to {plan_output_file}")
        print(f"\n{'='*60}")
        for p in image_prompts:
            print(f"\nSlide {p['slide_number']}: {p['zone_a_headline']}")
            print(f"  {p['zone_b_description']}")
        print(f"\n{'='*60}")
        print("Review the plan above. Edit images_plan.json if needed, then run without --plan-only to generate images.")
        return 0

    print(f"Image Architect produced {len(image_prompts)} slide prompts.")

    # Initialise API config (laozhang.ai via requests)
    try:
        api_config = _get_api_config()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Reference image: use slide_01 if it exists and --no-reference not set
    reference_path: Path | None = None
    if not args.no_reference:
        candidate = images_dir / "slide_01.png"
        if candidate.exists():
            reference_path = candidate
            print(f"Using {reference_path.name} as style reference for consistency.")

    # Generate slides
    manifest: list[dict] = []
    total = len(image_prompts)
    success_count = 0
    fail_count = 0

    for item in image_prompts:
        slide_num = item["slide_number"]

        # Skip if slide filter is active and this slide not in filter
        if slide_filter and slide_num not in slide_filter:
            # Carry over from existing manifest if available
            existing = next(
                (e for e in existing_manifest if e.get("slide_number") == slide_num),
                None,
            )
            if existing:
                manifest.append(existing)
            continue

        filename = item["filename"]
        output_path = images_dir / filename
        print(f"Generating slide {slide_num}/{total}: {item['zone_a_headline'][:50]}...")

        # For slide 1, never use a reference (it IS the reference)
        ref = None if slide_num == 1 else reference_path
        image_bytes = _generate_single_slide(api_config, item["prompt"], ref)

        if image_bytes:
            saved = _save_image_bytes(image_bytes, output_path)
            if saved:
                # Set slide_01 as reference for subsequent slides
                if slide_num == 1 and not args.no_reference:
                    reference_path = output_path
                    print(f"Slide 1 generated — using as style reference for slides 2–{total}.")
                success_count += 1
                manifest.append({
                    "slide_number": slide_num,
                    "filename": filename,
                    "path": str(output_path.relative_to(ROOT)),
                    "zone_a_headline": item["zone_a_headline"],
                    "zone_b_description": item["zone_b_description"],
                    "status": "generated",
                })
                print(f"  Saved: {output_path.name}")
            else:
                fail_count += 1
                manifest.append({
                    "slide_number": slide_num,
                    "filename": filename,
                    "path": "",
                    "zone_a_headline": item["zone_a_headline"],
                    "zone_b_description": item["zone_b_description"],
                    "status": "save_failed",
                })
        else:
            fail_count += 1
            manifest.append({
                "slide_number": slide_num,
                "filename": filename,
                "path": "",
                "zone_a_headline": item["zone_a_headline"],
                "zone_b_description": item["zone_b_description"],
                "status": "generation_failed",
            })
            print(f"  FAILED: slide {slide_num} could not be generated.")

        # Rate limiting: brief pause between API calls
        if slide_num < total:
            time.sleep(1.5)

    # Sort manifest by slide number and write
    manifest.sort(key=lambda x: x.get("slide_number", 0))
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if args.compile_pdf:
        try:
            from PIL import Image as PILImage
            generated = [m for m in manifest if m.get("status") == "generated" and m.get("path")]
            generated.sort(key=lambda x: x.get("slide_number", 0))
            if generated:
                pdf_path = images_dir / "carousel.pdf"
                pil_images = [PILImage.open(ROOT / m["path"]).convert("RGB") for m in generated]
                pil_images[0].save(
                    str(pdf_path),
                    save_all=True,
                    append_images=pil_images[1:],
                )
                print(f"  Carousel PDF: {pdf_path}")
            else:
                print("  No generated slides found for PDF compilation.")
        except Exception as e:
            print(f"  PDF compilation failed: {e}")

    print(f"\nImage generation complete.")
    print(f"  Success: {success_count}/{total} slides")
    if fail_count:
        print(f"  Failed:  {fail_count}/{total} slides")
        print(f"  Retry failed slides with: python scripts/generate_images.py --session-dir {session_dir} --slides {','.join(str(m['slide_number']) for m in manifest if m['status'] != 'generated')}")
    print(f"  Images: {images_dir}")
    print(f"  Manifest: {manifest_file}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
