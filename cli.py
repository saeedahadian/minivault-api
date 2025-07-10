#!/usr/bin/env python3
"""CLI tool for testing MiniVault API."""
import json
import asyncio
import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.text import Text

console = Console()


@click.group()
def cli():
    """MiniVault API CLI - Test your local AI API."""
    pass


@cli.command()
@click.option("--prompt", "-p", default="Hello, MiniVault!", help="Prompt to send")
@click.option("--url", "-u", default="http://localhost:8000", help="API URL")
def generate(prompt: str, url: str):
    """Send a prompt and get a response."""
    with console.status("[bold green]Sending request..."):
        try:
            response = httpx.post(f"{url}/generate", json={"prompt": prompt})
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
def stream(prompt: str, url: str):
    """Stream response tokens using SSE."""

    async def stream_tokens():
        async with httpx.AsyncClient() as client:
            try:
                console.print(f"\n[bold cyan]Prompt:[/bold cyan] {prompt}")
                console.print("[bold green]Response:[/bold green] ", end="")

                usage_info = None
                async with client.stream(
                    "POST", f"{url}/generate", json={"prompt": prompt, "stream": True}
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str == "[DONE]":
                                break
                            try:
                                token_data = json.loads(data_str)
                                console.print(token_data["token"], end="")
                                if token_data.get("usage"):
                                    usage_info = token_data["usage"]
                            except json.JSONDecodeError:
                                pass

                console.print("\n")
                if usage_info:
                    console.print(
                        f"[dim]Usage: {usage_info['prompt_tokens']} prompt + {usage_info['completion_tokens']} completion = {usage_info['total_tokens']} total tokens[/dim]"
                    )
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
        table.add_row("AI Assisted", "✅" if data["ai_assisted"] else "❌")

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@cli.command()
@click.option("--count", "-c", default=10, help="Number of requests to send")
@click.option("--url", "-u", default="http://localhost:8000", help="API URL")
def benchmark(count: int, url: str):
    """Run a simple benchmark."""
    console.print(f"\n[bold]Running benchmark with {count} requests...[/bold]")

    times = []
    errors = 0

    with console.status("[bold green]Benchmarking...") as status:
        for i in range(count):
            status.update(f"Request {i+1}/{count}")
            try:
                response = httpx.post(
                    f"{url}/generate", json={"prompt": f"Benchmark request {i}"}
                )
                response.raise_for_status()
                times.append(1)  # Just count successful requests
            except:
                errors += 1

    if times:
        table = Table(title="Benchmark Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Requests", str(count))
        table.add_row("Successful", str(len(times)))
        table.add_row("Errors", str(errors))
        table.add_row("Success Rate", f"{len(times)/count*100:.1f}%")

        console.print(table)
    else:
        console.print("[bold red]All requests failed![/bold red]")


if __name__ == "__main__":
    cli()
