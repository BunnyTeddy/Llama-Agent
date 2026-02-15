"""
Llama Cloud Workflow Entry Point.
Exposes the AgentWorkflow for Llama Cloud's appserver to serve.

When deployed to Llama Cloud:
- The appserver discovers this file via llama_deploy.toml / pyproject.toml
- It wraps the workflow in a FastAPI server automatically
- Users interact via the Llama Cloud UI at cloud.llamaindex.ai
"""

import os
from dotenv import load_dotenv

# Load .env for local development; on Llama Cloud, env vars are set via dashboard
load_dotenv()

from agents.orchestrator import create_workflow

# The workflow instance that Llama Cloud's appserver will serve
workflow = create_workflow()
