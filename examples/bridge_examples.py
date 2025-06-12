"""
Examples demonstrating the ZMCP bridge module.

This file contains examples of:
1. Converting an MCP tool to an A2A agent
2. Converting an A2A agent to MCP tools
"""
import asyncio
import json
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zmcp.core.mcp import Tool as MCPTool, TextContent
from zmcp.a2a.types import AgentCard, AgentSkill
from zmcp.bridge.mcp_to_a2a import MCPToolToA2AAgent
from zmcp.bridge.a2a_to_mcp import A2AAgentToMCPTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def calculator_handler(**kwargs):
    """A simple calculator handler for demonstration."""
    try:
        expression = kwargs.get("expression", "")
        # WARNING: eval is used for demonstration only. Never use eval in production code!
        result = eval(expression)
        return [TextContent(type="text", text=f"Result: {result}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def create_calculator_tool():
    """Create a simple calculator MCP tool."""
    return MCPTool(
        name="calculator",
        description="A simple calculator tool",
        handler=calculator_handler,
        input_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression to calculate"
                }
            },
            "required": ["expression"]
        }
    )


async def example_mcp_to_a2a():
    """Example of converting an MCP tool to an A2A agent."""
    logger.info("=== MCP Tool to A2A Agent Example ===")

    # Create an MCP tool
    calculator_tool = create_calculator_tool()
    logger.info(f"Created MCP tool: {calculator_tool.name}")

    # Convert to A2A agent
    bridge = MCPToolToA2AAgent(calculator_tool)
    logger.info("Created bridge from MCP tool to A2A agent")

    # Get the agent card
    agent_card = bridge.create_agent_card()
    logger.info(f"Agent card: {agent_card.name}")
    logger.info(f"Agent skills: {[skill.id for skill in agent_card.skills]}")

    # Create a FastAPI app
    app = bridge.create_app()
    logger.info("Created FastAPI app for the A2A agent")

    # In a real application, you would run the app with:
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    logger.info("To run the app: uvicorn examples.bridge_examples:app --host 0.0.0.0 --port 8000")


async def example_a2a_to_mcp():
    """Example of converting an A2A agent to MCP tools."""
    logger.info("\n=== A2A Agent to MCP Tool Example ===")

    # Create an agent card
    agent_card = AgentCard(
        name="Math Agent",
        description="An agent that can do math",
        url="/agent",
        version="1.0.0",
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain"],
        skills=[
            AgentSkill(
                id="calculate",
                name="Calculate",
                description="Calculate a math expression",
                tags=["math"]
            ),
            AgentSkill(
                id="convert",
                name="Convert",
                description="Convert between units",
                tags=["math"]
            )
        ],
        capabilities={
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        }
    )
    logger.info(f"Created agent card: {agent_card.name}")

    # Create the bridge
    # Note: In a real application, you would connect to an actual A2A agent
    bridge = A2AAgentToMCPTool(agent_card)
    logger.info("Created bridge from A2A agent to MCP tools")

    # Get the MCP tools
    tools = bridge.get_tools()
    logger.info(f"Created {len(tools)} MCP tools: {[tool.name for tool in tools]}")

    # In a real application, you would use these tools with an MCP client
    logger.info("These tools can now be used with an MCP client")

    # Clean up
    await bridge.close()


async def main():
    """Run all examples."""
    await example_mcp_to_a2a()
    await example_a2a_to_mcp()


if __name__ == "__main__":
    asyncio.run(main())
