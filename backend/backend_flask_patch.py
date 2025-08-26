
# -*- coding: utf-8 -*-

"""
Flask com endpoint /api/ai_extract que usa ai_extract_rules.py para extrair campos do PDF/texto.
Endpoints:
  GET /health -> {"ok": true}
  POST /api/ai_extract
    body: {"pdf_base64": "..."} ou {"text": "..."}  (opcional "provider")
    resp: {"ok": true, "provider": "regex", "meta": {...}, "values": {...}}
Requisitos:
  pip install flask flask-cors pymupdf
"""
import base64
from typing import Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

# PDF
import fitz  # PyMuPDF

from ai_extract_rules import extract_values_from_text

app = Flask(__name__)
CORS(app)

def _pdf_to_text(pdf_b64: str, max_pages: Optional[int] = None) -> str:
    data = base64.b64decode(pdf_b64.split(",")[-1])
    with fitz.open(stream=data, filetype="pdf") as doc:
        pages = range(len(doc)) if max_pages is None else range(min(max_pages, len(doc)))
        chunks = []
        for i in pages:
            chunks.append(doc[i].get_text())
        return "\n".join(chunks)

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/api/ai_extract")
def ai_extract():
    j = request.get_json(force=True, silent=True) or {}
    txt = j.get("text", "")
    pdf_b64 = j.get("pdf_base64")
    provider = j.get("provider") or "regex"

    if not txt and not pdf_b64:
        return jsonify({"ok": False, "error": "text ou pdf_base64 são obrigatórios"}), 400

    try:
        if not txt and pdf_b64:
            txt = _pdf_to_text(pdf_b64, max_pages=j.get("max_pages"))

        values, debug = extract_values_from_text(txt)
        meta = {
            "length": len(txt or ""),
            "method": "regex",
            "notes": "Regra com bomba->pc_pump_depth e normalização de vírgula decimal.",
            "debug": debug,
        }
        return jsonify({"ok": True, "provider": provider, "meta": meta, "values": values})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
