---
name: git-merge-to-main-and-push
description: Checkout main, merge the branch the user started from (current branch at invocation), then push. Use when the user wants to merge their branch into main and push, checkout main then merge then push, or finish a feature by merging to main.
---

# Git merge to main and push

## When to use

Apply when the user asks to:
- Checkout main, merge their branch, then push
- Merge the branch they started with into main and push
- Merge current branch to main and push

**Prerequisite:** User must be on the branch they want to merge (the "branch I started with") when they run this. The skill uses the current branch at invocation as the branch to merge.

## Workflow

1. **Capture current branch** (the branch to merge)
   ```bash
   git branch --show-current
   ```
   Store this name; e.g. `FEATURE_BRANCH`.

2. **Checkout main**
   ```bash
   git checkout main
   ```

3. **Merge the branch**
   ```bash
   git merge FEATURE_BRANCH
   ```
   If merge conflicts occur, report them and stop; let the user resolve before pushing.

4. **Push**
   ```bash
   git push
   ```
   If the repo uses an upstream like `origin main`, use `git push origin main` when needed.

## If user names a different branch

If the user says "merge branch X into main" (not "the branch I started with"), use that branch name instead of the current branch in step 3. Still checkout main first, then merge X, then push.
