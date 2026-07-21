"""Unit tests for the image-derivation transform (no storage/DB needed).

The full derive + fulfill_for_entry flow (storage + attach) is exercised live; here we pin the pure
transform: a 'thumbnail' is a square center-crop of the source, and kind spellings normalize.
"""

import io

from PIL import Image

from marvin.services.assets.asset_derivation_service import AssetDerivationService


def _png(w: int, h: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (10, 120, 200)).save(buf, "PNG")
    return buf.getvalue()


def test_normalize_kind_aliases():
    for spell in ("thumbnail", "Thumb", "cropped", "CROP"):
        assert AssetDerivationService.normalize_kind(spell) == "thumbnail"
    assert AssetDerivationService.normalize_kind("palette") is None   # not supported yet
    assert AssetDerivationService.normalize_kind("") is None


def test_render_thumbnail_is_a_square_jpeg_crop():
    svc = AssetDerivationService(repos=None, storage=None)
    out, ext, mime = svc._render("thumbnail", _png(800, 600))   # non-square source
    assert (ext, mime) == ("jpg", "image/jpeg")
    img = Image.open(io.BytesIO(out))
    assert img.size == (512, 512)      # center-cropped to a square, resized
    assert img.format == "JPEG"
