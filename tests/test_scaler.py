from pathlib import Path

from PIL import Image

from photo_scaler.core import ImageReadError, scale_image, scale_image_or_raise


def create_test_image(tmp_path: Path, width: int, height: int, name: str = "test.png"):
    img_path = tmp_path / name
    img = Image.new("RGB", (width, height), color="blue")
    img.save(img_path)
    return img_path


def test_scale_image_down(tmp_path):
    # Large landscape image
    img_path = create_test_image(tmp_path, 2000, 1000)

    out_path = scale_image(img_path, max_dim=1000, suffix="-scaled")
    assert out_path is not None
    assert out_path.name == "test-scaled.jpg"

    # Verify dimensions
    out_img = Image.open(out_path)
    assert out_img.size == (1000, 500)


def test_scale_image_portrait(tmp_path):
    # Large portrait image
    img_path = create_test_image(tmp_path, 1000, 2000)

    out_path = scale_image(img_path, max_dim=1000)
    assert out_path is not None
    assert out_path.name == "test.jpg"

    # Verify dimensions
    out_img = Image.open(out_path)
    assert out_img.size == (500, 1000)

    # The .png original must not survive alongside the new .jpg -- "overwrites
    # in place" means exactly one file after a scale, regardless of the input
    # extension. Found live 2026-09-20: every non-.jpg photo through the real
    # pipeline was silently doubling on disk because this wasn't checked.
    assert not img_path.exists()


def test_scale_image_no_scale_needed(tmp_path):
    # Small image
    img_path = create_test_image(tmp_path, 500, 500, name="small.jpg")

    # If no suffix and already jpg, should return the original path
    out_path = scale_image(img_path, max_dim=1000)
    assert out_path == img_path


def test_scale_needed_jpeg_extension_overwrites_in_place_no_duplicate(tmp_path):
    """The real-world failure case: a .jpeg (not .jpg) source that needs scaling."""
    img_path = create_test_image(tmp_path, 2000, 1000, name="photo.jpeg")

    out_path = scale_image(img_path, max_dim=1000)
    assert out_path is not None
    assert out_path.name == "photo.jpg"
    assert not img_path.exists()
    assert list(tmp_path.iterdir()) == [out_path]


def test_no_scale_needed_jpeg_extension_left_untouched(tmp_path):
    """A .jpeg that's already small enough shouldn't be re-encoded or renamed."""
    img_path = create_test_image(tmp_path, 500, 500, name="small.jpeg")

    out_path = scale_image(img_path, max_dim=1000)
    assert out_path == img_path
    assert img_path.exists()
    assert list(tmp_path.iterdir()) == [img_path]


def test_suffix_mode_keeps_original_alongside_the_copy(tmp_path):
    """--suffix is the one case where BOTH files are supposed to survive."""
    img_path = create_test_image(tmp_path, 2000, 1000, name="photo.jpeg")

    out_path = scale_image(img_path, max_dim=1000, suffix="-scaled")
    assert out_path.name == "photo-scaled.jpg"
    assert img_path.exists()
    assert out_path.exists()


def test_scale_image_dry_run(tmp_path):
    img_path = create_test_image(tmp_path, 2000, 2000)

    out_path = scale_image(img_path, max_dim=1000, dry_run=True)
    assert out_path is not None

    # Output file should NOT exist
    assert not out_path.exists()


def test_scale_image_or_raise_raises_on_missing_file(tmp_path):
    missing = tmp_path / "missing.png"

    try:
        scale_image_or_raise(missing, silent=True)
    except ImageReadError:
        pass
    else:
        raise AssertionError("Expected ImageReadError")
