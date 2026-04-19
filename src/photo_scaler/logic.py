import sys
from dataclasses import dataclass
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


class PhotoScalerError(Exception):
    """Base error for photo-scaler core operations."""


class ImageReadError(PhotoScalerError):
    """Raised when input image cannot be opened or decoded."""


class ImageWriteError(PhotoScalerError):
    """Raised when output image cannot be written."""


@dataclass
class ScaleImageResult:
    path: Path
    action: str


def scale_image_or_raise(
    image_path: Path,
    max_dim: int = 1200,
    quality: int = 85,
    suffix: str = "",
    dry_run: bool = False,
    silent: bool = False,
) -> ScaleImageResult:
    """Resize image if it exceeds max_dim and save as JPEG.

    Raises typed errors for image decode/encode failures.
    """
    try:
        img = Image.open(image_path)
    except Exception as e:  # noqa: BLE001
        raise ImageReadError(f"Could not open image {image_path.name}: {e}") from e

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
        return ScaleImageResult(path=image_path, action="unchanged")

    if dry_run:
        if not silent:
            action = "Scale and convert" if scale_needed else "Convert"
            console.print(
                f"[yellow][dry-run] Would {action} {image_path.name} -> {out_name} ({new_w}x{new_h})[/yellow]"
            )
        return ScaleImageResult(path=out_path, action="dry_run")

    if scale_needed:
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    try:
        img.save(out_path, "JPEG", quality=quality, optimize=True)
    except Exception as e:  # noqa: BLE001
        raise ImageWriteError(f"Could not save {out_name}: {e}") from e

    if not silent:
        console.print(
            f"[green]Successfully saved {out_path.name} ({new_w}x{new_h})[/green]"
        )
    return ScaleImageResult(path=out_path, action="scaled")


def scale_image(
    image_path: Path,
    max_dim: int = 1200,
    quality: int = 85,
    suffix: str = "",
    dry_run: bool = False,
    silent: bool = False,
) -> Optional[Path]:
    """Compatibility wrapper for callers that expect Optional[Path]."""
    try:
        result = scale_image_or_raise(
            image_path,
            max_dim=max_dim,
            quality=quality,
            suffix=suffix,
            dry_run=dry_run,
            silent=silent,
        )
        return result.path
    except PhotoScalerError as e:
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
