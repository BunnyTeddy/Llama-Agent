"""
Llama Cloud Workflow Entry Point.

Uses the standalone `workflows` API (compatible with Llama Cloud appserver).
Avoids importing from `llama_index.core` to prevent version conflicts.
"""

import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

from workflows import Workflow, step, Context
from workflows.events import StartEvent, StopEvent

import google.generativeai as genai


# ── Configure Gemini ──────────────────────────────────────────────────
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-flash")


# ── Matching Logic (pure Python, no external deps) ────────────────────

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
        if item.get("item_code", "").strip() == item_code.strip():
            return item
    for item in items:
        if item.get("item_name", "").strip().lower() == item_name.strip().lower():
            return item
    return None


def _check_values(val1, val2, label1: str, label2: str) -> dict:
    """Compare two values and return a check result."""
    if val1 is None and val2 is None:
        return {"match": True, "status": "⚪ N/A"}
    if val1 is None or val2 is None:
        return {
            "match": False,
            "status": "🔴 THIẾU DỮ LIỆU",
            label1: val1,
            label2: val2,
        }
    try:
        v1, v2 = float(val1), float(val2)
        if abs(v1 - v2) < 0.01:
            return {"match": True, "status": "🟢 KHỚP", label1: v1, label2: v2}
        else:
            return {"match": False, "status": "🔴 LỆCH", label1: v1, label2: v2}
    except (ValueError, TypeError):
        if str(val1).strip().lower() == str(val2).strip().lower():
            return {"match": True, "status": "🟢 KHỚP", label1: val1, label2: val2}
        else:
            return {"match": False, "status": "🔴 LỆCH", label1: val1, label2: val2}


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

        # Check 1: PO qty vs DN qty
        po_qty = po_item.get("quantity")
        dn_qty = dn_item.get("quantity") if dn_item else None
        check = _check_values(po_qty, dn_qty, "PO (đặt)", "DN (giao)")
        checks["quantity_po_vs_dn"] = check
        if not check["match"]:
            item_matched = False

        # Check 2: DN qty vs INV qty
        inv_qty = inv_item.get("quantity") if inv_item else None
        check = _check_values(dn_qty, inv_qty, "DN (giao)", "INV (hóa đơn)")
        checks["quantity_dn_vs_inv"] = check
        if not check["match"]:
            item_matched = False

        # Check 3: PO unit price vs INV unit price
        po_price = po_item.get("unit_price")
        inv_price = inv_item.get("unit_price") if inv_item else None
        check = _check_values(po_price, inv_price, "PO (giá)", "INV (giá)")
        checks["unit_price_po_vs_inv"] = check
        if not check["match"]:
            item_matched = False

        if not item_matched:
            all_matched = False

        results.append({
            "item_code": item_code,
            "item_name": item_name,
            "status": "🟢 KHỚP" if item_matched else "🔴 LỆCH",
            "checks": checks,
        })

    report = {
        "po_number": po_data.get("po_number", "N/A"),
        "dn_number": dn_data.get("dn_number", "N/A"),
        "inv_number": inv_data.get("inv_number", "N/A"),
        "overall_status": "🟢 TẤT CẢ KHỚP" if all_matched else "🔴 CÓ SAI LỆCH",
        "recommendation": "✅ Đề xuất DUYỆT thanh toán" if all_matched else "❌ Đề xuất TẠM DỪNG thanh toán — cần xác minh",
        "items": results,
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


# ── PDF Parsing via Gemini ────────────────────────────────────────────

async def parse_document_with_gemini(text: str, doc_type: str, schema: str) -> str:
    """Use Gemini to extract structured data from document text."""
    prompt = f"""Analyze this {doc_type} document and extract data into the following JSON schema.
Return ONLY valid JSON, no markdown code blocks.

Schema:
{schema}

Document text:
{text}"""
    response = await gemini_model.generate_content_async(prompt)
    return response.text


# ── Workflow Definition ──────────────────────────────────────────────


class ThreeWayMatcher(Workflow):
    """
    3-Way Matcher workflow for Llama Cloud deployment.
    Accepts JSON data for PO, DN, and Invoice, then cross-references them.
    """

    @step
    async def match(self, event: StartEvent, ctx: Context) -> StopEvent:
        user_input = event.input if hasattr(event, 'input') else str(event)

        # Try to parse as JSON with po/dn/inv keys
        parsed = _safe_parse_json(user_input)

        if parsed and all(k in parsed for k in ["po", "dn", "inv"]):
            # Direct JSON input with pre-parsed data
            po_json = json.dumps(parsed["po"]) if isinstance(parsed["po"], dict) else parsed["po"]
            dn_json = json.dumps(parsed["dn"]) if isinstance(parsed["dn"], dict) else parsed["dn"]
            inv_json = json.dumps(parsed["inv"]) if isinstance(parsed["inv"], dict) else parsed["inv"]

            report = cross_reference(po_json, dn_json, inv_json)
            return StopEvent(result=report)

        # If not structured JSON, use Gemini to help interpret the request
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


workflow = ThreeWayMatcher(timeout=None)
