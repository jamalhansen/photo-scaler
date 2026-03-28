# Image Scaler

Resizes an image so its longest dimension hits a target pixel count, then saves it as a high-quality JPEG.

## Features

- Preserves aspect ratio.
- Only scales down (never upscales).
- Configurable max dimension (`--max`).
- Configurable JPEG quality (`--quality`).
- Option to add filename suffix (`--suffix`).
- Supports single files or directory-wide batch processing.

## Usage

```bash
# Scale to default 1200px max
uv run scale-photo photo.png

# Scale to 2400px and save with suffix (photo-2400.jpg)
uv run scale-photo photo.png --max 2400 --suffix -2400

# Scale all images in a directory
uv run scale-photo ./raw_photos --max 1600

# Set JPEG quality (default 85)
uv run scale-photo photo.jpg --quality 95
```

## Development

```bash
# Run tests
uv run pytest
```

## Part of the Photo Pipeline
`photo-renamer` → `photo-metadata-scrubber` → `photo-scaler` → `unsplash-uploader`
