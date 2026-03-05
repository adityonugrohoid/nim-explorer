"""Probe a single NIM model for detailed capability info.

Usage:
    python scripts/probe_model.py meta/llama-3.3-70b-instruct
    python scripts/probe_model.py nvidia/llama-3.1-nemotron-ultra-253b-v1 --timeout 60
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_KEY = os.environ["NVIDIA_API_KEY"]
BASE_URL = "https://integrate.api.nvidia.com/v1"

console = Console(width=120)


async def chat(
    client: httpx.AsyncClient,
    model: str,
    messages: list[dict],
    timeout: float = 30.0,
    **kwargs: Any,
) -> dict[str, Any]:
    """Send a chat completion request, return full response dict."""
    resp = await client.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages, **kwargs},
        timeout=timeout,
    )
    try:
        return {"http": resp.status_code, "body": resp.json()}
    except Exception:
        return {"http": resp.status_code, "body": resp.text[:500]}


async def probe(model_id: str, timeout: float) -> None:
    console.rule(f"[bold cyan]Probing: {model_id}[/]")
    console.print()

    async with httpx.AsyncClient() as client:
        # 1. Basic chat
        console.print("[bold]1. Basic Chat[/]")
        result = await chat(client, model_id, [{"role": "user", "content": "Say hello in one word."}], timeout=timeout, max_tokens=10)
        print_result(result)

        if result["http"] != 200:
            console.print("[red]Model not available. Stopping.[/]")
            return

        await asyncio.sleep(1.5)

        # 2. Tool calling
        console.print("[bold]2. Tool Calling[/]")
        tool_result = await chat(
            client, model_id,
            [{"role": "user", "content": "What is the weather in Paris?"}],
            timeout=timeout,
            max_tokens=100,
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }],
            tool_choice="auto",
        )
        print_result(tool_result)

        if tool_result["http"] == 200:
            body = tool_result["body"]
            msg = body.get("choices", [{}])[0].get("message", {})
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                console.print("  [green]Tool calling: SUPPORTED[/]")
            else:
                console.print("  [yellow]Tool calling: model responded in content (no tool_calls)[/]")
        elif isinstance(tool_result["body"], dict) and "error" in tool_result["body"]:
            console.print(f"  [red]Tool calling: NOT SUPPORTED[/]")
        console.print()

        await asyncio.sleep(1.5)

        # 3. JSON mode
        console.print("[bold]3. JSON Mode (response_format)[/]")
        json_result = await chat(
            client, model_id,
            [{"role": "user", "content": "Return JSON with keys: name (string), age (number)."}],
            timeout=timeout,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        print_result(json_result)

        if json_result["http"] == 200:
            content = json_result["body"].get("choices", [{}])[0].get("message", {}).get("content", "")
            try:
                json.loads(content)
                console.print("  [green]JSON mode: SUPPORTED (valid JSON returned)[/]")
            except (json.JSONDecodeError, TypeError):
                console.print("  [yellow]JSON mode: response not valid JSON[/]")
        console.print()

        # Summary
        console.rule("[bold cyan]Summary[/]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Capability")
        table.add_column("Status")

        chat_ok = result["http"] == 200
        table.add_row("Chat", "[green]YES[/]" if chat_ok else "[red]NO[/]")

        tool_ok = (
            tool_result["http"] == 200
            and isinstance(tool_result["body"], dict)
            and tool_result["body"].get("choices", [{}])[0].get("message", {}).get("tool_calls")
        )
        table.add_row("Tool Calling", "[green]YES[/]" if tool_ok else "[red]NO[/]")

        json_ok = json_result["http"] == 200
        table.add_row("JSON Mode", "[green]YES[/]" if json_ok else "[red]NO[/]")

        # Check thinking indicators
        if chat_ok:
            msg = result["body"].get("choices", [{}])[0].get("message", {})
            has_reasoning = msg.get("reasoning_content") is not None and msg.get("reasoning_content") != ""
            content = msg.get("content", "") or ""
            has_think_tags = "<think>" in content
            if has_reasoning:
                table.add_row("Thinking", "[green]YES[/] (reasoning_content field)")
            elif has_think_tags:
                table.add_row("Thinking", "[green]YES[/] (<think> tags)")
            else:
                table.add_row("Thinking", "[dim]NO[/]")

        console.print(table)
        console.print()


def print_result(result: dict[str, Any]) -> None:
    status = result["http"]
    body = result["body"]
    color = "green" if status == 200 else "red"
    console.print(f"  HTTP {status}", style=color)

    if isinstance(body, dict):
        text = json.dumps(body, indent=2)
        if len(text) > 1500:
            text = text[:1500] + "\n  ... (truncated)"
        console.print(Panel(
            Syntax(text, "json", theme="monokai", word_wrap=True),
            border_style="dim",
            width=110,
        ))
    else:
        console.print(f"  {str(body)[:300]}")
    console.print()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Probe a single NIM model")
    parser.add_argument("model", help="Model ID (e.g., meta/llama-3.3-70b-instruct)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout (default: 30s)")
    args = parser.parse_args()

    asyncio.run(probe(args.model, args.timeout))


if __name__ == "__main__":
    main()
