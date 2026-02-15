# 🔄 3-Way Matcher — Supply Chain Reconciliation Agent

A **multi-agent AI system** that automatically cross-references 3 ERP documents (Purchase Order, Delivery Note, Invoice) to detect mismatches before payment approval.

Built with **LlamaIndex** + **Gemini 2.5 Pro** + **LlamaParse**.

## 🏗️ Architecture

```
User uploads 3 PDFs
        │
   ┌────┴────┐
   │ Orchestrator Agent │
   └─┬───┬───┬─┘
     │   │   │
  ┌──┘   │   └──┐
  ▼      ▼      ▼
PO     DN    Invoice
Parser Parser  Parser
  │      │      │
  ▼      ▼      ▼
LlamaParse (PDF → Markdown)
  │      │      │
  ▼      ▼      ▼
Gemini 2.5 Pro (Markdown → JSON)
  │      │      │
  └──┬───┴───┬──┘
     ▼       ▼
  Cross-Reference Engine
         │
         ▼
  Match Report (🟢/🔴)
```

## 📁 Project Structure

```
├── main.py                     # CLI entry point
├── agents/orchestrator.py      # Multi-agent workflow (4 agents)
├── tools/parser_tools.py       # LlamaParse PDF extraction
├── tools/matching_tools.py     # Cross-reference & report engine
├── models/schemas.py           # Pydantic data models
├── deployment/deploy.py        # Cloud deployment script
├── requirements.txt
└── .env.example                # API key template
```

## 🚀 Quick Start

### 1. Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your keys:
#   LLAMA_CLOUD_API_KEY=...  (from cloud.llamaindex.ai)
#   GOOGLE_API_KEY=...       (from aistudio.google.com/apikey)
```

### 3. Run

```bash
# Direct mode (faster, no multi-agent overhead)
python main.py \
  --po path/to/purchase_order.pdf \
  --dn path/to/delivery_note.pdf \
  --inv path/to/invoice.pdf \
  --direct

# Full agent orchestration mode
python main.py \
  --po path/to/purchase_order.pdf \
  --dn path/to/delivery_note.pdf \
  --inv path/to/invoice.pdf \
  --verbose
```

## 📊 Output Example

```
============================================================
  BÁO CÁO ĐỐI SOÁT 3 CHIỀU (3-WAY MATCH REPORT)
============================================================

  PO: PO-2026 | DN: DN-998 | INV: INV-554
  Trạng thái: 🔴 MISMATCH DETECTED
  Khớp: 0 | Sai lệch: 2

  [🔴] LT-01 — ThinkPad X1
    ✗ unit_price: PO $1,000 vs INV $1,050 (chênh $50)

  [🔴] MS-02 — Wireless Mouse
    ✗ quantity: PO 50 vs DN 45 (thiếu 5 đơn vị)

  ❌ Từ chối thanh toán — 2 sai lệch phát hiện
============================================================
```

## 🔑 Required API Keys

| Key | Source | Free Tier |
|-----|--------|-----------|
| `LLAMA_CLOUD_API_KEY` | [cloud.llamaindex.ai](https://cloud.llamaindex.ai) | 1,000 pages/day |
| `GOOGLE_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) | Free |

## 🛠️ Tech Stack

- **LlamaIndex** — Multi-agent framework (AgentWorkflow + FunctionAgent)
- **LlamaParse** — AI-native PDF table extraction
- **Gemini 2.5 Pro** — LLM for structured data extraction & agent reasoning
- **Pydantic** — Data validation & schemas

## ☁️ Cloud Deployment

This project can be deployed to [Llama Cloud](https://cloud.llamaindex.ai):

1. Push this repo to GitHub
2. Go to [cloud.llamaindex.ai](https://cloud.llamaindex.ai) → Deploy
3. Connect your GitHub repo
4. Set environment variables (`LLAMA_CLOUD_API_KEY`, `GOOGLE_API_KEY`)
5. Deploy!

## 📄 License

MIT
