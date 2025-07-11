#!/usr/bin/env python3
"""CLI tool for testing MiniVault API."""
import asyncio
import json

import click
import httpx
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

console = Console()


@click.group()
def cli():
    """MiniVault API CLI - Test your local AI API."""
    pass


@cli.command()
@click.option("--prompt", "-p", default="Hello, MiniVault!", help="Prompt to send")
@click.option("--url", "-u", default="http://localhost:8000", help="API URL")
@click.option(
    "--preset", help="Preset to use (creative, balanced, precise, deterministic, code)"
)
@click.option("--model", help="Model to use for generation")
@click.option("--temperature", type=float, help="Sampling temperature (0.0-2.0)")
@click.option("--top-p", "top_p", type=float, help="Top-p sampling (0.0-1.0)")
@click.option("--max-tokens", type=int, help="Maximum tokens to generate")
@click.option("--system", help="System prompt")
def generate(
    prompt: str,
    url: str,
    preset: str,
    model: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    system: str,
):
    """Send a prompt and get a response."""
    with console.status("[bold green]Sending request..."):
        try:
            # Build request payload
            payload = {"prompt": prompt}
            if preset:
                payload["preset"] = preset
            if model:
                payload["model"] = model
            if temperature is not None:
                payload["temperature"] = temperature
            if top_p is not None:
                payload["top_p"] = top_p
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            if system:
                payload["system"] = system

            response = httpx.post(f"{url}/generate", json=payload)
            response.raise_for_status()
            data = response.json()

            console.print("\n[bold cyan]Prompt:[/bold cyan]", prompt)
            console.print("[bold green]Response:[/bold green]", data["response"])

            # Show usage information
            if "usage" in data:
                usage = data["usage"]
                console.print(
                    f"[dim]Usage: {usage['prompt_tokens']} prompt + {usage['completion_tokens']} completion = {usage['total_tokens']} total tokens[/dim]"
                )
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


@cli.command()
@click.option("--prompt", "-p", default="Hello, MiniVault!", help="Prompt to send")
@click.option("--url", "-u", default="http://localhost:8000", help="API URL")
@click.option(
    "--preset", help="Preset to use (creative, balanced, precise, deterministic, code)"
)
@click.option("--model", help="Model to use for generation")
@click.option("--temperature", type=float, help="Sampling temperature (0.0-2.0)")
@click.option("--top-p", "top_p", type=float, help="Top-p sampling (0.0-1.0)")
@click.option("--max-tokens", type=int, help="Maximum tokens to generate")
@click.option("--system", help="System prompt")
def stream(
    prompt: str,
    url: str,
    preset: str,
    model: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    system: str,
):
    """Stream response tokens using SSE."""

    async def stream_tokens():
        # Set timeout for streaming requests
        timeout = httpx.Timeout(30.0, read=60.0)  # 30s connection, 60s read
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                console.print(f"\n[bold cyan]Prompt:[/bold cyan] {prompt}")
                console.print("[bold green]Response:[/bold green] ", end="")

                # Build request payload
                payload = {"prompt": prompt, "stream": True}
                if preset:
                    payload["preset"] = preset
                if model:
                    payload["model"] = model
                if temperature is not None:
                    payload["temperature"] = temperature
                if top_p is not None:
                    payload["top_p"] = top_p
                if max_tokens is not None:
                    payload["max_tokens"] = max_tokens
                if system:
                    payload["system"] = system

                usage_info = None
                first_token = True
                async with client.stream(
                    "POST", f"{url}/generate", json=payload
                ) as response:
                    # Check HTTP status before processing
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise httpx.HTTPStatusError(
                            f"HTTP {response.status_code}", 
                            request=response.request, 
                            response=response
                        )
                    
                    # Process streaming response
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str == "[DONE]":
                                break
                            try:
                                token_data = json.loads(data_str)
                                token = token_data["token"]
                                
                                # Strip leading whitespace from first token to avoid blank line
                                if first_token:
                                    token = token.lstrip()
                                    first_token = False
                                
                                console.print(token, end="")
                                if token_data.get("usage"):
                                    usage_info = token_data["usage"]
                            except json.JSONDecodeError:
                                # Skip malformed JSON lines
                                continue

                console.print("\n")
                if usage_info:
                    console.print(
                        f"[dim]Usage: {usage_info['prompt_tokens']} prompt + {usage_info['completion_tokens']} completion = {usage_info['total_tokens']} total tokens[/dim]"
                    )
            except httpx.HTTPStatusError as e:
                console.print(f"\n[bold red]HTTP Error:[/bold red] {e}")
            except httpx.TimeoutException:
                console.print(f"\n[bold red]Timeout Error:[/bold red] Request timed out")
            except httpx.RequestError as e:
                console.print(f"\n[bold red]Connection Error:[/bold red] {e}")
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] {e}")

    asyncio.run(stream_tokens())


