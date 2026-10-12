"""Memory-only English OCR, bounded before decoding or running Tesseract."""
import io
import os


def extract_image_text(data):
    if len(data) > 5_000_000:
        raise ValueError("Screenshot exceeds 5 MB")
    from PIL import Image, UnidentifiedImageError
    import pytesseract
    if os.getenv("TESSERACT_CMD"):
        pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in ("PNG", "JPEG", "WEBP"):
                raise ValueError("Use a PNG, JPEG or WebP screenshot")
            if image.width > 5000 or image.height > 5000 or image.width * image.height > 12_000_000:
                raise ValueError("Screenshot dimensions exceed limits")
            text = pytesseract.image_to_string(image.convert("RGB"), lang="eng", timeout=30)
    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError("Tesseract is unavailable. Install it and set TESSERACT_CMD; alternatively paste the screenshot text.") from exc
    except (UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid or oversized screenshot") from exc
    if not text.strip():
        raise ValueError("OCR found no readable text. Paste the text manually.")
    return text[:20000]
