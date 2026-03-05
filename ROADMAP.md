# NIM Explorer -- Roadmap

## v0.1 -- Model Catalog (In Progress)
**Goal:** Build a complete, machine-readable catalog of all Nvidia NIM models with an HTML browser.

- [ ] Probe script: test all models for availability + response shape
- [ ] `models/catalog.json` with metadata per model
- [ ] HTML model browser with filter/search/capability badges
- [ ] API reference documentation
- [ ] README, CLAUDE.md, ROADMAP

## v0.2 -- Capability Detection + Benchmark
- [ ] Tool calling probe per model
- [ ] JSON mode / structured output probe per model
- [ ] Thinking pattern detection per model
- [ ] Benchmark CLI (TTFT, total time, tokens/sec)
- [ ] Compare CLI (side-by-side responses)
- [ ] Benchmark HTML report with charts

## v0.3 -- Arena Integration
- [ ] Feed catalog into LLM Arena 3D concept
- [ ] Tool calling round-trip testing
- [ ] Structured output validation
