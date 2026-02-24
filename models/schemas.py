"""
Pydantic data models for the 3-Way Matcher Agent.
Defines structured schemas for Purchase Order, Delivery Note, Invoice,
and the cross-reference match results.
"""

from pydantic import BaseModel, Field
from typing import Optional


class LineItem(BaseModel):
    """A single line item from any document (PO, DN, or Invoice)."""
    item_code: str = Field(description="Item code")
    item_name: str = Field(description="Item name")
    quantity: float = Field(description="Quantity")
    unit: Optional[str] = Field(default=None, description="Unit of measure (e.g., 'box', 'piece')")
    unit_price: Optional[float] = Field(default=None, description="Unit price")
    total: Optional[float] = Field(default=None, description="Line total")


class PurchaseOrder(BaseModel):
    """Structured data extracted from a Purchase Order PDF."""
    po_number: str = Field(description="PO number")
    date: Optional[str] = Field(default=None, description="PO date")
    supplier: Optional[str] = Field(default=None, description="Supplier name")
    items: list[LineItem] = Field(description="List of line items")
    grand_total: Optional[float] = Field(default=None, description="Grand total")


class DeliveryNote(BaseModel):
    """Structured data extracted from a Delivery Note PDF."""
    dn_number: str = Field(description="Delivery note number")
    date: Optional[str] = Field(default=None, description="Delivery date")
    items: list[LineItem] = Field(description="List of delivered items")
    notes: Optional[str] = Field(default=None, description="Notes")


class Invoice(BaseModel):
    """Structured data extracted from an Invoice PDF."""
    inv_number: str = Field(description="Invoice number")
    date: Optional[str] = Field(default=None, description="Invoice date")
    items: list[LineItem] = Field(description="List of invoiced items")
    subtotal: Optional[float] = Field(default=None, description="Subtotal before tax")
    vat_rate: Optional[float] = Field(default=None, description="VAT rate (%)")
    vat_amount: Optional[float] = Field(default=None, description="VAT amount")
    grand_total: Optional[float] = Field(default=None, description="Grand total")


class FieldCheck(BaseModel):
    """Result of checking a single field between two documents."""
    source_a: str = Field(description="Value from document A")
    source_b: str = Field(description="Value from document B")
    match: bool = Field(description="Whether values match")
    note: Optional[str] = Field(default=None, description="Note about mismatch")


class ItemMatchResult(BaseModel):
    """Match result for a single line item across all 3 documents."""
    item_code: str = Field(description="Item code")
    item_name: str = Field(description="Item name")
    status: str = Field(description="🟢 Full Match or 🔴 Mismatch")
    checks: dict[str, FieldCheck] = Field(description="Per-field check details")


class MatchReport(BaseModel):
    """Final match report for the 3-way reconciliation."""
    overall_status: str = Field(description="🟢 ALL MATCHED or 🔴 MISMATCH DETECTED")
    total_items: int = Field(description="Total number of items")
    matched_count: int = Field(description="Number of matched items")
    mismatched_count: int = Field(description="Number of mismatched items")
    details: list[ItemMatchResult] = Field(description="Per-item details")
    recommendation: str = Field(description="Recommendation: Approve or Reject payment")
