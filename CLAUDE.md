# CLAUDE.md — VeilRender

## What this project is

Headless browser rendering API. Accepts a URL, renders it with Playwright +
Chromium, returns HTML/Markdown/readability content. Primary deployment target:
HF Spaces (free tier). Also runs as standalone Docker container.

## Architecture

- **Zero external deps** except `playwright` — uses vendored `zerodep` modules
  in `src/veilrender/_vendor/` for HTTP server, HTML parsing, readability, etc.
- **`httpserver`** (zerodep) as the async HTTP framework — not FastAPI
- **Playwright** for browser control — shared browser instance, per-request
  `BrowserContext` isolation
- **Stateless** — no session management, no database

## Repository layout

```
src/veilrender/
├── app.py          # HTTP server setup, route registration, main()
├── config.py       # Settings from env vars (VEILRENDER_ prefix)
├── auth.py         # Token verification
├── browser.py      # Playwright browser lifecycle
├── models.py       # Request/response dataclasses
├── routes/         # Route handlers (render, screenshot, health)
└── _vendor/        # zerodep modules — DO NOT EDIT manually
```

## Commands

```bash
make dev          # Run dev server on :7860
make build        # Docker build
make run          # Docker run
make lint         # ruff check --fix && ruff format
make typecheck    # ty check
make vendor       # Re-vendor zerodep modules
```

## Files to never edit

- `src/veilrender/_vendor/**` — vendored zerodep modules, update via
  `zerodep update` from ~/projects/zerodep

## Definition of done

1. `ruff check --fix && ruff format` on changed Python files
2. Server starts and `/health` returns 200
3. `/render` returns valid content for a test URL
