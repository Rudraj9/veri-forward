"""Memory-only English OCR, bounded before decoding or running Tesseract."""
import io
import os

try:
    from dotenv import load_dotenv
except ImportError:  # optional: the app still runs without python-dotenv
    def load_dotenv(*_args, **_kwargs):
        return False

load_dotenv()

# Standard Windows install locations, so a normal per-machine install works with
# no environment variable. An explicit TESSERACT_CMD always wins over these.
TESSERACT_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
    os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Tesseract-OCR", "tesseract.exe"),
)


def tesseract_command():
    """Resolve the Tesseract binary from the environment or a default install path."""
    configured = os.getenv("TESSERACT_CMD")
    if configured:
        return configured
    for candidate in TESSERACT_CANDIDATES:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def extract_image_text(data):
    if len(data) > 5_000_000:
        raise ValueError("Screenshot exceeds 5 MB")
    from PIL import Image, UnidentifiedImageError
    import pytesseract
    command = tesseract_command()
    if command:
        pytesseract.pytesseract.tesseract_cmd = command
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in ("PNG", "JPEG", "WEBP"):
                raise ValueError("Use a PNG, JPEG or WebP screenshot")
            if image.width > 5000 or image.height > 5000 or image.width * image.height > 12_000_000:
                raise ValueError("Screenshot dimensions exceed limits")
            text = pytesseract.image_to_string(image.convert("RGB"), lang="eng", timeout=30)
    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError(
            "Tesseract OCR is not installed. Install it with "
            "'winget install UB-Mannheim.TesseractOCR' and restart the app "
            "(no environment variable needed), then try again. "
            "Alternatively paste the screenshot text."
        ) from exc
    except (UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid or oversized screenshot") from exc
    if not text.strip():
        raise ValueError("OCR found no readable text. Paste the text manually.")
    return text[:20000]
