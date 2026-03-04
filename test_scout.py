from tools.browser import get_browser_context, scrape_personal_feed

ctx = get_browser_context()
results = scrape_personal_feed(ctx, max_posts=5)
ctx.close()

print(f'Found {len(results)} posts')
for r in results[:2]:
    print(f"- {r.get('name')}: {r.get('snippet', '')[:50]}...")
