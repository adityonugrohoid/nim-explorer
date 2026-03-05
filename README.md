<div align="center">

# NIM Explorer

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Models](https://img.shields.io/badge/models-107%20available-green.svg)](#model-catalog)

**Machine-readable catalog of 107 Nvidia NIM LLM models with capability detection and an HTML browser.**

[Getting Started](#getting-started) | [Model Catalog](#model-catalog) | [API Reference](#api-reference) | [Scripts](#scripts)

</div>

---

## Features

- **Model Catalog** -- JSON catalog of all 107 available NIM models with metadata (family, params, capabilities, quirks)
- **HTML Browser** -- Static page to filter, search, and explore models by capability
- **Capability Probing** -- Automated detection of tool calling, JSON mode, thinking support per model
- **API Reference** -- Complete Nvidia NIM endpoint documentation based on live testing

## Getting Started

### Prerequisites

- Python 3.12+
- Nvidia NIM API key ([get one free](https://build.nvidia.com))

### Installation

```bash
git clone https://github.com/adityonugrohoid/nim-explorer.git
cd nim-explorer

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env` with your Nvidia API key:

```bash
NVIDIA_API_KEY=nvapi-...
```

## Model Catalog

The catalog (`models/catalog.json`) contains metadata for every callable model on Nvidia NIM's free tier.

### By Organization

| Organization | Models | Highlights |
|-------------|--------|-----------|
| meta | 11 | Llama 3.x/4, vision, guard |
| nvidia | 16 | Nemotron (thinking + tools), safety, translation |
| mistralai | 13 | Mistral/Mixtral, Codestral, Mathstral |
| microsoft | 11 | Phi 3/3.5/4, reasoning, vision |
| google | 10 | Gemma 2/3/3n, ShieldGemma |
| qwen | 9 | Qwen 2/2.5/3/3.5, QwQ, coding |
| deepseek-ai | 5 | R1-distill (thinking), V3.x |
| 20+ others | 32 | Regional, specialized, emerging |

### Refreshing the Catalog

```bash
# Probe all models and rebuild catalog.json
python scripts/build_catalog.py
```

## API Reference

See [`docs/api-reference.md`](docs/api-reference.md) for complete Nvidia NIM endpoint documentation including:

- All request parameters with types, defaults, and ranges
- Response shape variations by model backend
- Tool calling format and supported models
- Thinking/reasoning patterns (3 different approaches)
- Streaming SSE format
- Error response inconsistencies

## Scripts

```bash
# Build the full model catalog
python scripts/build_catalog.py

# Probe a single model for detailed info
python scripts/probe_model.py meta/llama-3.3-70b-instruct
```

## Project Structure

```
nim-explorer/
├── models/
│   └── catalog.json            # Machine-readable model catalog
├── docs/
│   ├── index.html              # HTML model browser
│   └── api-reference.md        # Complete NIM API documentation
├── scripts/
│   ├── build_catalog.py        # Probe all models, build catalog
│   └── probe_model.py          # Probe single model
├── results/
│   └── raw/                    # Raw API responses (gitignored)
├── CLAUDE.md
├── README.md
├── ROADMAP.md
├── requirements.txt
└── .env.example
```

## Roadmap

- [ ] v0.1: Model catalog + HTML browser + API reference
- [ ] v0.2: Tool calling / JSON mode / thinking probes + benchmarks
- [ ] v0.3: Arena integration (multi-model comparison app)

## License

This project is licensed under the [MIT License](LICENSE).

## Author

**Adityo Nugroho** ([@adityonugrohoid](https://github.com/adityonugrohoid))
</div>
