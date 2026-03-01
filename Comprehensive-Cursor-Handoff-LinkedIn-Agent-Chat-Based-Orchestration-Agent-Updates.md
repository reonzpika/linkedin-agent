# Comprehensive Cursor Handoff: LinkedIn Agent Chat-Based Orchestration + Agent Updates

## Overview

This handoff implements **two major changes**:

1. **Agent workflow improvements** (original plan): Scout personal feed scraping, Architect comment drafting, Strategist validation
2. **Chat-based orchestration** (new architecture): Split into 2 scripts, Cursor orchestrates via chat, OS scheduling, 3 skills

---

## Part 1: Core Agent Updates (Original Plan)

### 1.1 tools/browser.py - Add scraping functions

**Add `scrape_personal_feed(context, max_posts=20)`**:
```python
def scrape_personal_feed(context: Any, max_posts: int = 20) -> list[dict[str, Any]]:
    """
    Navigate to LinkedIn personal feed, scrape recent posts.
    Returns list of {name, url, post_url, snippet, posted_date}.
    """
    page = context.new_page()
    results = []
    try:
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
        _random_delay()
        dismiss_modal_if_present(page)
        
        # Scroll once to load more posts
        page.evaluate("window.scrollBy(0, 1000)")
        _random_delay()
        
        # Extract post cards
        posts = page.locator("[data-id*='urn:li:activity']").all()[:max_posts]
        
        for post in posts:
            try:
                # Author name
                author_elem = post.locator(".update-components-actor__name").first
                name = author_elem.inner_text()[:80] if author_elem.count() > 0 else "LinkedIn User"
                
                # Post URL
                link = post.locator("a[href*='/posts/'], a[href*='/feed/update']").first
                if link.count() == 0:
                    continue
                href = link.get_attribute("href") or ""
                post_url = href if href.startswith("http") else f"https://www.linkedin.com{href}"
                
                # Snippet
                desc_elem = post.locator(".feed-shared-update-v2__description").first
                snippet = desc_elem.inner_text()[:200] if desc_elem.count() > 0 else ""
                
                # Posted date (optional)
                time_elem = post.locator("time").first
                posted_date = time_elem.get_attribute("datetime") or "" if time_elem.count() > 0 else ""
                
                results.append({
                    "name": name,
                    "url": post_url,  # Use post_url as url for test compatibility
                    "post_url": post_url,
                    "snippet": snippet,
                    "posted_date": posted_date
                })
            except Exception:
                continue
                
        return results
    except Exception as e:
        logger.warning(f"scrape_personal_feed failed: {e}")
        return []
    finally:
        page.close()
```

**Add `scrape_hashtag_posts(context, hashtags, max_posts=20)`**:
```python
def scrape_hashtag_posts(
    context: Any, 
    hashtags: list[str], 
    max_posts: int = 20
) -> list[dict[str, Any]]:
    """
    Navigate to LinkedIn hashtag feeds, scrape recent posts.
    Returns list of {name, url, post_url, snippet, posted_date}.
    """
    page = context.new_page()
    all_results = []
    seen_urls = set()
    
    try:
        for hashtag in hashtags[:3]:  # Limit to 3 hashtags
            clean_tag = hashtag.strip('#').lower()
            try:
                page.goto(
                    f"https://www.linkedin.com/feed/hashtag/{clean_tag}/",
                    wait_until="domcontentloaded",
                    timeout=20000
                )
                _random_delay()
                dismiss_modal_if_present(page)
                page.evaluate("window.scrollBy(0, 1000)")
                _random_delay()
                
                # Extract posts (same logic as personal feed)
                posts = page.locator("[data-id*='urn:li:activity']").all()[:10]
                
                for post in posts:
                    try:
                        author_elem = post.locator(".update-components-actor__name").first
                        name = author_elem.inner_text()[:80] if author_elem.count() > 0 else "LinkedIn User"
                        
                        link = post.locator("a[href*='/posts/'], a[href*='/feed/update']").first
                        if link.count() == 0:
                            continue
                        href = link.get_attribute("href") or ""
                        post_url = href if href.startswith("http") else f"https://www.linkedin.com{href}"
                        
                        if post_url in seen_urls:
                            continue
                        seen_urls.add(post_url)
                        
                        desc_elem = post.locator(".feed-shared-update-v2__description").first
                        snippet = desc_elem.inner_text()[:200] if desc_elem.count() > 0 else ""
                        
                        time_elem = post.locator("time").first
                        posted_date = time_elem.get_attribute("datetime") or "" if time_elem.count() > 0 else ""
                        
                        all_results.append({
                            "name": name,
                            "url": post_url,
                            "post_url": post_url,
                            "snippet": snippet,
                            "posted_date": posted_date
                        })
                        
                        if len(all_results) >= max_posts:
                            break
                    except Exception:
                        continue
                        
                if len(all_results) >= max_posts:
                    break
            except Exception:
                continue  # Skip failed hashtags
                
        return all_results[:max_posts]
    except Exception as e:
        logger.warning(f"scrape_hashtag_posts failed: {e}")
        return []
    finally:
        page.close()
```

