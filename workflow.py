"""
Llama Cloud Workflow Entry Point.

Uses the standalone `workflows` API (compatible with Llama Cloud appserver).
Accepts either:
  1. Base64-encoded PDFs (po, dn, inv) → parses with LlamaParse + Gemini → cross-references
  2. Pre-parsed JSON (po, dn, inv dicts) → cross-references directly
"""

import os
import json
import re
import base64
import tempfile
import asyncio
from dotenv import load_dotenv

load_dotenv()

from workflows import Workflow, step, Context
from workflows.events import StartEvent, StopEvent, Event

import google.generativeai as genai
from llama_parse import LlamaParse


# ── Configure Gemini ──────────────────────────────────────────────────
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-flash")


# ── Events ────────────────────────────────────────────────────────────

class DocumentsParsed(Event):
    """Fired after all 3 PDFs are parsed into JSON."""
    po_json: str
    dn_json: str
    inv_json: str


# ── Helpers ───────────────────────────────────────────────────────────

def _safe_parse_json(text: str) -> dict:
    """Parse JSON from text, handling markdown code blocks."""
    if isinstance(text, dict):
        return text
    if isinstance(text, str):
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}
    return {}


def _find_matching_item(items: list, item_code: str, item_name: str) -> dict | None:
    """Find a matching item by code or name."""
    for item in items:
        if item.get("item_code", "").strip().upper() == item_code.strip().upper():
            return item
    for item in items:
        if item_name.strip().lower() in item.get("item_name", "").strip().lower():
            return item
        if item.get("item_name", "").strip().lower() in item_name.strip().lower():
            return item
    return None


def _check_values(val1, val2, label1: str, label2: str) -> dict:
    """Compare two values and return a check result."""
    if val1 is None and val2 is None:
        return {"match": True, "status": "⚪ N/A"}
    if val1 is None or val2 is None:
        return {
            "match": False,
            "status": "🔴 MISSING DATA",
            label1: val1,
            label2: val2,
        }
    try:
        v1, v2 = float(val1), float(val2)
        if abs(v1 - v2) < 0.01:
            return {"match": True, "status": "🟢 MATCH", label1: v1, label2: v2}
        else:
            return {"match": False, "status": "🔴 MISMATCH", label1: v1, label2: v2}
    except (ValueError, TypeError):
        if str(val1).strip().lower() == str(val2).strip().lower():
            return {"match": True, "status": "🟢 MATCH", label1: val1, label2: val2}
        else:
            return {"match": False, "status": "🔴 MISMATCH", label1: val1, label2: val2}


def cross_reference(po_json: str, dn_json: str, inv_json: str) -> str:
    """Cross-reference PO, DN, and Invoice data."""
    po_data = _safe_parse_json(po_json)
    dn_data = _safe_parse_json(dn_json)
    inv_data = _safe_parse_json(inv_json)

    po_items = po_data.get("items", [])
    dn_items = dn_data.get("items", [])
    inv_items = inv_data.get("items", [])

    results = []
    all_matched = True

    for po_item in po_items:
        item_code = po_item.get("item_code", "UNKNOWN")
        item_name = po_item.get("item_name", "Unknown")
        dn_item = _find_matching_item(dn_items, item_code, item_name)
        inv_item = _find_matching_item(inv_items, item_code, item_name)

        checks = {}
        item_matched = True

        po_qty = po_item.get("quantity")
        dn_qty = dn_item.get("quantity") if dn_item else None
        check = _check_values(po_qty, dn_qty, "PO (ordered)", "DN (delivered)")
        checks["quantity_po_vs_dn"] = check
        if not check["match"]:
            item_matched = False

        inv_qty = inv_item.get("quantity") if inv_item else None
        check = _check_values(dn_qty, inv_qty, "DN (delivered)", "INV (invoiced)")
        checks["quantity_dn_vs_inv"] = check
        if not check["match"]:
            item_matched = False

        po_price = po_item.get("unit_price")
        inv_price = inv_item.get("unit_price") if inv_item else None
        check = _check_values(po_price, inv_price, "PO (price)", "INV (price)")
        checks["unit_price_po_vs_inv"] = check
        if not check["match"]:
            item_matched = False

        if not item_matched:
            all_matched = False

        results.append({
            "item_code": item_code,
            "item_name": item_name,
            "status": "🟢 MATCH" if item_matched else "🔴 MISMATCH",
            "checks": checks,
        })

    matched_count = sum(1 for r in results if "🟢" in r["status"])
    mismatched_count = len(results) - matched_count

    report = {
        "match_summary": {
            "status": "🟢 ALL MATCHED" if all_matched else "🔴 MISMATCH DETECTED",
            "total_items": len(results),
            "matched": matched_count,
            "mismatched": mismatched_count,
        },
        "document_refs": {
            "po_number": po_data.get("po_number", "N/A"),
            "dn_number": dn_data.get("dn_number", "N/A"),
            "inv_number": inv_data.get("inv_number", "N/A"),
        },
        "items": results,
        "recommendation": (
            "✅ APPROVE payment" if all_matched
            else f"❌ HOLD payment — {mismatched_count} discrepancies detected"
        ),
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


def generate_report_summary(report_json: str) -> str:
    """Generate a human-readable summary from the match report."""
    report = _safe_parse_json(report_json)
    summary_info = report.get("match_summary", {})
    doc_refs = report.get("document_refs", {})
    items = report.get("items", [])

    lines = [
        "=" * 50,
        "  3-WAY MATCH REPORT",
        "=" * 50,
        "",
        f"  PO: {doc_refs.get('po_number', 'N/A')}",
        f"  DN: {doc_refs.get('dn_number', 'N/A')}",
        f"  INV: {doc_refs.get('inv_number', 'N/A')}",
        "",
        f"  Status: {summary_info.get('status', 'N/A')}",
        f"  Items: {summary_info.get('matched', 0)} matched, {summary_info.get('mismatched', 0)} mismatched",
        "",
    ]

    for item in items:
        lines.append(f"  [{item['status']}] {item['item_code']} — {item['item_name']}")

    lines.append("")
    lines.append(f"  {report.get('recommendation', '')}")
    lines.append("=" * 50)

    return "\n".join(lines)


# ── PDF Parsing ──────────────────────────────────────────────────────

PO_SCHEMA = """{
  "po_number": "string", "date": "string", "supplier": "string",
  "items": [{"item_code": "string", "item_name": "string", "quantity": number, "unit": "string or null", "unit_price": number, "total": number}],
  "grand_total": number
}"""

DN_SCHEMA = """{
  "dn_number": "string", "date": "string",
  "items": [{"item_code": "string", "item_name": "string", "quantity": number, "unit": "string or null"}],
  "notes": "string or null"
}"""

INV_SCHEMA = """{
  "inv_number": "string", "date": "string",
  "items": [{"item_code": "string", "item_name": "string", "quantity": number, "unit": "string or null", "unit_price": number, "total": number}],
  "subtotal": number, "vat_rate": number, "vat_amount": number, "grand_total": number
}"""


async def _parse_pdf_base64(b64_data: str, doc_type: str, schema: str) -> str:
    """Decode base64 PDF → LlamaParse → Gemini structured extraction."""
    # Decode base64 to temp file
    pdf_bytes = base64.b64decode(b64_data)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix=f"{doc_type}_")
    tmp.write(pdf_bytes)
    tmp.close()

    try:
        # Parse PDF to markdown with LlamaParse
        parser = LlamaParse(
            api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
            result_type="markdown",
        )
        documents = await parser.aload_data(tmp.name)
        markdown = "\n\n".join([doc.text for doc in documents])

        # Extract structured data with Gemini
        prompt = f"""Analyze this {doc_type} document and extract data into the following JSON schema.
Return ONLY valid JSON, no markdown code blocks.

Schema:
{schema}

Document text:
{markdown}"""

        response = await gemini_model.generate_content_async(prompt)
        return response.text.strip()
    finally:
        os.unlink(tmp.name)


