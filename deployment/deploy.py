"""
Deploy to Llama Cloud using llama-deploy.

Usage:
    # Option 1: Deploy via llamactl CLI
    pip install llama-deploy
    llamactl deploy create

    # Option 2: Deploy programmatically
    python deployment/deploy.py
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def deploy_workflow():
    """Deploy the 3-Way Matcher workflow using llama-deploy."""
    try:
        from llama_deploy import (
            deploy_workflow as ld_deploy,
            WorkflowServiceConfig,
            ControlPlaneConfig,
        )
    except ImportError:
        print("❌ llama-deploy not installed. Install with:")
        print("   pip install llama-deploy")
        return

    # Import from project root
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agents.orchestrator import create_workflow

    workflow = create_workflow()

    print("🚀 Deploying 3-Way Matcher to Llama Cloud...")

    await ld_deploy(
        workflow,
        workflow_config=WorkflowServiceConfig(
            host="0.0.0.0",
            port=8002,
            service_name="three-way-matcher",
        ),
        control_plane_config=ControlPlaneConfig(),
    )

    print("✅ Deployed! Service running.")
    print("   Endpoint: http://0.0.0.0:8002")


if __name__ == "__main__":
    asyncio.run(deploy_workflow())