### 1.2 agents/researcher.py - Pillar classification

Update system prompt (keep existing fallback `pillar = state.get("pillar") or "pillar_1"`):

```python
system = f"""You are an NZ Health Researcher. Use only the following context. Output a single block in this exact format:

<SOLUTION>
pillar: pillar_1|pillar_2|pillar_3
research_summary: [max 300 words, synthesised from the provided sources; NZ focus]
target_urls: [comma-separated list of 3-5 source URLs from the context]
</SOLUTION>

Pillar classification rules:
- pillar_1 (NZ Primary Care Infrastructure): Medtech, HealthLink, clinical software, APIs, cloud migrations, technical infrastructure, what breaks and why
- pillar_2 (Building in Public): Product development, GP feedback, feature shipping, learning from users, what GPs actually want vs what they say
- pillar_3 (Policy/Admin): Workforce issues, regulatory changes, practice management, admin burden, government policy, PHO communications

NZ context (glossary): {nz_context[:3000]}

Dehallucination: if the topic touches any of these, output instead a single line: DEHALLUCINATION: [the exact clarification question from the table]. Topics: {dehallucination[:2000]}
"""
```

### 1.3 agents/scout.py - Complete rewrite

```python
"""
LinkedIn Scout: Golden Hour target discovery via personal feed + hashtag scraping.
Returns 6 recent post targets for engagement; does NOT draft comments (Architect's job).
"""

import json
import re
from pathlib import Path

from graph.state import LinkedInContext

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"
OUTPUTS = Path(__file__).resolve().parent.parent / "outputs"


def _load_recent_engagement_urls() -> set[str]:
    """Load URLs from all engagement.json files to avoid repeats."""
    recent_urls = set()
    if OUTPUTS.exists():
        for p in OUTPUTS.rglob("engagement.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for t in data.get("targets", []) or data.get("scout_targets", []):
                    u = t.get("url") or t.get("post_url")
                    if u:
                        recent_urls.add(u)
            except Exception:
                pass
    return recent_urls


def _filter_spam_and_recruiters(posts: list[dict]) -> list[dict]:
    """Filter out recruiters, hiring posts, vendor spam."""
    filtered = []
    for post in posts:
        author_name = (post.get("name") or "").lower()
        snippet = (post.get("snippet") or "").lower()
        
        # Skip recruiters
        if any(word in author_name for word in ["recruiter", "hiring", "recruitment", "talent acquisition"]):
            continue
        
        # Skip hiring posts
        if any(phrase in snippet for phrase in ["we're hiring", "job opening", "apply now", "join our team"]):
            continue
        
        # Skip vendor spam
        if any(phrase in snippet for phrase in ["buy now", "limited offer", "demo", "free trial"]):
            continue
        
        filtered.append(post)
    
    return filtered


def run(state: LinkedInContext) -> dict:
    """
    Find 6 recent posts from target audience for Golden Hour engagement.
    Primary: scrape personal feed. Fallback: hashtag scraping if <6 found.
    Returns scout_targets only (no comments).
    """
    raw_input = state.get("raw_input") or ""
    recent_urls = _load_recent_engagement_urls()
    
    from tools.browser import get_browser_context, scrape_personal_feed, scrape_hashtag_posts
    
    ctx = get_browser_context()
    scout_targets = []
    
    try:
        # Primary: scrape personal feed
        feed_posts = scrape_personal_feed(ctx, max_posts=20)
        
        # Filter spam and recent targets
        filtered = _filter_spam_and_recruiters(feed_posts)
        filtered = [p for p in filtered if p.get("post_url") not in recent_urls]
        
        # Optional keyword relevance filter
        if raw_input:
            keywords = raw_input.lower().split()[:3]
            relevant = []
            for post in filtered:
                snippet = (post.get("snippet") or "").lower()
                if any(kw in snippet for kw in keywords):
                    relevant.append(post)
            if len(relevant) >= 3:
                filtered = relevant
        
        scout_targets = filtered[:6]
        
        # Fallback: hashtag scraping if <6
        if len(scout_targets) < 6:
            hashtag_path = KNOWLEDGE / "hashtag_library.md"
            if hashtag_path.exists():
                hashtag_text = hashtag_path.read_text(encoding="utf-8")
                hashtags = re.findall(r'#[A-Za-z0-9_]+', hashtag_text)[:5]
                
                if hashtags:
                    hashtag_posts = scrape_hashtag_posts(ctx, hashtags, max_posts=20)
                    filtered_hashtag = _filter_spam_and_recruiters(hashtag_posts)
                    filtered_hashtag = [p for p in filtered_hashtag if p.get("post_url") not in recent_urls]
                    
                    for post in filtered_hashtag:
                        if len(scout_targets) >= 6:
                            break
                        if post.get("post_url") not in [t.get("post_url") for t in scout_targets]:
                            scout_targets.append(post)
        
    finally:
        ctx.close()
    
    # Normalize: ensure 'rationale' field exists (Architect expects it)
    for target in scout_targets:
        if "snippet" in target and "rationale" not in target:
            target["rationale"] = target["snippet"]
    
    return {"scout_targets": scout_targets}
```