@cli.command()
@click.option("--url", "-u", default="http://localhost:8000", help="API URL")
def health(url: str):
    """Check API health status."""
    try:
        response = httpx.get(f"{url}/health")
        response.raise_for_status()
        data = response.json()

        table = Table(title="MiniVault API Health Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", data["status"])
        table.add_row("Version", data["version"])
        table.add_row("Uptime", f"{data['uptime_seconds']:.1f} seconds")
        table.add_row("Total Requests", str(data["total_requests"]))

        # Show LLM status if available
        if "llm_status" in data and data["llm_status"]:
            llm_status = data["llm_status"]
            status_emoji = "✅" if llm_status["status"] == "healthy" else "❌"
            table.add_row("LLM Status", f"{status_emoji} {llm_status['status']}")
            if "models" in llm_status:
                model_count = len(llm_status["models"])
                table.add_row("Available Models", str(model_count))
        else:
            table.add_row("LLM Status", "❌ Not available")

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@cli.command()
@click.option("--url", "-u", default="http://localhost:8000", help="API URL")
def presets(url: str):
    """List available preset configurations."""
    try:
        response = httpx.get(f"{url}/presets")
        response.raise_for_status()
        data = response.json()

        table = Table(title="Available Presets")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Temperature", style="green")
        table.add_column("Top-p", style="green")
        table.add_column("Max Tokens", style="green")

        for preset in data["presets"]:
            name = preset["name"]
            if name == data["default"]:
                name += " (default)"
            table.add_row(
                name,
                preset["description"],
                str(preset["temperature"]),
                str(preset["top_p"]),
                str(preset["max_tokens"]),
            )

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@cli.command()
@click.option("--url", "-u", default="http://localhost:8000", help="API URL")
def models(url: str):
    """List available models."""
    try:
        response = httpx.get(f"{url}/models")
        response.raise_for_status()
        data = response.json()

        if not data["models"]:
            console.print("[yellow]No models available[/yellow]")
            return

        table = Table(title="Available Models")
        table.add_column("Name", style="cyan")
        table.add_column("Size", style="green")
        table.add_column("Modified", style="dim")

        for model in data["models"]:
            size = model.get("size", "Unknown")
            modified = model.get("modified", "Unknown")
            if modified != "Unknown" and modified is not None:
                # Format datetime if available
                modified = modified.split("T")[0]  # Just show date

            table.add_row(model["name"], str(size), str(modified))

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@cli.command()
@click.option("--count", "-c", default=10, help="Number of requests to send")
@click.option("--url", "-u", default="http://localhost:8000", help="API URL")
@click.option(
    "--preset", help="Preset to test (creative, balanced, precise, deterministic, code)"
)
@click.option("--model", help="Model to test")
@click.option("--prompt", default="Benchmark test", help="Prompt to use for testing")
def benchmark(count: int, url: str, preset: str, model: str, prompt: str):
    """Run a benchmark with optional preset and model testing."""
    preset_info = f" with preset '{preset}'" if preset else ""
    model_info = f" and model '{model}'" if model else ""
    console.print(
        f"\n[bold]Running benchmark with {count} requests{preset_info}{model_info}...[/bold]"
    )

    times = []
    errors = 0
    total_tokens = 0

    with console.status("[bold green]Benchmarking...") as status:
        for i in range(count):
            status.update(f"Request {i+1}/{count}")
            try:
                # Build request payload
                payload = {"prompt": f"{prompt} {i}"}
                if preset:
                    payload["preset"] = preset
                if model:
                    payload["model"] = model

                import time

                start_time = time.perf_counter()
                response = httpx.post(f"{url}/generate", json=payload)
                end_time = time.perf_counter()

                response.raise_for_status()
                data = response.json()

                request_time = (end_time - start_time) * 1000  # Convert to ms
                times.append(request_time)

                if "usage" in data:
                    total_tokens += data["usage"]["total_tokens"]

            except Exception as e:
                errors += 1

    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        table = Table(title="Benchmark Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Requests", str(count))
        table.add_row("Successful", str(len(times)))
        table.add_row("Errors", str(errors))
        table.add_row("Success Rate", f"{len(times)/count*100:.1f}%")
        table.add_row("Average Time", f"{avg_time:.1f}ms")
        table.add_row("Min Time", f"{min_time:.1f}ms")
        table.add_row("Max Time", f"{max_time:.1f}ms")
        if total_tokens > 0:
            table.add_row("Total Tokens", str(total_tokens))
            table.add_row("Avg Tokens/Request", f"{total_tokens/len(times):.1f}")

        console.print(table)
    else:
        console.print("[bold red]All requests failed![/bold red]")


@cli.command()
@click.option(
    "--prompt",
    "-p",
    default="Write a short story about AI",
    help="Prompt to test with all presets",
)
@click.option("--url", "-u", default="http://localhost:8000", help="API URL")
def compare_presets(prompt: str, url: str):
    """Compare responses across all available presets."""
    console.print(
        f"\n[bold]Comparing presets with prompt: [cyan]'{prompt}'[/cyan][/bold]"
    )

    # First get available presets
    try:
        response = httpx.get(f"{url}/presets")
        response.raise_for_status()
        presets_data = response.json()
        presets = [p["name"] for p in presets_data["presets"]]
    except Exception as e:
        console.print(f"[bold red]Error getting presets:[/bold red] {e}")
        return

    results = {}

    # Test each preset
    with console.status("[bold green]Testing presets...") as status:
        for i, preset in enumerate(presets):
            status.update(f"Testing {preset} ({i+1}/{len(presets)})")
            try:
                import time

                start_time = time.perf_counter()
                response = httpx.post(
                    f"{url}/generate", json={"prompt": prompt, "preset": preset}
                )
                end_time = time.perf_counter()
                response.raise_for_status()
                data = response.json()

                results[preset] = {
                    "response": data["response"],
                    "tokens": data["usage"]["total_tokens"],
                    "time_ms": (end_time - start_time) * 1000,
                }
            except Exception as e:
                results[preset] = {"error": str(e)}

    # Display results
    for preset, result in results.items():
        console.print(f"\n[bold cyan]═══ {preset.upper()} ═══[/bold cyan]")
        if "error" in result:
            console.print(f"[bold red]Error:[/bold red] {result['error']}")
        else:
            console.print(
                f"[dim]Tokens: {result['tokens']} | Time: {result['time_ms']:.1f}ms[/dim]"
            )
            console.print(result["response"])

    console.print("\n[dim]Comparison complete![/dim]")


if __name__ == "__main__":
    cli()
