from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image
from rich.console import Console

console = Console(stderr=True)


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
