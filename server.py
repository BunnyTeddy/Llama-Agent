"""
3-Way Matcher — FastAPI Backend
Accepts 3 PDF uploads (PO, DN, Invoice), parses them, cross-references, and returns a match report.

Run: python server.py
"""

import asyncio
import json
import os
import sys
import tempfile
import traceback
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from tools.parser_tools import parse_purchase_order, parse_delivery_note, parse_invoice
from tools.matching_tools import cross_reference, generate_report_summary


def _try_parse_json(text):
    """Safely parse JSON string, return raw string if not valid JSON."""
    if isinstance(text, dict):
        return text
    try:
        import re
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return text


# ── Lifespan ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate API keys on startup
    missing = []
    if not os.getenv("LLAMA_CLOUD_API_KEY"):
        missing.append("LLAMA_CLOUD_API_KEY")
    if not os.getenv("GOOGLE_API_KEY"):
        missing.append("GOOGLE_API_KEY")
    if missing:
        print(f"⚠️  Warning: Missing API keys: {', '.join(missing)}")
        print("   PDF parsing will fail. Set them in .env")
    else:
        print("✅ API keys configured")
    
    print("🚀 3-Way Matcher API running on http://localhost:8000")
    print("📖 API docs: http://localhost:8000/docs")
    yield


app = FastAPI(
    title="3-Way Matcher API",
    description="Upload 3 PDFs (PO, DN, Invoice) for automated supply chain reconciliation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origins (dev + Vercel production)
_default_origins = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
_cors_origins = os.getenv("CORS_ORIGINS", _default_origins)
allowed_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "3-way-matcher"}


# ── Main matching endpoint ────────────────────────────────────────────
@app.post("/api/match")
async def match_documents(
    po: UploadFile = File(..., description="Purchase Order PDF"),
    dn: UploadFile = File(..., description="Delivery Note PDF"),
    inv: UploadFile = File(..., description="Invoice PDF"),
):
    """
    Upload 3 PDF files for 3-way matching.
    Returns a detailed match report with per-item comparison.
    """
    # Validate file types
    for label, file in [("PO", po), ("DN", dn), ("Invoice", inv)]:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, f"{label} file must be a PDF (got: {file.filename})")

    # Save uploads to temp files
    temp_files = []
    try:
        for label, file in [("po", po), ("dn", dn), ("inv", inv)]:
            content = await file.read()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix=f"{label}_")
            tmp.write(content)
            tmp.close()
            temp_files.append(tmp.name)
        
        po_path, dn_path, inv_path = temp_files

        # Parse all 3 PDFs in parallel using LlamaParse + Gemini
        print("⏳ Parsing 3 PDFs...")
        po_json, dn_json, inv_json = await asyncio.gather(
            parse_purchase_order(po_path),
            parse_delivery_note(dn_path),
            parse_invoice(inv_path),
        )
        print(f"✅ PO parsed: {po_json[:100]}...")
        print(f"✅ DN parsed: {dn_json[:100]}...")
        print(f"✅ INV parsed: {inv_json[:100]}...")

        # Cross-reference
        report_json = cross_reference(po_json, dn_json, inv_json)
        report = json.loads(report_json)

        # Generate human-readable summary
        summary = generate_report_summary(report_json)

        return {
            "success": True,
            "report": report,
            "summary": summary,
            "parsed_data": {
                "po": _try_parse_json(po_json),
                "dn": _try_parse_json(dn_json),
                "inv": _try_parse_json(inv_json),
            },
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Matching failed: {str(e)}")

    finally:
        # Clean up temp files
        for path in temp_files:
            try:
                os.unlink(path)
            except OSError:
                pass


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
