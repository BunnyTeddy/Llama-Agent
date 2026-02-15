"""
Llama Cloud Workflow Entry Point.
This file exposes the AgentWorkflow for deployment to Llama Cloud.

When deployed, the workflow is accessible via HTTP API.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import create_workflow

# The workflow instance that Llama Cloud / llama-deploy will serve
workflow = create_workflow()
