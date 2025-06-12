"""
A2A Server Application

FastAPI application for serving A2A agents.
"""
import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from zmcp.a2a.server.agent_executor import AgentExecutor, EventQueue, RequestContext
from zmcp.a2a.types import (
    AgentCard,
    AgentSkill,
    Message,
    SendMessageRequest,
    SendMessageResponse,
    GetTaskRequest,
    GetTaskResponse,
    TaskIdParams,
    Task,
    TaskState,
    JSONRPCErrorResponse,
    JSONRPCError,
    Role,
)

logger = logging.getLogger(__name__)


def create_a2a_app(
    agent_executor: AgentExecutor,
    agent_name: str,
    agent_description: str,
    agent_version: str = "1.0.0",
    skills: Optional[List[AgentSkill]] = None,
) -> FastAPI:
    """Create a FastAPI application for an A2A agent.

    Args:
        agent_executor: The agent executor implementation
        agent_name: The name of the agent
        agent_description: The description of the agent
        agent_version: The version of the agent
        skills: Optional list of agent skills

    Returns:
        A FastAPI application
    """
    app = FastAPI(title=agent_name, description=agent_description)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create default skill if none provided
    if not skills:
        skills = [
            AgentSkill(
                id="general",
                name="General Assistant",
                description="General purpose assistant capabilities",
                tags=["assistant"],
            )
        ]

    # Create agent card
    agent_card = AgentCard(
        name=agent_name,
        description=agent_description,
        url="/",  # Will be updated with the actual URL
        version=agent_version,
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain"],
        skills=skills,
        capabilities={
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        },
    )

    # Store active tasks
    active_tasks: Dict[str, Task] = {}

    @app.get("/.well-known/agent.json")
    async def get_agent_card():
        """Return the agent card."""
        return agent_card

    @app.post("/")
    async def handle_jsonrpc(request: Request):
        """Handle JSON-RPC requests."""
        try:
            # Parse the request
            data = await request.json()

            # Check for required fields
            if "jsonrpc" not in data or data["jsonrpc"] != "2.0" or "method" not in data:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request",
                        },
                        "id": data.get("id"),
                    },
                )

            # Handle different methods
            method = data["method"]
            request_id = data.get("id")

            if method == "message/send":
                return await handle_send_message(data, request_id)
            elif method == "message/stream":
                return StreamingResponse(
                    handle_stream_message(data, request_id),
                    media_type="text/event-stream",
                )
            elif method == "tasks/get":
                return await handle_get_task(data, request_id)
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}",
                        },
                        "id": request_id,
                    },
                )

        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                    },
                    "id": None,
                },
            )
        except Exception as e:
            logger.exception(f"Error handling request: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                    },
                    "id": data.get("id") if "data" in locals() else None,
                },
            )

    async def handle_send_message(data: Dict[str, Any], request_id: Optional[str]):
        """Handle a send message request."""
        try:
            # Parse the request
            request = SendMessageRequest.model_validate(data)

            # Create a request context
            message = request.params.message
            context = RequestContext.create_new(message)

            # Create an event queue
            event_queue = EventQueue()

            # Execute the agent logic
            task = asyncio.create_task(agent_executor.execute(context, event_queue))

            # Wait for the first event
            event = await event_queue.get()
            event_queue.task_done()

            # Store the task if it's a Task event
            if isinstance(event, Task):
                active_tasks[event.id] = event

            # Return the event
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "result": event.model_dump(mode="json"),
                    "id": request_id,
                },
            )

        except ValidationError as e:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": "Invalid params",
                        "data": e.errors(),
                    },
                    "id": request_id,
                },
            )

    async def handle_stream_message(data: Dict[str, Any], request_id: Optional[str]):
        """Handle a streaming message request."""
        try:
            # Parse the request
            request = SendMessageRequest.model_validate(data)

            # Create a request context
            message = request.params.message
            context = RequestContext.create_new(message)

            # Create an event queue
            event_queue = EventQueue()

            # Execute the agent logic
            task = asyncio.create_task(agent_executor.execute(context, event_queue))

            # Stream events
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=60.0)
                    event_queue.task_done()

                    # Store the task if it's a Task event
                    if isinstance(event, Task):
                        active_tasks[event.id] = event

                    # Yield the event
                    yield json.dumps({
                        "jsonrpc": "2.0",
                        "result": event.model_dump(mode="json"),
                        "id": request_id,
                    }) + "\n\n"

                    # If the task is in a final state, stop streaming
                    if isinstance(event, Task) and event.status.state in [
                        TaskState.completed,
                        TaskState.canceled,
                        TaskState.failed,
                        TaskState.rejected,
                    ]:
                        break
                except asyncio.TimeoutError:
                    # No events for a while, check if the task is still running
                    if task.done():
                        break

        except ValidationError as e:
            yield json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "Invalid params",
                    "data": e.errors(),
                },
                "id": request_id,
            }) + "\n\n"
        except Exception as e:
            logger.exception(f"Error in streaming: {e}")
            yield json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                },
                "id": request_id,
            }) + "\n\n"

    async def handle_get_task(data: Dict[str, Any], request_id: Optional[str]):
        """Handle a get task request."""
        try:
            # Parse the request
            request = GetTaskRequest.model_validate(data)

            # Get the task ID
            task_id = request.params.id

            # Check if the task exists
            if task_id not in active_tasks:
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32001,
                            "message": "Task not found",
                        },
                        "id": request_id,
                    },
                )

            # Return the task
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "result": active_tasks[task_id].model_dump(mode="json"),
                    "id": request_id,
                },
            )

        except ValidationError as e:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": "Invalid params",
                        "data": e.errors(),
                    },
                    "id": request_id,
                },
            )

    return app
