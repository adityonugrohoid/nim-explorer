# NIM Explorer

## Overview
Python toolkit + static HTML explorer for Nvidia NIM LLM models. Catalog 107+ models with metadata, probe capabilities (tool calling, JSON mode, thinking), benchmark and compare.

## Tech Stack
- Python 3.12+ (scripts, probing)
- httpx (async HTTP client)
- rich (terminal output)
- Vanilla HTML/CSS/JS (model browser, no build step)
- python-dotenv (.env management)

## Architecture
```
scripts/build_catalog.py  →  Probe NIM API  →  models/catalog.json
                                                      ↓
                                              docs/index.html (loads JSON)
```

## Key Files
- `models/catalog.json` — Machine-readable model catalog (generated)
- `docs/index.html` — HTML model browser
- `docs/api-reference.md` — Complete NIM API documentation
- `scripts/build_catalog.py` — Probe all models, build catalog
- `scripts/probe_model.py` — Probe single model for detailed info

## Commands
```bash
source .venv/bin/activate

# Build/refresh the catalog
python scripts/build_catalog.py

# Probe a single model
python scripts/probe_model.py meta/llama-3.3-70b-instruct
```

## API Details
- Base URL: `https://integrate.api.nvidia.com/v1`
- Auth: `Authorization: Bearer $NVIDIA_API_KEY`
- Rate limit: 40 RPM (free tier)
- Endpoints: `/v1/models` (GET), `/v1/chat/completions` (POST)

## Key Patterns
- All API calls use httpx async client with timeout handling
- Rate limiting: 1.5s delay between requests (stays under 40 RPM)
- Probe results saved to `results/raw/` for debugging
- `catalog.json` is committed — it's the primary artifact
- HTML browser loads catalog.json via fetch, no build step

## Important Notes
- 187 models listed by API, only ~107 callable on free tier
- Tool calling support varies — must be probed per model
- Response shapes differ by backend (vLLM vs TensorRT-LLM)
- Some models timeout at 20s, need 60s+ (large MoE models)
