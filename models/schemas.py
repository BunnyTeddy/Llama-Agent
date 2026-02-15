"""
Pydantic data models for the 3-Way Matcher Agent.
Defines structured schemas for Purchase Order, Delivery Note, Invoice,
and the cross-reference match results.
"""

from pydantic import BaseModel, Field
from typing import Optional


class LineItem(BaseModel):
    """A single line item from any document (PO, DN, or Invoice)."""
    item_code: str = Field(description="Mã hàng / Item code")
    item_name: str = Field(description="Tên hàng / Item name")
    quantity: float = Field(description="Số lượng / Quantity")
    unit: Optional[str] = Field(default=None, description="Đơn vị tính / Unit (e.g., 'kiện', 'cái')")
    unit_price: Optional[float] = Field(default=None, description="Đơn giá / Unit price")
    total: Optional[float] = Field(default=None, description="Thành tiền / Line total")


class PurchaseOrder(BaseModel):
    """Structured data extracted from a Purchase Order PDF."""
    po_number: str = Field(description="Số PO / PO number")
    date: Optional[str] = Field(default=None, description="Ngày PO / PO date")
    supplier: Optional[str] = Field(default=None, description="Nhà cung cấp / Supplier name")
    items: list[LineItem] = Field(description="Danh sách hàng hóa / List of line items")
    grand_total: Optional[float] = Field(default=None, description="Tổng cộng / Grand total")


class DeliveryNote(BaseModel):
    """Structured data extracted from a Delivery Note PDF."""
    dn_number: str = Field(description="Số phiếu giao / Delivery note number")
    date: Optional[str] = Field(default=None, description="Ngày giao / Delivery date")
    items: list[LineItem] = Field(description="Danh sách hàng giao / List of delivered items")
    notes: Optional[str] = Field(default=None, description="Ghi chú / Notes")


class Invoice(BaseModel):
    """Structured data extracted from an Invoice PDF."""
    inv_number: str = Field(description="Số hóa đơn / Invoice number")
    date: Optional[str] = Field(default=None, description="Ngày hóa đơn / Invoice date")
    items: list[LineItem] = Field(description="Danh sách hàng hóa / List of invoiced items")
    subtotal: Optional[float] = Field(default=None, description="Tổng trước thuế / Subtotal")
    vat_rate: Optional[float] = Field(default=None, description="Thuế suất VAT / VAT rate (%)")
    vat_amount: Optional[float] = Field(default=None, description="Tiền thuế VAT / VAT amount")
    grand_total: Optional[float] = Field(default=None, description="Tổng cộng / Grand total")


class FieldCheck(BaseModel):
    """Result of checking a single field between two documents."""
    source_a: str = Field(description="Giá trị từ document A")
    source_b: str = Field(description="Giá trị từ document B")
    match: bool = Field(description="Có khớp không / Is it a match?")
    note: Optional[str] = Field(default=None, description="Ghi chú / Note about mismatch")


class ItemMatchResult(BaseModel):
    """Match result for a single line item across all 3 documents."""
    item_code: str = Field(description="Mã hàng / Item code")
    item_name: str = Field(description="Tên hàng / Item name")
    status: str = Field(description="🟢 Khớp 100% or 🔴 Sai lệch")
    checks: dict[str, FieldCheck] = Field(description="Chi tiết kiểm tra từng trường")


class MatchReport(BaseModel):
    """Final match report for the 3-way reconciliation."""
    overall_status: str = Field(description="🟢 ALL MATCHED or 🔴 MISMATCH DETECTED")
    total_items: int = Field(description="Tổng số mặt hàng")
    matched_count: int = Field(description="Số mặt hàng khớp")
    mismatched_count: int = Field(description="Số mặt hàng sai lệch")
    details: list[ItemMatchResult] = Field(description="Chi tiết từng mặt hàng")
    recommendation: str = Field(description="Khuyến nghị: Chấp nhận thanh toán / Từ chối thanh toán")