### 1.4 agents/architect.py - Add comment drafting

Update system prompt and parsing (around line 31):

```python
scout_targets = state.get("scout_targets") or []

system = f"""You are the Content Architect. Draft one LinkedIn post AND 6 Golden Hour engagement comments.

Voice and rules: {voice[:2500]}

Algorithm: {algo[:1500]}

Hashtag library (pick 3-4): {hashtag_lib[:1500]}

POST REQUIREMENTS:
- 150-300 words
- Structure: Hook (specific clinical observation) → systemic point (1-2 paragraphs) → insider take (conclusion, not question)
- No links in body, no banned terms, end with conclusion

FIRST COMMENT REQUIREMENTS:
- Placeholder for outbound URL or short comment
- Links go here only
- NO engagement-bait questions

GOLDEN HOUR COMMENTS (6 required):
- Draft exactly 6 comments for pre-engagement on other LinkedIn posts
- Each: 2-3 sentences, substantive, reference specific point from target's post
- Use target snippets below to tailor each comment
- Must reinforce pillar positioning of your main post
- NO generic praise, NO engagement-bait questions
- Comment order MUST match target order: comment 1 for target 1, etc.

Medtech/ALEX framing: ALEX is API/integration platform, not clinical UI. Don't describe as "crashing". Acknowledge Medtech progress before naming gaps.

Output format:
<SOLUTION>
post_draft:
[150-300 words]
first_comment:
[Placeholder or short comment; no engagement bait]
hashtags:
[3-4 hashtags, one per line]
</SOLUTION>

<COMMENTS>
[Exactly 6 lines, one comment per line. Line 1 for target 1, line 2 for target 2, etc.]
</COMMENTS>
"""

user = f"""Topic: {raw_input}. Pillar: {pillar}. Research: {research_summary[:2000]}.

Scout targets for Golden Hour engagement (draft tailored comments for each):
{json.dumps([{"index": i+1, "name": t.get("name", ""), "snippet": t.get("rationale", "")[:200]} for i, t in enumerate(scout_targets[:6])], indent=2)}
"""

# ... existing parsing for post_draft, first_comment, hashtags ...

# Add comment parsing:
comments_list = []
comments_match = re.search(r"<COMMENTS>\s*(.*?)\s*</COMMENTS>", out, re.DOTALL)
if comments_match:
    comments_block = comments_match.group(1).strip()
    comments_list = [line.strip() for line in comments_block.split("\n") if line.strip()][:6]

# Pad if needed
while len(comments_list) < 6:
    comments_list.append("Interesting perspective. This aligns with what we're seeing in NZ primary care.")

comments_list = comments_list[:6]

return {
    "post_draft": post_draft,
    "first_comment": first_comment,
    "hashtags": hashtags,
    "comments_list": comments_list,  # NEW
}
```

