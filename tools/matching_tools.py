"""
Cross-reference matching tools for the 3-Way Matcher Agent.
Compares data from PO, Delivery Note, and Invoice to detect mismatches.
"""

import json
from typing import Any


def _safe_parse_json(json_str: str) -> dict:
    """Parse JSON string, handling markdown code blocks."""
    cleaned = json_str.strip()
    if cleaned.startswith("```"):
        # Remove markdown code block markers
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


def _find_matching_item(items: list[dict], item_code: str, item_name: str) -> dict | None:
    """Find an item in a list by item_code, falling back to item_name fuzzy match."""
    # Exact match on item_code
    for item in items:
        if item.get("item_code", "").strip().upper() == item_code.strip().upper():
            return item

    # Fallback: match by item_name (case-insensitive contains)
    for item in items:
        if item_name.strip().lower() in item.get("item_name", "").strip().lower():
            return item
        if item.get("item_name", "").strip().lower() in item_name.strip().lower():
            return item

    return None


def _check_values(val_a: Any, val_b: Any, label_a: str, label_b: str) -> dict:
    """Compare two values and return a check result."""
    # Handle None
    if val_a is None and val_b is None:
        return {
            "source_a": f"{label_a}: N/A",
            "source_b": f"{label_b}: N/A",
            "match": True,
            "note": "Both values not available"
        }
    if val_a is None or val_b is None:
        return {
            "source_a": f"{label_a}: {val_a}",
            "source_b": f"{label_b}: {val_b}",
            "match": False,
            "note": f"Missing value: {label_a if val_a is None else label_b} is N/A"
        }

    # Numeric comparison with tolerance
    try:
        num_a = float(val_a)
        num_b = float(val_b)
        match = abs(num_a - num_b) < 0.01
        note = None
        if not match:
            diff = num_a - num_b
            note = f"Chênh lệch: {diff:+.2f} ({label_a}: {num_a}, {label_b}: {num_b})"
        return {
            "source_a": f"{label_a}: {num_a}",
            "source_b": f"{label_b}: {num_b}",
            "match": match,
            "note": note
        }
    except (ValueError, TypeError):
        pass

    # String comparison
    match = str(val_a).strip().lower() == str(val_b).strip().lower()
    return {
        "source_a": f"{label_a}: {val_a}",
        "source_b": f"{label_b}: {val_b}",
        "match": match,
        "note": None if match else f"Giá trị không khớp: {label_a}={val_a}, {label_b}={val_b}"
    }