# ── Workflow Definition ──────────────────────────────────────────────

class ThreeWayMatcher(Workflow):
    """
    3-Way Matcher workflow for Llama Cloud deployment.
    Accepts either:
      - base64-encoded PDFs → parses + cross-references
      - pre-parsed JSON dicts → cross-references directly
    """

    @step
    async def parse_documents(self, event: StartEvent, ctx: Context) -> DocumentsParsed | StopEvent:
        user_input = event.input if hasattr(event, 'input') else str(event)
        parsed = _safe_parse_json(user_input)

        # Path 1: Pre-parsed JSON with po/dn/inv dicts (not base64)
        if parsed and all(k in parsed for k in ["po", "dn", "inv"]):
            po_val = parsed["po"]
            dn_val = parsed["dn"]
            inv_val = parsed["inv"]

            # Check if values are dicts (already parsed) or base64 strings
            if isinstance(po_val, dict) and isinstance(dn_val, dict) and isinstance(inv_val, dict):
                po_json = json.dumps(po_val)
                dn_json = json.dumps(dn_val)
                inv_json = json.dumps(inv_val)
                return DocumentsParsed(po_json=po_json, dn_json=dn_json, inv_json=inv_json)

            # Path 2: Base64-encoded PDFs
            if isinstance(po_val, str) and isinstance(dn_val, str) and isinstance(inv_val, str):
                po_json, dn_json, inv_json = await asyncio.gather(
                    _parse_pdf_base64(po_val, "Purchase Order", PO_SCHEMA),
                    _parse_pdf_base64(dn_val, "Delivery Note", DN_SCHEMA),
                    _parse_pdf_base64(inv_val, "Invoice", INV_SCHEMA),
                )
                return DocumentsParsed(po_json=po_json, dn_json=dn_json, inv_json=inv_json)

        # Path 3: Freeform text — use Gemini to interpret
        prompt = f"""You are a 3-way matching assistant for supply chain documents.
The user sent this message:

{user_input}

If the user provided PO, DN, and Invoice data, extract and organize them.
If not enough data, explain what's needed:
- Purchase Order (PO) data as JSON
- Delivery Note (DN) data as JSON  
- Invoice (INV) data as JSON

Each should have: items (with item_code, item_name, quantity, unit_price, total), 
and document number (po_number, dn_number, inv_number).

Respond helpfully."""

        response = await gemini_model.generate_content_async(prompt)
        return StopEvent(result=response.text)

    @step
    async def match_documents(self, event: DocumentsParsed, ctx: Context) -> StopEvent:
        report_json = cross_reference(event.po_json, event.dn_json, event.inv_json)
        summary = generate_report_summary(report_json)

        # Parse the JSON strings for the response
        result = {
            "success": True,
            "report": _safe_parse_json(report_json),
            "summary": summary,
            "parsed_data": {
                "po": _safe_parse_json(event.po_json),
                "dn": _safe_parse_json(event.dn_json),
                "inv": _safe_parse_json(event.inv_json),
            },
        }
        return StopEvent(result=json.dumps(result, ensure_ascii=False))


workflow = ThreeWayMatcher(timeout=None)