### 1.5 agents/strategist.py - Validate comment count

Add after existing failures checks (around line 50):

```python
# Validate comment count matches target count
scout_targets = state.get("scout_targets") or []
if len(comments_list) != len(scout_targets):
    failures.append(f"Comment count mismatch: {len(comments_list)} comments for {len(scout_targets)} targets")
```

### 1.6 tests/test_agents.py - Update for 6 targets/comments

```python
# Extend MOCK_SCOUT_TARGETS to 6 items
MOCK_SCOUT_TARGETS = [
    # ... existing 3 ...
    {"name": "Dr Jane Smith", "url": "https://linkedin.com/in/janesmith", "post_url": "https://linkedin.com/posts/abc4", "rationale": "Practice efficiency discussion"},
    {"name": "Tom Wilson - Practice Manager", "url": "https://linkedin.com/in/tomwilson", "post_url": "https://linkedin.com/posts/abc5", "rationale": "Admin burden insights"},
    {"name": "Dr Lisa Chen", "url": "https://linkedin.com/in/lisachen", "post_url": "https://linkedin.com/posts/abc6", "rationale": "Workforce retention strategies"},
]

# In test: Do NOT pre-fill comments_list, Architect will generate it
state = {
    "raw_input": "Medtech ALEX",
    "research_summary": "...",
    "pillar": "pillar_1",
    "scout_targets": MOCK_SCOUT_TARGETS,
    "comments_list": [],  # Empty, Architect fills it
}

architect_result = architect_run(state)
state.update(architect_result)

assert len(state.get("comments_list", [])) == 6, "Architect must generate 6 comments"
```

---

## Part 2: Chat-Based Orchestration Architecture

### 2.1 Create `/temporary` folder structure

```
/project-root/
├── /temporary/              # NEW - intermediate state files
│   ├── review_ready.json    # Signals prepare_post.py completed
│   ├── approved.json        # Signals user approved draft
│   └── pending_posts.json   # Scheduled posts queue
```

### 2.2 Create `prepare_post.py` (replaces current main.py for chat workflow)

```python
"""
LinkedIn Post Preparation Script
Runs workflow until human review, then EXITS (no pause/wait).
Writes outputs and review marker for Cursor orchestration.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

def main():
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    if not topic:
        print("Error: No topic provided")
        sys.exit(1)
    
    from graph.workflow import get_compiled_graph_prepare  # New function
    
    thread_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    config = {"configurable": {"thread_id": thread_id}}
    
    graph = get_compiled_graph_prepare()  # Graph that stops at review
    result = graph.invoke({"raw_input": topic, "logs": []}, config=config)
    
    # Save outputs
    from main import output_dir_for_topic
    output_dir = output_dir_for_topic(topic)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    (output_dir / "research.md").write_text(result.get("research_summary", ""), encoding="utf-8")
    (output_dir / "plan.md").write_text(result.get("plan", ""), encoding="utf-8")
    (output_dir / "draft_final.md").write_text(result.get("post_draft", ""), encoding="utf-8")
    (output_dir / "engagement.json").write_text(
        json.dumps({
            "scout_targets": result.get("scout_targets", []),
            "comments_list": result.get("comments_list", [])
        }, indent=2),
        encoding="utf-8"
    )
    
    state_for_save = {k: v for k, v in result.items() if k not in ("logs", "__interrupt__")}
    (output_dir / "session_state.json").write_text(
        json.dumps(state_for_save, indent=2, default=str), encoding="utf-8"
    )
    
    # Write review marker for Cursor
    marker = {
        "status": "ready_for_review",
        "session_id": output_dir.name,
        "output_dir": str(output_dir),
        "thread_id": thread_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    temp_dir = ROOT / "temporary"
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "review_ready.json").write_text(json.dumps(marker, indent=2), encoding="utf-8")
    
    print(f"✓ Draft completed. Outputs saved to {output_dir}")
    print(f"✓ Review marker written to temporary/review_ready.json")
    sys.exit(0)  # EXIT (don't pause)

if __name__ == "__main__":
    main()
```