def cross_reference(po_json: str, dn_json: str, inv_json: str) -> str:
    """
    Perform 3-way cross-reference matching between PO, Delivery Note, and Invoice.

    Checks:
    - PO vs DN: Quantity ordered matches quantity delivered
    - PO vs INV: Unit price on PO matches unit price on invoice
    - DN vs INV: Quantity delivered matches quantity on invoice
    - Grand total verification

    Args:
        po_json: JSON string of Purchase Order data
        dn_json: JSON string of Delivery Note data
        inv_json: JSON string of Invoice data

    Returns:
        JSON string of the complete match report with 🟢/🔴 status
    """
    po_data = _safe_parse_json(po_json)
    dn_data = _safe_parse_json(dn_json)
    inv_data = _safe_parse_json(inv_json)

    po_items = po_data.get("items", [])
    dn_items = dn_data.get("items", [])
    inv_items = inv_data.get("items", [])

    results = []
    all_matched = True

    # Use PO items as the reference list
    for po_item in po_items:
        item_code = po_item.get("item_code", "UNKNOWN")
        item_name = po_item.get("item_name", "Unknown")

        # Find corresponding items in DN and Invoice
        dn_item = _find_matching_item(dn_items, item_code, item_name)
        inv_item = _find_matching_item(inv_items, item_code, item_name)

        checks = {}
        item_matched = True

        # Check 1: PO quantity vs DN quantity (Ordered vs Delivered)
        po_qty = po_item.get("quantity")
        dn_qty = dn_item.get("quantity") if dn_item else None

        check = _check_values(po_qty, dn_qty, "PO (đặt)", "DN (giao)")
        checks["quantity_po_vs_dn"] = check
        if not check["match"]:
            item_matched = False
            if po_qty and dn_qty:
                try:
                    diff = float(po_qty) - float(dn_qty)
                    if diff > 0:
                        check["note"] = f"Thiếu {diff:.0f} đơn vị hàng trên phiếu giao → cần xác minh trước khi thanh toán"
                    else:
                        check["note"] = f"Giao thừa {abs(diff):.0f} đơn vị so với PO → cần xác minh"
                except (ValueError, TypeError):
                    pass

        # Check 2: PO unit_price vs INV unit_price
        po_price = po_item.get("unit_price")
        inv_price = inv_item.get("unit_price") if inv_item else None

        check = _check_values(po_price, inv_price, "PO (giá đặt)", "INV (giá hóa đơn)")
        checks["unit_price_po_vs_inv"] = check
        if not check["match"]:
            item_matched = False

        # Check 3: DN quantity vs INV quantity (Delivered vs Invoiced)
        inv_qty = inv_item.get("quantity") if inv_item else None

        check = _check_values(dn_qty, inv_qty, "DN (giao)", "INV (hóa đơn)")
        checks["quantity_dn_vs_inv"] = check
        if not check["match"]:
            item_matched = False

        # Check 4: Line total verification (unit_price * quantity == total on invoice)
        if inv_item and inv_item.get("unit_price") and inv_item.get("quantity") and inv_item.get("total"):
            try:
                calculated = float(inv_item["unit_price"]) * float(inv_item["quantity"])
                actual = float(inv_item["total"])
                check = _check_values(calculated, actual, "Tính lại (giá×SL)", "INV (thành tiền)")
                checks["line_total_verification"] = check
                if not check["match"]:
                    item_matched = False
            except (ValueError, TypeError):
                pass

        if not item_matched:
            all_matched = False

        results.append({
            "item_code": item_code,
            "item_name": item_name,
            "status": "🟢 Khớp 100%" if item_matched else "🔴 Sai lệch",
            "checks": checks
        })

    # Check for items in DN/INV that are NOT in PO (unexpected items)
    for dn_item in dn_items:
        dn_code = dn_item.get("item_code", "")
        dn_name = dn_item.get("item_name", "")
        if not _find_matching_item(po_items, dn_code, dn_name):
            all_matched = False
            results.append({
                "item_code": dn_code,
                "item_name": dn_name,
                "status": "🔴 Sai lệch",
                "checks": {
                    "unexpected_item": {
                        "source_a": "PO: Không có",
                        "source_b": f"DN: Có ({dn_item.get('quantity', '?')} đơn vị)",
                        "match": False,
                        "note": "Hàng giao không có trong đơn đặt hàng → từ chối"
                    }
                }
            })

    matched_count = sum(1 for r in results if "🟢" in r["status"])
    mismatched_count = len(results) - matched_count

    report = {
        "match_summary": {
            "status": "🟢 ALL MATCHED — Chấp nhận thanh toán" if all_matched else "🔴 MISMATCH DETECTED — Cần xem xét",
            "total_items": len(results),
            "matched": matched_count,
            "mismatched": mismatched_count
        },
        "document_refs": {
            "po_number": po_data.get("po_number", "N/A"),
            "dn_number": dn_data.get("dn_number", "N/A"),
            "inv_number": inv_data.get("inv_number", "N/A")
        },
        "details": results,
        "recommendation": (
            "✅ Chấp nhận thanh toán — Tất cả chứng từ khớp nhau."
            if all_matched else
            f"❌ Từ chối thanh toán — Phát hiện {mismatched_count} sai lệch. Cần liên hệ nhà cung cấp để đối chiếu."
        )
    }

    return json.dumps(report, ensure_ascii=False, indent=2)


def generate_report_summary(match_report_json: str) -> str:
    """
    Generate a human-readable summary from the match report.

    Args:
        match_report_json: JSON string of the match report

    Returns:
        Human-readable summary string in Vietnamese
    """
    report = _safe_parse_json(match_report_json)
    summary = report.get("match_summary", {})
    details = report.get("details", [])

    lines = []
    lines.append("=" * 60)
    lines.append("  BÁO CÁO ĐỐI SOÁT 3 CHIỀU (3-WAY MATCH REPORT)")
    lines.append("=" * 60)
    lines.append("")

    doc_refs = report.get("document_refs", {})
    lines.append(f"  PO: {doc_refs.get('po_number', 'N/A')}")
    lines.append(f"  DN: {doc_refs.get('dn_number', 'N/A')}")
    lines.append(f"  INV: {doc_refs.get('inv_number', 'N/A')}")
    lines.append("")
    lines.append(f"  Trạng thái: {summary.get('status', 'N/A')}")
    lines.append(f"  Tổng mặt hàng: {summary.get('total_items', 0)}")
    lines.append(f"  Khớp: {summary.get('matched', 0)} | Sai lệch: {summary.get('mismatched', 0)}")
    lines.append("")
    lines.append("-" * 60)

    for item in details:
        lines.append(f"\n  [{item['status']}] {item['item_code']} — {item['item_name']}")
        for check_name, check in item.get("checks", {}).items():
            icon = "✓" if check["match"] else "✗"
            lines.append(f"    {icon} {check_name}: {check['source_a']} vs {check['source_b']}")
            if check.get("note"):
                lines.append(f"      → {check['note']}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"  {report.get('recommendation', '')}")
    lines.append("=" * 60)

    return "\n".join(lines)
