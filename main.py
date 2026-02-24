"""
3-Way Matcher Agent — Main Entry Point
Supply Chain Reconciliation: PO ↔ Delivery Note ↔ Invoice

Usage:
    python main.py --po path/to/po.pdf --dn path/to/dn.pdf --inv path/to/invoice.pdf
    python main.py  (interactive mode)
"""

import asyncio
import argparse
import json
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Validate API keys
def _check_api_keys():
    missing = []
    if not os.getenv("LLAMA_CLOUD_API_KEY"):
        missing.append("LLAMA_CLOUD_API_KEY")
    if not os.getenv("GOOGLE_API_KEY"):
        missing.append("GOOGLE_API_KEY")
    if missing:
        print("❌ Missing API keys! Please set in .env file:")
        for key in missing:
            print(f"   {key}=your_key_here")
        print(f"\n   Copy .env.example to .env and fill in your keys.")
        sys.exit(1)


async def run_matching(po_path: str, dn_path: str, inv_path: str, verbose: bool = False):
    """Run the 3-way matching workflow."""

    # Validate files exist
    for label, path in [("PO", po_path), ("DN", dn_path), ("Invoice", inv_path)]:
        if not os.path.exists(path):
            print(f"❌ File not found: {label} = {path}")
            sys.exit(1)

    print("=" * 60)
    print("  🔄 3-WAY MATCHER — Supply Chain Reconciliation")
    print("=" * 60)
    print(f"\n  📄 PO:      {os.path.basename(po_path)}")
    print(f"  📄 DN:      {os.path.basename(dn_path)}")
    print(f"  📄 Invoice: {os.path.basename(inv_path)}")
    print(f"\n  ⏳ Processing... (may take 30-60 seconds)\n")

    from agents.orchestrator import create_workflow

    workflow = create_workflow()

    prompt = (
        f"Please perform a 3-way match reconciliation on these documents:\n"
        f"- Purchase Order (PO): {po_path}\n"
        f"- Delivery Note (DN): {dn_path}\n"
        f"- Invoice (INV): {inv_path}\n\n"
        f"Parse each document, then cross-reference and generate the match report."
    )

    handler = workflow.run(user_msg=prompt)

    if verbose:
        from llama_index.core.agent.workflow import (
            AgentOutput,
            ToolCall,
            ToolCallResult,
        )
        async for ev in handler.stream_events():
            if isinstance(ev, ToolCall):
                print(f"  🔧 Calling: {ev.tool_name}")
            elif isinstance(ev, ToolCallResult):
                print(f"  ✅ {ev.tool_name} completed")

    result = await handler

    print("\n" + "=" * 60)
    print("  📊 MATCH RESULTS")
    print("=" * 60)
    print(f"\n{result}")

    return result


async def run_direct_matching(po_path: str, dn_path: str, inv_path: str):
    """
    Run matching directly without multi-agent orchestration.
    Simpler, faster, and more reliable for straightforward use cases.
    """

    # Validate files exist
    for label, path in [("PO", po_path), ("DN", dn_path), ("Invoice", inv_path)]:
        if not os.path.exists(path):
            print(f"❌ File not found: {label} = {path}")
            sys.exit(1)

    print("=" * 60)
    print("  🔄 3-WAY MATCHER — Supply Chain Reconciliation (Direct Mode)")
    print("=" * 60)
    print(f"\n  📄 PO:      {os.path.basename(po_path)}")
    print(f"  📄 DN:      {os.path.basename(dn_path)}")
    print(f"  📄 Invoice: {os.path.basename(inv_path)}")
    print(f"\n  ⏳ Processing...\n")

    from tools.parser_tools import parse_purchase_order, parse_delivery_note, parse_invoice
    from tools.matching_tools import cross_reference, generate_report_summary

    # Step 1: Parse all 3 documents in parallel
    print("  📝 Step 1/3: Parsing PDFs with LlamaParse...")
    po_json, dn_json, inv_json = await asyncio.gather(
        parse_purchase_order(po_path),
        parse_delivery_note(dn_path),
        parse_invoice(inv_path),
    )

    print("  📝 Step 2/3: Extracted data:")
    print(f"    PO:  {po_json[:100]}...")
    print(f"    DN:  {dn_json[:100]}...")
    print(f"    INV: {inv_json[:100]}...")

    # Step 2: Cross-reference
    print("\n  🔀 Step 3/3: Cross-referencing...")
    report_json = cross_reference(po_json, dn_json, inv_json)

    # Step 3: Generate summary
    summary = generate_report_summary(report_json)

    print("\n" + summary)
    print("\n📋 Raw JSON Report:")
    print(report_json)

    # Save report to file
    report_path = os.path.join(os.path.dirname(po_path), "match_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_json)
    print(f"\n💾 Report saved to: {report_path}")

    return report_json


def main():
    parser = argparse.ArgumentParser(
        description="3-Way Matcher — Supply Chain Document Reconciliation Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --po po.pdf --dn delivery.pdf --inv invoice.pdf
  python main.py --po po.pdf --dn delivery.pdf --inv invoice.pdf --direct
  python main.py --po po.pdf --dn delivery.pdf --inv invoice.pdf --verbose
        """
    )
    parser.add_argument("--po", required=True, help="Path to Purchase Order PDF")
    parser.add_argument("--dn", required=True, help="Path to Delivery Note PDF")
    parser.add_argument("--inv", required=True, help="Path to Invoice PDF")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed agent activity")
    parser.add_argument(
        "--direct", "-d", action="store_true",
        help="Use direct mode (no multi-agent orchestration, faster and simpler)"
    )

    args = parser.parse_args()

    _check_api_keys()

    if args.direct:
        asyncio.run(run_direct_matching(args.po, args.dn, args.inv))
    else:
        asyncio.run(run_matching(args.po, args.dn, args.inv, verbose=args.verbose))


if __name__ == "__main__":
    main()