### 2.3 Create `execute_post.py` (scheduled execution)

```python
"""
LinkedIn Post Execution Script
Reads approved state, executes Golden Hour posting.
Called by OS scheduler at designated time.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

def main():
    if len(sys.argv) < 2:
        print("Error: No session_id provided")
        sys.exit(1)
    
    session_id = sys.argv[1]  # e.g. "2026-03-01_medtech-alex"
    output_dir = ROOT / "outputs" / session_id
    
    if not output_dir.exists():
        print(f"Error: Output directory not found: {output_dir}")
        sys.exit(1)
    
    # Load approved state
    state_file = output_dir / "session_state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    
    # Execute posting
    from graph.workflow import executor_run  # Import executor function
    from tools.browser import get_browser_context
    
    context = get_browser_context()
    
    try:
        result = executor_run(state, context)
        
        # Save execution results
        (output_dir / "execution_results.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        
        # Remove from pending queue
        temp_dir = ROOT / "temporary"
        pending_file = temp_dir / "pending_posts.json"
        if pending_file.exists():
            pending = json.loads(pending_file.read_text(encoding="utf-8"))
            pending["posts"] = [p for p in pending.get("posts", []) if p.get("session_id") != session_id]
            pending_file.write_text(json.dumps(pending, indent=2), encoding="utf-8")
        
        print(f"✓ Execution completed for {session_id}")
        sys.exit(0)
        
    except Exception as e:
        print(f"✗ Execution failed: {e}")
        sys.exit(1)
    finally:
        context.close()

if __name__ == "__main__":
    main()
```

### 2.4 Create OS scheduling helper

Create `tools/scheduler.py`:

```python
"""
Cross-platform OS scheduling for LinkedIn post execution.
"""

import platform
import subprocess
from datetime import datetime
from pathlib import Path

def schedule_execution(session_id: str, execution_time: datetime) -> dict:
    """
    Schedule execute_post.py to run at execution_time using OS scheduler.
    Returns {success: bool, task_id: str, error: str}
    """
    script_path = Path(__file__).resolve().parent.parent / "execute_post.py"
    python_exe = "python"  # or sys.executable
    
    system = platform.system()
    
    try:
        if system == "Windows":
            # Use schtasks
            task_name = f"LinkedInPost_{session_id}"
            date_str = execution_time.strftime("%Y-%m-%d")
            time_str = execution_time.strftime("%H:%M")
            
            cmd = [
                "schtasks", "/create",
                "/tn", task_name,
                "/tr", f'"{python_exe}" "{script_path}" {session_id}',
                "/sc", "once",
                "/sd", date_str,
                "/st", time_str,
                "/f"  # Force overwrite if exists
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {"success": True, "task_id": task_name, "error": ""}
            else:
                return {"success": False, "task_id": "", "error": result.stderr}
                
        elif system in ["Darwin", "Linux"]:
            # Use 'at' command (simpler than cron for one-time tasks)
            time_str = execution_time.strftime("%H:%M %Y-%m-%d")
            cmd = f'echo "{python_exe} {script_path} {session_id}" | at {time_str}'
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Extract job ID from 'at' output
                job_id = result.stderr.split()[-1] if result.stderr else "unknown"
                return {"success": True, "task_id": job_id, "error": ""}
            else:
                return {"success": False, "task_id": "", "error": result.stderr}
        else:
            return {"success": False, "task_id": "", "error": f"Unsupported OS: {system}"}
            
    except Exception as e:
        return {"success": False, "task_id": "", "error": str(e)}
```

### 2.5 Update `graph/workflow.py`

Add function to compile graph without executor (stops at review):

```python
def get_compiled_graph_prepare():
    """
    Compile graph for preparation only (stops before executor).
    Used by prepare_post.py.
    """
    # Same as get_compiled_graph() but don't add executor node
    # Or add conditional that skips executor
    # Implementation depends on your current workflow structure
    pass
```

Extract executor logic into standalone function:

```python
def executor_run(state: dict, context: Any) -> dict:
    """
    Execute Golden Hour posting protocol.
    Can be called standalone by execute_post.py.
    """
    scout_targets = state.get("scout_targets", [])[:6]
    comments_list = state.get("comments_list", [])
    post_draft = state.get("post_draft", "")
    first_comment = state.get("first_comment", "")
    
    from tools.browser import post_comment, schedule_post
    
    results = []
    
    # Post main content
    post_result = schedule_post(context, post_draft, first_comment, "")
    results.append({"type": "main_post", "result": post_result})
    
    # Post Golden Hour comments
    for i, target in enumerate(scout_targets):
        if i >= len(comments_list):
            break
        comment_text = comments_list[i]
        post_url = target.get("post_url", "")
        
        if post_url and comment_text:
            comment_result = post_comment(context, post_url, comment_text)
            results.append({
                "type": "comment",
                "target": target.get("name", ""),
                "result": comment_result
            })
    
    return {"execution_results": results}
```

---

## Part 3: Skills Implementation

### 3.1 Create Skill 1: linkedin-post-create

Create `/mnt/skills/user/linkedin-post-create/SKILL.md`:

```markdown
# LinkedIn Post Creation Skill

**Trigger**: "create linkedin post", "draft post about", "write about [topic]"

**Description**: Orchestrates LinkedIn post creation workflow: pre-flight questions, research, drafting, review loop, and scheduling.

---

## Orchestration Protocol

### Phase 1: Pre-Flight Questions (Plan Mode)

Ask 2-3 clarifying questions before running workflow:

1. **Pillar preference**: "Which content pillar does this fit? (1: Infrastructure, 2: Building in Public, 3: Policy/Admin, or auto-detect?)"
2. **Specific angle**: "Any specific hook or observation you want highlighted?"

If user provides no topic, ask: "What topic would you like to create a post about?"

Show execution plan:
```
Plan: I'll research NZ primary care context, scout 6 Golden Hour targets from your feed, draft post + comments, and schedule for next Golden Hour (8am NZST tomorrow). Approve?
```

Wait for approval before proceeding.

---

### Phase 2: Execute Workflow

Run: `python prepare_post.py "[topic]" --pillar [1|2|3]`

Monitor for completion by watching `/temporary/review_ready.json`.

---

### Phase 3: Review Loop

When `review_ready.json` appears:

1. Read outputs from session folder
2. Format review in chat:

```
📝 Draft Ready for Review

POST:
[post_draft with line breaks preserved]

HASHTAGS: [list]
FIRST COMMENT: [first_comment]

GOLDEN HOUR COMMENTS (6):
1. [target.name] → [comment]
   Link: [target.post_url]
2. ...

