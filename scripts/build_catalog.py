"""Build the NIM model catalog by probing all models on the live API.

Probes every model listed by /v1/models with a minimal chat request,
records availability and response shape, outputs models/catalog.json.

Usage:
    cd ~/projects/nim-explorer
    source .venv/bin/activate
    python scripts/build_catalog.py
    python scripts/build_catalog.py --timeout 60   # longer timeout for slow models
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_KEY = os.environ["NVIDIA_API_KEY"]
BASE_URL = "https://integrate.api.nvidia.com/v1"
DELAY_BETWEEN_REQUESTS = 1.5  # 40 RPM safe

console = Console()


def infer_metadata(model_id: str) -> dict[str, Any]:
    """Infer family, organization, and tags from model ID."""
    org, name = model_id.split("/", 1) if "/" in model_id else ("unknown", model_id)
    lower = name.lower()

    family = "other"
    family_map = {
        "llama": "llama", "gemma": "gemma", "mistral": "mistral", "mixtral": "mistral",
        "phi-": "phi", "qwen": "qwen", "deepseek": "deepseek", "nemotron": "nemotron",
        "jamba": "jamba", "solar": "solar", "glm": "glm", "granite": "granite",
        "falcon": "falcon", "starcoder": "starcoder", "codestral": "mistral",
        "kimi": "kimi", "minimax": "minimax", "gpt-oss": "gpt-oss", "bielik": "bielik",
    }
    for keyword, fam in family_map.items():
        if keyword in lower:
            family = fam
            break

    tags: list[str] = [family]
    if any(kw in lower for kw in ("r1", "qwq", "reasoning", "thinking")):
        tags.append("thinking")
    if any(kw in lower for kw in ("coder", "codestral", "starcoder", "devstral")):
        tags.append("coding")
    if any(kw in lower for kw in ("vision", "multimodal", "vl-", "-vl")):
        tags.append("vision")
    if any(kw in lower for kw in ("guard", "safety", "shield")):
        tags.append("safety")
    if "instruct" in lower or "chat" in lower or "-it" in lower:
        tags.append("instruct")
    if any(kw in lower for kw in ("embed", "retriever")):
        tags.append("embedding")

    return {"organization": org, "family": family, "tags": sorted(set(tags))}


async def fetch_model_list(client: httpx.AsyncClient) -> list[str]:
    """Get all model IDs from /v1/models."""
    resp = await client.get(
        f"{BASE_URL}/models",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return sorted(set(m["id"] for m in data["data"]))


async def probe_model(
    client: httpx.AsyncClient,
    model_id: str,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Probe a single model with a minimal chat request."""
    try:
        resp = await client.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            },
            timeout=timeout,
        )

        status = resp.status_code
        try:
            body = resp.json()
        except Exception:
            body = {"_raw_text": resp.text[:500]}

        if status == 200 and isinstance(body, dict) and "choices" in body:
            # Extract response shape info
            msg = body.get("choices", [{}])[0].get("message", {})
            usage = body.get("usage", {})

            response_fields = sorted(body.keys())
            message_fields = sorted(msg.keys())
            usage_fields = sorted(usage.keys())

            return {
                "status": "available",
                "http": 200,
                "response_fields": response_fields,
                "message_fields": message_fields,
                "usage_fields": usage_fields,
                "finish_reason": body.get("choices", [{}])[0].get("finish_reason"),
                "has_reasoning_content": msg.get("reasoning_content") is not None,
                "has_tool_calls_field": "tool_calls" in msg,
            }
        elif status == 404:
            return {"status": "not_found", "http": 404}
        elif status == 400:
            err = body.get("error", body) if isinstance(body, dict) else str(body)
            detail = err.get("message", str(err))[:200] if isinstance(err, dict) else str(err)[:200]
            return {"status": "error_400", "http": 400, "detail": detail}
        elif status == 500:
            return {"status": "server_error", "http": 500}
        else:
            return {"status": f"http_{status}", "http": status}

    except httpx.TimeoutException:
        return {"status": "timeout", "http": None}
    except Exception as e:
        return {"status": "exception", "http": None, "detail": str(e)[:200]}


