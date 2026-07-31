"""
Multimodal input pipeline.

The primary, always-available input is pasted text. Image input is supported
when an OCR engine (pytesseract + Tesseract) is installed; otherwise the pipeline
degrades gracefully and asks the user to paste or correct the text — it never
silently fails. Uploaded bytes are processed in memory and discarded unless the
user's passport explicitly opts into storage.
"""
from __future__ import annotations

import io

try:  # optional dependency
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore
    _HAS_PIL = True
except Exception:  # pragma: no cover
    pytesseract = None
    _HAS_PIL = False
    try:
        from PIL import Image  # type: ignore
        _HAS_PIL = True
    except Exception:
        Image = None
        _HAS_PIL = False


def ocr_available() -> bool:
    if pytesseract is None:
        return False
    try:  # pragma: no cover
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def image_quality_report(image_bytes: bytes) -> dict:
    """Cheap, dependency-light quality hints (size, aspect). Pillow only."""
    report = {"ok": True, "notes": [], "width": None, "height": None}
    if not _HAS_PIL or Image is None:
        report["ok"] = False
        report["notes"].append("Image tools are not installed on this server.")
        return report
    try:
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        report["width"], report["height"] = w, h
        if min(w, h) < 400:
            report["notes"].append(
                "The image is small — text may be hard to read. A closer, "
                "well-lit photo helps.")
        if img.mode not in ("RGB", "L"):
            report["notes"].append("Unusual color mode; results may vary.")
    except Exception:
        report["ok"] = False
        report["notes"].append("This file could not be opened as an image.")
    return report


def extract_text(image_bytes: bytes, languages: str = "eng") -> dict:
    """
    Return {"text", "confidence", "available", "message"}.

    When OCR is unavailable, `available` is False and `message` explains the
    graceful fallback so the UI can prompt the user to paste text instead.
    """
    if not ocr_available():
        return {
            "text": "",
            "confidence": None,
            "available": False,
            "message": ("Automatic text reading (OCR) is not installed on this "
                        "server. Please paste or type the text and AccessWeave "
                        "will do the rest."),
        }
    try:  # pragma: no cover - requires tesseract binary
        img = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(
            img, lang=languages, output_type=pytesseract.Output.DICT)
        words, confs = [], []
        for word, conf in zip(data["text"], data["conf"]):
            if word.strip():
                words.append(word)
                try:
                    c = float(conf)
                    if c >= 0:
                        confs.append(c)
                except ValueError:
                    pass
        text = " ".join(words)
        confidence = (sum(confs) / len(confs) / 100.0) if confs else None
        return {"text": text, "confidence": confidence,
                "available": True, "message": ""}
    except Exception as exc:
        return {"text": "", "confidence": None, "available": False,
                "message": f"Could not read the image: {exc}"}
