import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel

from local_first_common.cli import (
    dry_run_option,
    resolve_dry_run,
    pipe_option,
    init_config_option,
    provider_option,
    model_option,
)
from local_first_common.tracking import register_tool
from .core import (
    PhotoScalerError,
    scale_image_or_raise,
)

TOOL_NAME = "photo-scaler"
DEFAULTS = {"provider": "ollama", "model": "llama3"}
_TOOL = register_tool(TOOL_NAME)

console = Console(stderr=True)  # Send rich output to stderr
app = typer.Typer(help="Resizes images and saves as optimized JPEG.")


@app.command()
def scale(
    path: Annotated[
        Optional[Path], typer.Argument(help="File or directory to scale")
    ] = None,
    max_dim: Annotated[
        int, typer.Option("--max", help="Maximum dimension (width or height)")
    ] = 1200,
    quality: Annotated[
        int, typer.Option("--quality", help="JPEG quality (1-100)")
    ] = 85,
    suffix: Annotated[
        str,
        typer.Option(
            "--suffix", help="Suffix to add to output filename (e.g. -scaled)"
        ),
    ] = "",
    provider_name: Annotated[str, provider_option()] = "ollama",
    model: Annotated[Optional[str], model_option()] = None,
    dry_run: Annotated[bool, dry_run_option()] = False,
    pipe: Annotated[bool, pipe_option()] = False,
    init_config: Annotated[bool, init_config_option(TOOL_NAME, DEFAULTS)] = False,
):
    """Resize images to a target maximum dimension and save as optimized JPEG."""
    dry_run = resolve_dry_run(dry_run, False)

    files_to_process = []
    if path is None:
        if not sys.stdin.isatty():
            for line in sys.stdin:
                p = Path(line.strip())
                if p.exists():
                    files_to_process.append(p)
        else:
            console.print("[red]Error: No path provided and no stdin detected.[/red]")
            raise typer.Exit(1)
    else:
        if not path.exists():
            console.print(f"[red]Path does not exist: {path}[/red]")
            raise typer.Exit(1)
        if path.is_file():
            files_to_process.append(path)
        elif path.is_dir():
            for ext in (".jpg", ".jpeg", ".png", ".tiff", ".webp"):
                files_to_process.extend(path.glob(f"*{ext}"))
                files_to_process.extend(path.glob(f"*{ext.upper()}"))

    if not files_to_process:
        if not pipe:
            console.print("No images found.")
        return

    if not pipe:
        console.print(
            Panel(
                f"Scaling {len(files_to_process)} images to max {max_dim}px...",
                title="Image Scaler",
                border_style="cyan",
            )
        )

    scaled_count = 0
    for file in files_to_process:
        try:
            result = scale_image_or_raise(
                file,
                max_dim=max_dim,
                quality=quality,
                suffix=suffix,
                dry_run=dry_run,
                silent=pipe,
            )
        except PhotoScalerError as e:
            if not pipe:
                console.print(f"[red]Error processing {file.name}: {e}[/red]")
            continue

        if result.path:
            scaled_count += 1
            if pipe:
                print(result.path.absolute())

    if not pipe:
        if not dry_run:
            console.print(
                f"\n[bold green]Done! Processed {scaled_count} images.[/bold green]"
            )
        else:
            console.print(
                f"\n[yellow][dry-run] Would have processed {scaled_count} images.[/yellow]"
            )


if __name__ == "__main__":
    app()
