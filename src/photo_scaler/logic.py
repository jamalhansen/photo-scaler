from pathlib import Path
from typing import Annotated, Optional

import typer
from PIL import Image
from rich.console import Console
from rich.panel import Panel

from local_first_common.cli import (
    dry_run_option,
    resolve_dry_run,
)
from local_first_common.tracking import register_tool

_TOOL = register_tool("photo-scaler")
console = Console()
app = typer.Typer(help="Resizes images and saves as optimized JPEG.")

def scale_image(
    image_path: Path, 
    max_dim: int = 1200, 
    quality: int = 85, 
    suffix: str = "", 
    dry_run: bool = False
) -> Optional[Path]:
    """Resize image if it exceeds max_dim and save as JPEG."""
    try:
        img = Image.open(image_path)
        orig_w, orig_h = img.size
        
        # Calculate new dimensions
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

        # Determine output path
        if suffix:
            out_name = f"{image_path.stem}{suffix}.jpg"
        else:
            out_name = f"{image_path.stem}.jpg"
        
        out_path = image_path.parent / out_name

        if not scale_needed and image_path.suffix.lower() == ".jpg" and not suffix:
            console.print(f"[dim]No scaling or format change needed for {image_path.name}[/dim]")
            return None

        if dry_run:
            action = "Scale and convert" if scale_needed else "Convert"
            console.print(f"[yellow][dry-run] Would {action} {image_path.name} -> {out_name} ({new_w}x{new_h})[/yellow]")
            return out_path

        # Perform resizing
        if scale_needed:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary (e.g. for PNG with alpha)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.save(out_path, "JPEG", quality=quality, optimize=True)
        console.print(f"[green]Successfully saved {out_path.name} ({new_w}x{new_h})[/green]")
        return out_path

    except Exception as e:
        console.print(f"[red]Error processing {image_path.name}: {e}[/red]")
        return None

@app.command()
def scale(
    path: Annotated[Path, typer.Argument(help="File or directory to scale")],
    max_dim: Annotated[int, typer.Option("--max", help="Maximum dimension (width or height)")] = 1200,
    quality: Annotated[int, typer.Option("--quality", help="JPEG quality (1-100)")] = 85,
    suffix: Annotated[str, typer.Option("--suffix", help="Suffix to add to output filename (e.g. -scaled)")] = "",
    dry_run: Annotated[bool, dry_run_option()] = False,
):
    """Resize images to a target maximum dimension and save as optimized JPEG."""
    dry_run = resolve_dry_run(dry_run, False)

    if not path.exists():
        console.print(f"[red]Path does not exist: {path}[/red]")
        raise typer.Exit(1)

    files_to_process = []
    if path.is_file():
        files_to_process.append(path)
    elif path.is_dir():
        for ext in (".jpg", ".jpeg", ".png", ".tiff", ".webp"):
            files_to_process.extend(path.glob(f"*{ext}"))
            files_to_process.extend(path.glob(f"*{ext.upper()}"))

    if not files_to_process:
        console.print(f"No images found in {path}")
        return

    console.print(Panel(f"Scaling {len(files_to_process)} images to max {max_dim}px...", title="Image Scaler", border_style="cyan"))

    scaled_count = 0
    for file in files_to_process:
        if scale_image(file, max_dim=max_dim, quality=quality, suffix=suffix, dry_run=dry_run):
            scaled_count += 1

    if not dry_run:
        console.print(f"\n[bold green]Done! Processed {scaled_count} images.[/bold green]")
    else:
        console.print(f"\n[yellow][dry-run] Would have processed {scaled_count} images.[/yellow]")

if __name__ == "__main__":
    app()
