# -*- coding: utf-8 -*-
import base64, io, os, re, unicodedata, json
from typing import Dict, Any, List, Tuple
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

from backend.ai_providers import PROVIDERS, AIProviderError

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

SCHEMA = [
  "well_name","kb_offset",
  "casing_od","casing_weight","casing_top","casing_bottom",
  "tubing_od","tubing_weight","tubing_top","tubing_bottom","tubing_avg_joint_length",
  "rod_string","tubing_anchor","pc_pump_depth",
  "perforation_top","perforation_bottom","plugback"
]

def load_font(size: int):
    for p in [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\segoeui.ttf"]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()

def decode_image(b64: str) -> Image.Image:
    data = base64.b64decode(b64.split(",")[-1])
    return Image.open(io.BytesIO(data)).convert("RGBA")

def encode_image(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

def draw_autofit_text(draw: ImageDraw.ImageDraw, text: str, x: float, y: float, w: float, h: float, initial_size: int):
    size = max(8, int(initial_size))
    while size > 8:
        font = load_font(size)
        bbox = draw.textbbox((x, y), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= w and height <= h:
            draw.text((x, y), text, font=font, fill="black")
            return size
        size -= 1
    draw.text((x, y), text, font=load_font(8), fill="black")
    return 8

def render(payload: Dict[str, Any]) -> Image.Image:
    img = decode_image(payload["template_base64"])
    draw = ImageDraw.Draw(img)

    image_size = payload.get("image_size")
    if image_size and len(image_size) == 2:
        exp_w, exp_h = image_size
        rw, rh = img.size
        sx = rw / exp_w if exp_w else 1.0
        sy = rh / exp_h if exp_h else 1.0
    else:
        sx = sy = 1.0

    values: Dict[str, Any] = payload.get("values", {})
    fields: List[Dict[str, Any]] = payload.get("fields", [])
    missing = "Não presente no PDF"

    for f in fields:
        name = f.get("name", "")
        x = float(f.get("x", 0)) * sx
        y = float(f.get("y", 0)) * sy
        w = float(f.get("w", 0)) * sx
        h = float(f.get("h", 0)) * sy
        fs = int(f.get("font_size", 18))
        border = bool(f.get("border", False))

        value = str(values.get(name, missing))
        if border:
            draw.rectangle([x, y, x + w, y + h], outline="black", width=1)

        draw_autofit_text(draw, value, x, y, w, h, fs)

    return img

def _read_with_pymupdf(pdf_bytes: bytes, max_pages: int):
    if not fitz:
        return "", "pymupdf_not_installed"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texts = []
        for i in range(min(max_pages, len(doc))):
            page = doc[i]
            texts.append(page.get_text("text") or "")
        return "\n".join(texts), "pymupdf"
    except Exception as e:
        return "", f"pymupdf_error:{e}"

def _read_with_pypdf2(pdf_bytes: bytes, max_pages: int):
    if not PdfReader:
        return "", "pypdf2_not_installed"
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for i, page in enumerate(reader.pages[:max_pages]):
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
        return "\n".join(pages), "pypdf2"
    except Exception as e:
        return "", f"pypdf2_error:{e}"

def parse_pdf_text(pdf_b64: str, max_pages: int = 2):
    data = base64.b64decode(pdf_b64.split(",")[-1])
    text, method = _read_with_pymupdf(data, max_pages)
    if len(text.strip()) < 30:
        ftext, fmethod = _read_with_pypdf2(data, max_pages)
        if len(ftext.strip()) > len(text.strip()):
            text, method = ftext, fmethod
    meta = {"method": method, "length": len(text)}
    return text, meta

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/api/generate")
def generate():
    try:
        payload = request.get_json(force=True)
        img = render(payload)
        return jsonify({"image_base64": encode_image(img)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.post("/api/generate_pdf")
def generate_pdf():
    try:
        payload = request.get_json(force=True)
        img = render(payload).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PDF")
        pdf_b64 = "data:application/pdf;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
        return jsonify({"pdf_base64": pdf_b64})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.post("/api/extract_pdf")
def extract_pdf():
    try:
        payload = request.get_json(force=True)
        pdf_b64 = payload["pdf_base64"]
        raw_text, meta = parse_pdf_text(pdf_b64, max_pages=int(payload.get("max_pages", 2)))
        return jsonify({"ok": True, "raw_text": raw_text, "meta": meta})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.post("/api/ai_extract")
def ai_extract():
    try:
        from .ai_providers import PROVIDERS
        payload = request.get_json(force=True)
        text = payload.get("text", "")
        if not text:
            pdf_b64 = payload.get("pdf_base64")
            if not pdf_b64:
                return jsonify({"ok": False, "error": "Forneça 'text' ou 'pdf_base64'"}), 400
            raw_text, meta = parse_pdf_text(pdf_b64, max_pages=int(payload.get("max_pages", 2)))
            text = raw_text or ""
        else:
            meta = {"method": "text_manual", "length": len(text)}

        provider = (payload.get("provider") or os.getenv("AI_PROVIDER") or "openai").lower()
        options = payload.get("provider_options", {})

        if provider not in PROVIDERS:
            return jsonify({"ok": False, "error": f"Provider '{provider}' não suportado"}), 400

        fn = PROVIDERS[provider]
        result = fn(text, SCHEMA, **options)
        cleaned = {k: str(result.get(k, "")) for k in SCHEMA}
        return jsonify({"ok": True, "values": cleaned, "meta": meta, "provider": provider})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
