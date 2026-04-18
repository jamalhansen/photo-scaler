from pathlib import Path

from PIL import Image
from photo_scaler.logic import scale_image

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

def test_scale_image_no_scale_needed(tmp_path):
    # Small image
    img_path = create_test_image(tmp_path, 500, 500, name="small.jpg")
    
    # If no suffix and already jpg, should return the original path
    out_path = scale_image(img_path, max_dim=1000)
    assert out_path == img_path

def test_scale_image_dry_run(tmp_path):
    img_path = create_test_image(tmp_path, 2000, 2000)
    
    out_path = scale_image(img_path, max_dim=1000, dry_run=True)
    assert out_path is not None
    
    # Output file should NOT exist
    assert not out_path.exists()
