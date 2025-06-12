"""
A2A Client

Implementation of a client for the A2A protocol.
"""
import json
import uuid
import logging
from typing import Dict, List, Optional, Any, Union, Callable, Awaitable

import httpx
from pydantic import ValidationError

from zmcp.a2a.types import (
    AgentCard, Message, Task, Role, Part, TextPart,
    SendMessageRequest, SendMessageResponse, GetTaskRequest, GetTaskResponse
)

logger = logging.getLogger(__name__)


class A2AClientError(Exception):
    """Base exception for A2A client errors."""
    pass


class A2AClient:
    """
    Client for interacting with A2A protocol agents.

    This client handles the communication with A2A agents, including:
    - Retrieving agent cards
    - Sending messages
    - Checking task status
    """

    def __init__(
        self,
        agent_url: str,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the A2A client.

        Args:
            agent_url: Base URL of the A2A agent
            timeout: Request timeout in seconds
            headers: Optional headers to include in requests
        """
        self.agent_url = agent_url.rstrip('/')
        self.timeout = timeout
        self.headers = headers or {}
        self.headers.setdefault("Content-Type", "application/json")
        self.client = httpx.AsyncClient(timeout=timeout, headers=self.headers)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_agent_card(self) -> AgentCard:
        """
        Retrieve the agent card from the A2A agent.

        Returns:
            AgentCard: The agent's card with capabilities and skills

        Raises:
            A2AClientError: If the request fails or returns invalid data
        """
        try:
            response = await self.client.get(self.agent_url)
            response.raise_for_status()

            agent_card_data = response.json()
            return AgentCard.model_validate(agent_card_data)

        except httpx.HTTPError as e:
            raise A2AClientError(f"HTTP error retrieving agent card: {e}")
        except ValidationError as e:
            raise A2AClientError(f"Invalid agent card format: {e}")
        except Exception as e:
            raise A2AClientError(f"Error retrieving agent card: {e}")

    async def send_message(
        self,
        text: str,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        configuration: Optional[Dict[str, Any]] = None
    ) -> Union[Task, Message]:
        """
        Send a text message to the A2A agent.

        Args:
            text: The message text to send
            context_id: Optional context ID for the conversation
            task_id: Optional task ID if continuing a task
            metadata: Optional metadata to include with the message
            configuration: Optional configuration for the agent

        Returns:
            Union[Task, Message]: The agent's response

        Raises:
            A2AClientError: If the request fails or returns invalid data
        """
        # Create a unique message ID
        message_id = str(uuid.uuid4())

        # Create a context ID if not provided
        if not context_id:
            context_id = str(uuid.uuid4())

        # Create the message
        message = Message(
            messageId=message_id,
            role=Role.user,
            parts=[TextPart(kind="text", text=text)],
            contextId=context_id,
            taskId=task_id
        )

        # Create the request
        request = SendMessageRequest(
            id=str(uuid.uuid4()),
            params={"message": message, "metadata": metadata, "configuration": configuration}
        )

        try:
            response = await self.client.post(
                f"{self.agent_url}/message/send",
                content=request.model_dump_json()
            )
            response.raise_for_status()

            # Parse the response
            response_data = response.json()
            send_message_response = SendMessageResponse.model_validate(response_data)

            # Check for error
            if hasattr(send_message_response.root, 'error'):
                error = send_message_response.root.error
                raise A2AClientError(f"Agent error: {error.code} - {error.message}")

            # Return the result
            return send_message_response.root.result

        except httpx.HTTPError as e:
            raise A2AClientError(f"HTTP error sending message: {e}")
        except ValidationError as e:
            raise A2AClientError(f"Invalid response format: {e}")
        except Exception as e:
            raise A2AClientError(f"Error sending message: {e}")

    async def get_task(self, task_id: str, metadata: Optional[Dict[str, Any]] = None) -> Task:
        """
        Get the status of a task.

        Args:
            task_id: The ID of the task to check
            metadata: Optional metadata to include with the request

        Returns:
            Task: The task information

        Raises:
            A2AClientError: If the request fails or returns invalid data
        """
        # Create the request
        request = GetTaskRequest(
            id=str(uuid.uuid4()),
            params={"id": task_id, "metadata": metadata}
        )

        try:
            response = await self.client.post(
                f"{self.agent_url}/tasks/get",
                content=request.model_dump_json()
            )
            response.raise_for_status()

            # Parse the response
            response_data = response.json()
            get_task_response = GetTaskResponse.model_validate(response_data)

            # Check for error
            if hasattr(get_task_response.root, 'error'):
                error = get_task_response.root.error
                raise A2AClientError(f"Agent error: {error.code} - {error.message}")

            # Return the result
            return get_task_response.root.result

        except httpx.HTTPError as e:
            raise A2AClientError(f"HTTP error getting task: {e}")
        except ValidationError as e:
            raise A2AClientError(f"Invalid response format: {e}")
        except Exception as e:
            raise A2AClientError(f"Error getting task: {e}")
