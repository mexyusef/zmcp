"""
A2A Agent Executor

Base class for implementing agent logic in A2A servers.
"""
from abc import ABC, abstractmethod
import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from zmcp.a2a.types import (
    Message,
    Task,
    TaskState,
    TaskStatus,
    Role,
    TextPart,
)

logger = logging.getLogger(__name__)


class EventQueue:
    """Queue for publishing events from agent execution."""

    def __init__(self):
        self._queue = asyncio.Queue()

    async def publish(self, event: Union[Task, Message]):
        """Publish an event to the queue."""
        await self._queue.put(event)

    async def get(self) -> Union[Task, Message]:
        """Get the next event from the queue."""
        return await self._queue.get()

    def task_done(self):
        """Mark a task as done."""
        self._queue.task_done()

    async def join(self):
        """Wait for all items in the queue to be processed."""
        await self._queue.join()


class RequestContext:
    """Context for an agent request."""

    def __init__(
        self,
        task_id: str,
        context_id: str,
        message: Optional[Message] = None,
        history: Optional[List[Message]] = None,
    ):
        self.task_id = task_id
        self.context_id = context_id
        self.message = message
        self.history = history or []

    @classmethod
    def create_new(cls, message: Message) -> 'RequestContext':
        """Create a new request context for a message."""
        task_id = str(uuid.uuid4())
        context_id = str(uuid.uuid4())

        # If the message doesn't have a task ID, set it
        if not message.taskId:
            message.taskId = task_id

        # If the message doesn't have a context ID, set it
        if not message.contextId:
            message.contextId = context_id

        return cls(
            task_id=task_id,
            context_id=context_id,
            message=message,
            history=[message],
        )


class AgentExecutor(ABC):
    """Agent Executor interface.

    Implementations of this interface contain the core logic of the agent,
    executing tasks based on requests and publishing updates to an event queue.
    """

    @abstractmethod
    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Execute the agent's logic for a given request context.

        The agent should read necessary information from the `context` and
        publish `Task` or `Message` events to the `event_queue`. This method should
        return once the agent's execution for this request is complete or
        yields control (e.g., enters an input-required state).

        Args:
            context: The request context containing the message, task ID, etc.
            event_queue: The queue to publish events to.
        """
        pass

    @abstractmethod
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Request the agent to cancel an ongoing task.

        The agent should attempt to stop the task identified by the task_id
        in the context and publish a `TaskStatusUpdateEvent` with state
        `TaskState.canceled` to the `event_queue`.

        Args:
            context: The request context containing the task ID to cancel.
            event_queue: The queue to publish the cancellation status update to.
        """
        pass

    def create_task_from_context(
        self,
        context: RequestContext,
        state: TaskState = TaskState.working,
        message: Optional[str] = None
    ) -> Task:
        """Create a Task object from a RequestContext.

        Args:
            context: The request context
            state: The task state
            message: Optional status message

        Returns:
            A Task object
        """
        status_message = None
        if message:
            status_message = Message(
                kind="message",
                messageId=str(uuid.uuid4()),
                role=Role.agent,
                parts=[TextPart(kind="text", text=message)],
                taskId=context.task_id,
                contextId=context.context_id,
            )

        status = TaskStatus(
            state=state,
            message=status_message,
        )

        return Task(
            kind="task",
            id=context.task_id,
            contextId=context.context_id,
            status=status,
            history=context.history,
        )

    def create_response_message(
        self,
        context: RequestContext,
        text: str,
    ) -> Message:
        """Create a response message.

        Args:
            context: The request context
            text: The response text

        Returns:
            A Message object
        """
        return Message(
            kind="message",
            messageId=str(uuid.uuid4()),
            role=Role.agent,
            parts=[TextPart(kind="text", text=text)],
            taskId=context.task_id,
            contextId=context.context_id,
        )