def build_catalog_entry(model_id: str, probe: dict[str, Any]) -> dict[str, Any]:
    """Build a catalog entry from model ID and probe result."""
    meta = infer_metadata(model_id)
    entry: dict[str, Any] = {
        "id": model_id,
        "organization": meta["organization"],
        "family": meta["family"],
        "tags": meta["tags"],
        "status": probe["status"],
    }

    if probe["status"] == "available":
        entry["response_fields"] = probe.get("response_fields", [])
        entry["message_fields"] = probe.get("message_fields", [])
        entry["usage_fields"] = probe.get("usage_fields", [])
        entry["has_reasoning_content"] = probe.get("has_reasoning_content", False)
        entry["has_tool_calls_field"] = probe.get("has_tool_calls_field", False)

    return entry


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build NIM model catalog")
    parser.add_argument("--timeout", type=float, default=20.0, help="Request timeout in seconds (default: 20)")
    args = parser.parse_args()

    console.rule("[bold cyan]NIM Explorer -- Building Model Catalog[/]")
    console.print()

    async with httpx.AsyncClient() as client:
        # Fetch model list
        console.print("[bold]Fetching model list...[/] ", end="")
        all_models = await fetch_model_list(client)
        console.print(f"[green]{len(all_models)} models[/]")
        console.print(f"[dim]Timeout: {args.timeout}s, delay: {DELAY_BETWEEN_REQUESTS}s[/]")
        est_min = len(all_models) * DELAY_BETWEEN_REQUESTS / 60
        console.print(f"[dim]Estimated time: ~{est_min:.0f} min[/]")
        console.print()

        # Probe each model
        probes: dict[str, dict[str, Any]] = {}
        counts = {"available": 0, "not_found": 0, "timeout": 0, "error": 0}

        for i, model_id in enumerate(all_models):
            probe = await probe_model(client, model_id, timeout=args.timeout)
            probes[model_id] = probe

            marker = {"available": "[green]OK[/]", "not_found": "[dim]404[/]", "timeout": "[yellow]TIMEOUT[/]"}
            status_str = marker.get(probe["status"], f"[red]{probe['status']}[/]")

            short = model_id.split("/")[-1][:45]
            console.print(f"  [{i+1:3d}/{len(all_models)}] {short:<47s} {status_str}")

            if probe["status"] == "available":
                counts["available"] += 1
            elif probe["status"] == "not_found":
                counts["not_found"] += 1
            elif probe["status"] == "timeout":
                counts["timeout"] += 1
            else:
                counts["error"] += 1

            await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

    # Build catalog
    catalog_entries = []
    for model_id in all_models:
        entry = build_catalog_entry(model_id, probes[model_id])
        catalog_entries.append(entry)

    catalog = {
        "metadata": {
            "provider": "nvidia-nim",
            "base_url": BASE_URL,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total_listed": len(all_models),
            "total_available": counts["available"],
            "total_timeout": counts["timeout"],
            "probe_timeout_seconds": args.timeout,
        },
        "models": catalog_entries,
    }

    # Write catalog
    catalog_path = ROOT / "models" / "catalog.json"
    with open(catalog_path, "w") as f:
        json.dump(catalog, f, indent=2)

    # Write raw probe results
    probe_path = ROOT / "results" / f"probe-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    with open(probe_path, "w") as f:
        json.dump(probes, f, indent=2)

    # Summary
    console.print()
    console.rule("[bold cyan]Summary[/]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")
    table.add_row("[green]Available[/]", str(counts["available"]))
    table.add_row("[dim]Not Found[/]", str(counts["not_found"]))
    table.add_row("[yellow]Timeout[/]", str(counts["timeout"]))
    table.add_row("[red]Error[/]", str(counts["error"]))
    table.add_row("[bold]Total[/]", f"[bold]{len(all_models)}[/]")
    console.print(table)

    console.print()
    console.print(f"  Catalog: [green]{catalog_path}[/]")
    console.print(f"  Raw:     [dim]{probe_path}[/]")
    console.print()


if __name__ == "__main__":
    asyncio.run(main())