What would you like to do?
- "Approve" to schedule
- Request specific changes (I'll edit and show diff)
- "Regenerate" to run Architect again
```

3. Handle user response:
   - **Approve**: Move to Phase 4
   - **Edit request**: Apply changes directly to draft, show diff, ask "Approve these changes?"
   - **Regenerate**: Re-run Architect with feedback, return to review

---

### Phase 4: Scheduling

After approval:

1. Calculate next Golden Hour (8:00am NZST, tomorrow if after 8am today)
2. Create OS scheduled task using `tools/scheduler.py`
3. Write to `/temporary/approved.json`:
   ```json
   {
     "session_id": "2026-03-01_medtech-alex",
     "approved_at": "2026-03-01T17:30:00Z",
     "scheduled_for": "2026-03-02T08:00:00+13:00"
   }
   ```
4. Append to `/temporary/pending_posts.json`
5. Confirm in chat:
   ```
   ✓ Approved and scheduled
   Post will go live: Tomorrow 8:00am NZST
   Session: 2026-03-01_medtech-alex
   
   I'll execute the Golden Hour protocol automatically.
   ```

---

### Phase 5: Learning from Feedback

If user requests changes during review:

1. Apply changes
2. Derive rule from feedback (if pattern detected)
3. Follow Self-Improvement Protocol from AGENTS.md:
   - Identify which knowledge file to update
   - Announce: "Updating [file]: [specific rule]"
   - Update file immediately
4. Continue with review

---

## Error Handling

**Script fails**: Show error, offer to retry or abort  
**Scheduling fails**: Warn user, offer manual execution  
**No targets found**: Explain Scout found 0 targets, suggest running `python scripts/login.py` to refresh session

---

## Success Criteria

- User approves draft with minimal edits (<3 requests)
- Scheduling succeeds
- User understands when post will go live
- No exposed credentials or errors in chat
```

### 3.2 Create Skill 2: linkedin-post-execute

Create `/mnt/skills/user/linkedin-post-execute/SKILL.md`:

```markdown
# LinkedIn Post Execution Skill

**Trigger**: Internal (called by OS scheduler), or manual "execute [session_id]"

**Description**: Executes Golden Hour posting protocol for approved session.

---

## Execution Protocol

### Invocation

Called by OS scheduler at designated time:
```
python execute_post.py [session_id]
```

Or manually in chat: "Execute 2026-03-01_medtech-alex"

---

### Process

1. Load session state from `/outputs/[session_id]/session_state.json`
2. Verify approval marker in `/temporary/approved.json`
3. Execute posting:
   - Main post + first comment
   - 6 Golden Hour comments to scout targets
4. Save execution results to `execution_results.json`
5. Remove from `/temporary/pending_posts.json`

---

### Post-Execution

If Cursor is open when execution completes:
- Check `/outputs/[session_id]/execution_results.json`
- Announce in chat:
  ```
  ✓ Posted successfully at 8:00am NZST
  Session: 2026-03-01_medtech-alex
  Results: 1 post + 6 comments
  
  View outputs: outputs/2026-03-01_medtech-alex/
  ```

If any failures occurred:
- Show which actions failed
- Offer to retry failed actions manually
- Log to session logs

---

## Error Handling

**Browser session expired**: Notify user to run `python scripts/login.py`  
**Posting fails**: Save error details, notify user, offer manual retry  
**Network issues**: Retry once, then abort and notify

---

## Success Criteria

- All actions execute without errors
- Execution results saved
- User notified (if Cursor open)
- Pending queue updated
```

### 3.3 Create Skill 3: linkedin-agent-improve

Create `/mnt/skills/user/linkedin-agent-improve/SKILL.md`:

```markdown
# LinkedIn Agent Self-Improvement Skill

**Trigger**: User gives feedback on draft quality, voice, structure, or agent behavior

**Description**: Applies Self-Improvement Protocol to update knowledge files based on feedback.

---

## Detection Triggers

Activate when user says:
- "Hook is too weak"
- "Sounds too marketing-y"
- "That's not how PHOs work"
- "Don't mention [X] in posts"
- "Comments are too long"
- Any corrective feedback during review

---

## Protocol

### 1. Identify Feedback Tier

Map feedback to knowledge file using table from AGENTS.md:

| Feedback Type | Target File |
|--------------|-------------|
| Voice/tone | `knowledge/voice_profile.md` |
| Post structure | `knowledge/voice_profile.md` + `algorithm_sop.md` |
| Content pillar | `knowledge/clinicpro_strategy.md` |
| Algorithm rules | `knowledge/algorithm_sop.md` |
| NZ health facts | `knowledge/nz_health_context.md` |
| Agent behavior | Relevant file in `/agents/` |
| Playwright/tools | Relevant file in `/tools/` |
| Dehallucination | `knowledge/dehallucination_triggers.md` |

### 2. Derive Specific Rule

Transform feedback into testable constraint:

**Weak**: "Be more specific"  
**Strong**: "Hook must open with named NZ clinical system or workflow step (e.g. 'Medtech Cloud', 'HealthLink referral') - never with rhetorical question or statistic without context"

### 3. Update File

1. Announce in chat BEFORE updating:
   ```
   Updating knowledge/voice_profile.md: Adding rule that hooks must open with specific clinical observation. Applying now.
   ```
2. Append rule to appropriate section in file
3. If updating agent file, also update AGENTS.md if behavior changes
4. Do NOT ask for approval (follow AGENTS.md protocol)

### 4. Apply to Current Session

If still in drafting phase, re-run Architect with updated rule.

---

## Strategic Changes

If proposed update would:
- Alter public positioning
- Contradict existing pillar
- Remove constraint (not add)

Then: Flag in chat, wait for approval before updating.

---

## Examples

**Feedback**: "Hook is too generic"  
**Action**: Update `voice_profile.md` with specific hook requirements, announce, re-run Architect

**Feedback**: "That PHO structure is wrong"  
**Action**: Update `nz_health_context.md` with correct info, announce, continue

**Feedback**: "Don't mention user numbers in Building in Public posts"  
**Action**: Flag as strategic change, wait for approval

---

## Success Criteria

- Feedback correctly mapped to file
- Rule is specific and testable
- Update announced before applied
- User sees immediate effect in next draft
- System doesn't repeat same mistake
```

---

## Part 4: Update AGENTS.md

Restructure AGENTS.md to be lighter (move orchestration to skills):

**Keep in AGENTS.md**:
- High-level architecture (WAT framework)
- State schema
- Agent descriptions (what each does, not how Cursor orchestrates)
- Self-Improvement Protocol
- LinkedIn auth protocol
- Failure/recovery protocols
- Code style conventions

**Move to Skills**:
- Detailed workflow orchestration steps
- Review loop protocol
- Scheduling implementation
- Error handling in orchestration layer

**Add to AGENTS.md**:
```markdown
## Chat-Based Orchestration (New)

This system is designed for Cursor IDE orchestration via chat. Cursor uses Skills to manage workflows:

- **linkedin-post-create**: Full post creation from topic to scheduled execution
- **linkedin-post-execute**: Golden Hour posting execution
- **linkedin-agent-improve**: Self-improvement based on feedback

See `/mnt/skills/user/linkedin-*/SKILL.md` for orchestration protocols.

### Architecture: 2-Script Design

**prepare_post.py**: Research → Draft → EXIT (writes review marker to `/temporary/`)  
**execute_post.py**: Scheduled execution via OS task

Cursor detects completion via marker files and orchestrates review loop in chat.

### Temporary Folder Contracts

`/temporary/review_ready.json`: Signals draft ready for review  
`/temporary/approved.json`: Signals user approved  
`/temporary/pending_posts.json`: Scheduled posts queue

See Skills for full protocol.
```

---

## Implementation Checklist

**Phase 1 - Agent Updates** (original plan):
- [ ] Add `scrape_personal_feed()` and `scrape_hashtag_posts()` to `tools/browser.py`
- [ ] Update `agents/researcher.py` system prompt with pillar rules
- [ ] Rewrite `agents/scout.py` (personal feed + hashtags, no comments)
- [ ] Update `agents/architect.py` (add comment drafting, parse `<COMMENTS>`)
- [ ] Update `agents/strategist.py` (validate comment count)
- [ ] Update `tests/test_agents.py` (6 mock targets, assert 6 comments)
- [ ] Run `python scripts/run_tests.py` and fix failures

**Phase 2 - Orchestration Architecture**:
- [ ] Create `/temporary/` folder
- [ ] Create `prepare_post.py` (exits at review, writes marker)
- [ ] Create `execute_post.py` (scheduled execution)
- [ ] Create `tools/scheduler.py` (OS scheduling helper)
- [ ] Update `graph/workflow.py` (add `get_compiled_graph_prepare()` and `executor_run()`)

**Phase 3 - Skills**:
- [ ] Create `/mnt/skills/user/linkedin-post-create/SKILL.md`
- [ ] Create `/mnt/skills/user/linkedin-post-execute/SKILL.md`
- [ ] Create `/mnt/skills/user/linkedin-agent-improve/SKILL.md`

**Phase 4 - Documentation**:
- [ ] Update AGENTS.md (add orchestration section, move details to skills)
- [ ] Test full workflow in Cursor chat
- [ ] Update agentic-workflow-report.md if needed

---

## Testing Instructions

1. **Test agent updates**: `python scripts/run_tests.py` (Phases 4, 5, 5b must pass)
2. **Test orchestration**: In Cursor chat, say "Create a post about Medtech ALEX"
3. **Verify Cursor**:
   - Asks 2-3 pre-flight questions
   - Runs `prepare_post.py` in background
   - Detects completion, shows formatted review
   - Handles approval, creates OS scheduled task
   - Confirms scheduling in chat
4. **Manual execution test**: `python execute_post.py [session_id]` (verify posting works)

---

This handoff integrates both the original agent improvements and the new chat-based orchestration architecture. Implement in order: agents first, then orchestration, then skills, then docs.