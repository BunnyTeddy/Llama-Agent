"""
PDF Parser Tools using LlamaParse.
Each tool extracts structured data from a specific document type (PO, DN, Invoice)
and returns a JSON string conforming to the Pydantic schemas.
"""

import json
import os
from llama_parse import LlamaParse
from llama_index.llms.gemini import Gemini


# Shared LLM instance for structured extraction
def _get_llm():
    return Gemini(model="models/gemini-2.5-pro", api_key=os.getenv("GOOGLE_API_KEY"), temperature=0)


def _get_parser():
    return LlamaParse(
        api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
        result_type="markdown",
    )


async def _parse_pdf_to_markdown(file_path: str) -> str:
    """Parse a PDF file to markdown using LlamaParse."""
    parser = _get_parser()
    documents = await parser.aload_data(file_path)
    return "\n\n".join([doc.text for doc in documents])


async def _extract_structured_data(markdown: str, document_type: str, schema_description: str) -> str:
    """Use LLM to convert markdown to structured JSON."""
    llm = _get_llm()

    prompt = f"""You are a document data extraction expert. Extract structured data from the following {document_type} document content (in markdown format).

IMPORTANT RULES:
- Extract ALL line items from the table(s) in the document
- For each item, extract: item_code, item_name, quantity, unit (if available), unit_price (if available), total (if available)
- Numbers should be numeric values (not strings), remove any thousand separators
- If a field is not found, use null
- Return ONLY valid JSON, no explanation

Expected JSON schema:
{schema_description}

Document content:
---
{markdown}
---

Return the JSON:"""

    response = await llm.acomplete(prompt)
    return response.text.strip()


async def parse_purchase_order(file_path: str) -> str:
    """
    Parse a Purchase Order PDF and extract structured data as JSON.

    Args:
        file_path: Absolute path to the PO PDF file

    Returns:
        JSON string with PO data: po_number, date, supplier, items[], grand_total
    """
    schema = """{
  "po_number": "string - PO number",
  "date": "string - PO date",
  "supplier": "string - Supplier name",
  "items": [
    {
      "item_code": "string",
      "item_name": "string",
      "quantity": number,
      "unit": "string or null",
      "unit_price": number,
      "total": number
    }
  ],
  "grand_total": number
}"""

    markdown = await _parse_pdf_to_markdown(file_path)
    result = await _extract_structured_data(markdown, "Purchase Order", schema)
    return result


async def parse_delivery_note(file_path: str) -> str:
    """
    Parse a Delivery Note PDF and extract structured data as JSON.

    Args:
        file_path: Absolute path to the Delivery Note PDF file

    Returns:
        JSON string with DN data: dn_number, date, items[], notes
    """
    schema = """{
  "dn_number": "string - Delivery note number",
  "date": "string - Delivery date",
  "items": [
    {
      "item_code": "string",
      "item_name": "string",
      "quantity": number,
      "unit": "string or null",
      "unit_price": null,
      "total": null
    }
  ],
  "notes": "string or null"
}"""

    markdown = await _parse_pdf_to_markdown(file_path)
    result = await _extract_structured_data(markdown, "Delivery Note", schema)
    return result


async def parse_invoice(file_path: str) -> str:
    """
    Parse an Invoice PDF and extract structured data as JSON.

    Args:
        file_path: Absolute path to the Invoice PDF file

    Returns:
        JSON string with Invoice data: inv_number, date, items[], subtotal, vat_rate, vat_amount, grand_total
    """
    schema = """{
  "inv_number": "string - Invoice number",
  "date": "string - Invoice date",
  "items": [
    {
      "item_code": "string",
      "item_name": "string",
      "quantity": number,
      "unit": "string or null",
      "unit_price": number,
      "total": number
    }
  ],
  "subtotal": number,
  "vat_rate": number,
  "vat_amount": number,
  "grand_total": number
}"""

    markdown = await _parse_pdf_to_markdown(file_path)
    result = await _extract_structured_data(markdown, "Invoice", schema)
    return result
