# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A FastAPI web application that processes Excel files to generate personalized PDF/HTML vouchers, with integration to SharePoint via Microsoft Graph API. Supports multiple clients (GlobalEvents, Mastercard, Banco Guayaquil), languages (es/en/pt), and branding profiles.

## Development Commands

```bash
# Run dev server (with auto-reload)
python run.py
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_validator.py -v

# Build Docker image
docker build -t voucher-generator .
docker run -p 8080:8080 --env-file .env voucher-generator
```

## Architecture Overview

### Request Lifecycle

1. Browser SPA (served from `app/templates/index.html`) calls `/api/sharepoint/run` or `/api/local/run`
2. A background thread runs the pipeline steps, writing intermediate files under `work/jobs/{job_id}/`
3. Frontend polls `/api/jobs/{job_id}` for real-time progress
4. Final artifacts are zipped and downloadable via `/api/download-zip/{job_id}`

### Pipeline Steps (in `app/pipeline_runner.py`)

| Step | Module | Output |
|------|--------|--------|
| Parse Excel | `voucher_generator/xlsx_to_voucher_json.py` | `payloads.json` |
| Enrich hotels | `voucher_generator/enrich_hotels.py` | `enriched.json` (calls Google Places API) |
| Render HTML | `voucher_generator/render_vouchers_html.py` | `vouchers/*.html` |
| Render PDF | `voucher_generator/render_vouchers_pdf.py` | `vouchers/*.pdf` (Playwright/Chromium) |

Row-level validation errors do not abort the pipeline — they are captured and included in warnings output.

### Key Files

- `app/main.py` — Core FastAPI app: route definitions, `JOB_STORE` (in-memory + disk), background job orchestration
- `app/services/sharepoint_graph.py` — Microsoft Graph API client (download/upload files, browse folders)
- `app/client_registry.py` — Maps client names to profile and site configuration
- `voucher_generator/profile_catalog.py` — Dynamically loads profile configs from `voucher_generator/config/profiles/*.json`
- `app/config.py` — Pydantic settings; reads `.env`

### Multi-Site / Multi-Client Configuration

Sites are defined in the `SHAREPOINT_SITES_JSON` environment variable. Each site carries: SharePoint library name, default folder path, default profile, and branding overrides. The profile system (`voucher_generator/profiles/`) handles template selection and language. New clients require entries in both `SHAREPOINT_SITES_JSON` and `app/client_registry.py`.

### Authentication

OAuth 2.0 via Azure AD (MSAL). Tokens are stored per-user email in `app/token_store.py` (simple file-based). All SharePoint API calls validate the token before use. The fake SharePoint implementation (`app/services/sharepoint_fake.py`) can be swapped in for local testing without Graph API credentials.

### Job State

`JOB_STORE` is an in-memory dict keyed by `job_id`. State is also persisted to `BASE_JOB_STATE_DIR` (temp directory) so jobs survive restarts. A monitoring thread tracks generated files in real time and updates progress percentage.

### Frontend

Single Page Application in `app/templates/index.html`. JavaScript is modularized across `app/static/js/`. Polls job status API for live progress. No build step — plain JS served statically.

## Environment Variables (`.env`)

| Variable | Purpose |
|----------|---------|
| `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID` | Azure AD OAuth credentials |
| `MS_REDIRECT_URI` | OAuth callback (`http://localhost:8000/auth/callback`) |
| `SHAREPOINT_HOSTNAME` | e.g. `patagonik.sharepoint.com` |
| `SHAREPOINT_SITES_JSON` | JSON array of site configs with profiles and branding |
| `GOOGLE_PLACES_API_KEY` | Hotel enrichment (coordinates, images) |
| `BRAND_LOGO` | Default branding asset |
