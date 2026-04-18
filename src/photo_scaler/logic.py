import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from PIL import Image
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

TOOL_NAME = "photo-scaler"
DEFAULTS = {"provider": "ollama", "model": "llama3"}
_TOOL = register_tool(TOOL_NAME)

console = Console(stderr=True)  # Send rich output to stderr
app = typer.Typer(help="Resizes images and saves as optimized JPEG.")


def scale_image(
    image_path: Path,
    max_dim: int = 1200,
    quality: int = 85,
    suffix: str = "",
    dry_run: bool = False,
    silent: bool = False,
) -> Optional[Path]:
    """Resize image if it exceeds max_dim and save as JPEG."""
    try:
        img = Image.open(image_path)
        orig_w, orig_h = img.size

        if orig_w > orig_h:
            if orig_w <= max_dim:
                scale_needed = False
                new_w, new_h = orig_w, orig_h
            else:
                scale_needed = True
                new_w = max_dim
                new_h = int(orig_h * (max_dim / orig_w))
        else:
            if orig_h <= max_dim:
                scale_needed = False
                new_w, new_h = orig_w, orig_h
            else:
                scale_needed = True
                new_h = max_dim
                new_w = int(orig_w * (max_dim / orig_h))

        if suffix:
            out_name = f"{image_path.stem}{suffix}.jpg"
        else:
            out_name = f"{image_path.stem}.jpg"

        out_path = image_path.parent / out_name

        if not scale_needed and image_path.suffix.lower() == ".jpg" and not suffix:
            if not silent:
                console.print(
                    f"[dim]No scaling or format change needed for {image_path.name}[/dim]"
                )
            return image_path  # Return existing path as it's ready

        if dry_run:
            if not silent:
                action = "Scale and convert" if scale_needed else "Convert"
                console.print(
                    f"[yellow][dry-run] Would {action} {image_path.name} -> {out_name} ({new_w}x{new_h})[/yellow]"
                )
            return out_path

        if scale_needed:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(out_path, "JPEG", quality=quality, optimize=True)
        if not silent:
            console.print(
                f"[green]Successfully saved {out_path.name} ({new_w}x{new_h})[/green]"
            )
        return out_path

    except Exception as e:
        if not silent:
            console.print(f"[red]Error processing {image_path.name}: {e}[/red]")
        return None


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
        new_path = scale_image(
            file,
            max_dim=max_dim,
            quality=quality,
            suffix=suffix,
            dry_run=dry_run,
            silent=pipe,
        )
        if new_path:
            scaled_count += 1
            if pipe:
                print(new_path.absolute())

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
