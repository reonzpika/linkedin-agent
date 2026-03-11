---
name: work-to-completion
description: Instructs the agent to work autonomously until the stated goal is achieved, without stopping early. Use when the user wants the AI to continue without stopping until the goal is done, when working from an AGENTS.md or similar status doc, or when the user says to "keep going" or "don't stop until finished."
---

# Work to Completion

## Core principle

**Do not stop until the goal is achieved.** Work in repeated loops until success criteria are met. If tests fail or something is incomplete, fix it and continue. Only hand back with "here is what's left" if the user explicitly asks for a status update, or the goal is fully done.

## Phase 1: Plan first

Before implementing, create a **plan file** (e.g. `plan.md` or `PLAN.md`) that includes:

- Goal and scope (from user request and/or AGENTS.md, README).
- Ordered steps to achieve the goal (understand, implement, test, install deps as needed).
- How you will verify success (e.g. Playwright tests, acceptance criteria).

**Then stop and hand the plan to the user.** The user executes (approves or runs the next phase). Do not start implementation until the user indicates they want execution (e.g. "go," "execute," "implement").

## Phase 2: Execute

After the user approves or asks to execute, run the development loop until the goal is met. Do not stop with unfinished work unless the user asks for status.

## Development loop

Repeat until the goal is met:

1. **Understand** – Read project docs (e.g. AGENTS.md, EPICS_AND_STORIES, USER_FLOWS, README) and relevant existing code.
2. **Implement** – Write clean, incremental code; one logical change at a time where possible.
3. **Dependencies** – Install any required dependencies to achieve the goal (e.g. `npm install`, `pip install`, adding packages to package.json or requirements.txt). Do this whenever new code or tests need a package.
4. **Test** – Use the **Playwright CLI** (see "Playwright tests" below). Run `npx playwright test` (or a focused run). Respect project config (e.g. `PLAYWRIGHT_BASE_URL` if dev runs on another port). Run the dev server manually first if the project expects it; then run Playwright. Fix failures and re-run.
5. **Self-improve** – If tests fail or the goal is not met: analyse the cause, update the code or approach (fix assertions, selectors, flows, or implementation), then retry. Do not report and stop; adjust and continue until tests pass and the goal is achieved.
6. **Reflect** – If the project keeps a status doc (e.g. AGENTS.md), update current status, learning log, or next-iteration plan. Update the plan file if steps or scope changed.

## Using project context

- **Mission and scope:** Look for AGENTS.md, README, or docs at the repo root. Treat the "Mission" or "Current status" section as the goal and scope.
- **Implemented vs pending:** If the project tracks an "Implemented vs Pending" table or backlog, use it to choose the next work and update it when you complete items.
- **Success criteria:** If the project defines success criteria (e.g. in AGENTS.md), treat them as the definition of done. Keep going until each is satisfied.

## Success criteria (default)

When the project does not define its own, aim for:

- Playwright tests pass (`npx playwright test`).
- Stated goal or acceptance criteria are met.
- No new regressions (e.g. console errors, broken flows).
- Required dependencies are installed and documented (package.json, requirements.txt, etc.).
- Changes are consistent with existing style and docs.

## Playwright tests

Use the Playwright CLI to run and debug tests. Full reference: [Playwright Test CLI](https://playwright.dev/docs/test-cli).

**Run tests:**
- `npx playwright test` — run all tests
- `npx playwright test <path>` — e.g. `npx playwright test e2e/ai-scribe.spec.ts` or `npx playwright test e2e/todo-page/`
- `npx playwright test -g "title or pattern"` — run tests whose title matches the regex

- `npx playwright test --project=chromium` — run only one project
- `npx playwright test --workers=1` — disable parallelisation (useful for flaky or ordering-sensitive tests)

**Debug and inspect:**
- `npx playwright test --debug` — run with Playwright Inspector (headed, single worker, no timeout)
- `npx playwright test --headed` — run in headed browsers
- `npx playwright show-report` — open HTML report from last run

**Other:** `npx playwright test --help` for all options (e.g. `--last-failed`, `--retries`, `--timeout`).

## SQL migrations

When the goal involves schema changes or applying a migration from `database/migrations/`:

1. **Create/update** the migration SQL file in `database/migrations/` and the corresponding schema in `database/schema/` per `database/AGENTS.md`. Never use `drizzle-kit migrate`, `drizzle-kit push`, or `db:push`.
2. **Apply the migration yourself**; do not leave "run this SQL in Neon" as a manual step.
   - **Preferred:** If `DATABASE_URL` is available (e.g. from `.env.local`), run:  
     `pnpm tsx scripts/run-migration.ts <migration-file>.sql`  
     Example: `pnpm tsx scripts/run-migration.ts 0048_openmailer_send_lock.sql`
   - **If `DATABASE_URL` is not set:** Use the Neon CLI (assumed installed and authed). Get a connection string with `neon connection-string` (or `npx neonctl connection-string`), set it as `DATABASE_URL`, then run the script above. On Windows PowerShell:  
     `$env:DATABASE_URL = (neon connection-string); pnpm tsx scripts/run-migration.ts <migration-file>.sql`  
     Alternatively, if `psql` is available:  
     `psql "<connection_string>" -f database/migrations/<migration-file>.sql`
3. If running the migration fails (e.g. missing credentials or Neon context), report the error and what the user must provide (e.g. set `DATABASE_URL` or run the migration in Neon SQL Editor).

Ref: [Neon CLI reference](https://neon.com/docs/reference/neon-cli); project: `database/AGENTS.md`, `database/DRIZZLE-MIGRATIONS-GUIDE.md`, `scripts/run-migration.ts`.

## Persistence rules

- **Plan then execute:** Always produce a plan file first; wait for user to approve or say "execute" before implementing.
- **Fix, don't report:** Encountering a failing test or broken step means fix it and re-run; do not stop and only summarise failures unless the user asked for a status report.
- **Self-improve:** When something fails, change the code or approach and retry; do not hand back with "tests still fail" without having tried to fix.
- **Install what's needed:** If the goal or tests require a dependency, install it (npm, pip, etc.); do not leave "install X" as a manual step for the user.
- **Next step always clear:** After each loop, either the goal is achieved or there is a concrete next action. Take that action in the same session when possible.
- **Update status when relevant:** If the project uses AGENTS.md or similar, update "Current status," "Implemented vs Pending," or "Next iteration" so the next run (or another agent) can continue without re-discovering everything.
