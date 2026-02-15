"""
Worker and Orchestrator Agents for the 3-Way Matcher.
Uses LlamaIndex FunctionAgent + AgentWorkflow for multi-agent orchestration.
"""

import os
from llama_index.core.agent.workflow import FunctionAgent, AgentWorkflow
from llama_index.core.tools import FunctionTool
from llama_index.llms.gemini import Gemini
from tools.parser_tools import parse_purchase_order, parse_delivery_note, parse_invoice
from tools.matching_tools import cross_reference, generate_report_summary


def _get_llm():
    return Gemini(model="models/gemini-2.5-pro", api_key=os.getenv("GOOGLE_API_KEY"), temperature=0)


def create_workflow() -> AgentWorkflow:
    """Create the multi-agent workflow for 3-way matching."""

    llm = _get_llm()

    # ── Tool Definitions ──────────────────────────────────────────

    parse_po_tool = FunctionTool.from_defaults(
        async_fn=parse_purchase_order,
        name="parse_purchase_order",
        description="Parse a Purchase Order (PO) PDF file and extract structured data as JSON. Input: file_path (absolute path to PDF)."
    )

    parse_dn_tool = FunctionTool.from_defaults(
        async_fn=parse_delivery_note,
        name="parse_delivery_note",
        description="Parse a Delivery Note (DN) PDF file and extract structured data as JSON. Input: file_path (absolute path to PDF)."
    )

    parse_inv_tool = FunctionTool.from_defaults(
        async_fn=parse_invoice,
        name="parse_invoice",
        description="Parse an Invoice (INV) PDF file and extract structured data as JSON. Input: file_path (absolute path to PDF)."
    )

    cross_ref_tool = FunctionTool.from_defaults(
        fn=cross_reference,
        name="cross_reference",
        description=(
            "Perform 3-way cross-reference matching between PO, DN, and Invoice JSON data. "
            "Compares quantities, prices, and totals. Returns a JSON match report with 🟢/🔴 status. "
            "Inputs: po_json, dn_json, inv_json (all JSON strings from the parser tools)."
        )
    )

    report_tool = FunctionTool.from_defaults(
        fn=generate_report_summary,
        name="generate_report_summary",
        description=(
            "Generate a human-readable summary from the match report JSON. "
            "Input: match_report_json (the JSON string output from cross_reference tool)."
        )
    )

    # ── Agent Definitions ─────────────────────────────────────────

    po_agent = FunctionAgent(
        name="po_parser_agent",
        llm=llm,
        tools=[parse_po_tool],
        description="Specialist agent for parsing Purchase Order (PO) PDF files into structured JSON.",
        system_prompt=(
            "You are a Purchase Order parser agent. When given a PO PDF file path, "
            "use the parse_purchase_order tool to extract the data. "
            "Return the extracted JSON data. Do not modify the JSON output."
        ),
        can_handoff_to=["orchestrator"],
    )

    dn_agent = FunctionAgent(
        name="dn_parser_agent",
        llm=llm,
        tools=[parse_dn_tool],
        description="Specialist agent for parsing Delivery Note (DN) PDF files into structured JSON.",
        system_prompt=(
            "You are a Delivery Note parser agent. When given a DN PDF file path, "
            "use the parse_delivery_note tool to extract the data. "
            "Return the extracted JSON data. Do not modify the JSON output."
        ),
        can_handoff_to=["orchestrator"],
    )

    inv_agent = FunctionAgent(
        name="inv_parser_agent",
        llm=llm,
        tools=[parse_inv_tool],
        description="Specialist agent for parsing Invoice (INV) PDF files into structured JSON.",
        system_prompt=(
            "You are an Invoice parser agent. When given an Invoice PDF file path, "
            "use the parse_invoice tool to extract the data. "
            "Return the extracted JSON data. Do not modify the JSON output."
        ),
        can_handoff_to=["orchestrator"],
    )

    orchestrator = FunctionAgent(
        name="orchestrator",
        llm=llm,
        tools=[cross_ref_tool, report_tool],
        description="Main orchestrator that coordinates parsing and matching of PO, DN, and Invoice documents.",
        system_prompt=(
            "You are the 3-Way Matcher orchestrator. Your job is to coordinate the reconciliation "
            "of 3 supply chain documents: Purchase Order (PO), Delivery Note (DN), and Invoice (INV).\n\n"
            "WORKFLOW:\n"
            "1. You will receive file paths for 3 PDF documents (PO, DN, INV)\n"
            "2. Hand off each file to the appropriate parser agent:\n"
            "   - PO file → po_parser_agent\n"
            "   - DN file → dn_parser_agent\n"
            "   - INV file → inv_parser_agent\n"
            "3. Collect the JSON results from all 3 parser agents\n"
            "4. Use the cross_reference tool with all 3 JSON outputs\n"
            "5. Use generate_report_summary to create a readable report\n"
            "6. Present both the JSON match report and the human-readable summary\n\n"
            "IMPORTANT: Always process all 3 documents before doing the cross-reference."
        ),
        can_handoff_to=["po_parser_agent", "dn_parser_agent", "inv_parser_agent"],
    )

    # ── Workflow ──────────────────────────────────────────────────

    workflow = AgentWorkflow(
        agents=[orchestrator, po_agent, dn_agent, inv_agent],
        root_agent="orchestrator",
    )

    return workflow
