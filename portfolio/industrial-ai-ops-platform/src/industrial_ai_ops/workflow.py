from __future__ import annotations

import asyncio
from dataclasses import dataclass
from .models import IndustrialEvent, RuleDecision, TaskCallback


@dataclass
class WorkflowTask:
    task_id: str
    event_id: str
    status: str
    severity: str


class InMemoryTaskCenter:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._tasks: dict[str, WorkflowTask] = {}
        self._event_to_task: dict[str, str] = {}
        self._callbacks: set[str] = set()

    async def create_task(self, event: IndustrialEvent, decision: RuleDecision) -> WorkflowTask:
        async with self._lock:
            existing_id = self._event_to_task.get(event.event_id)
            if existing_id:
                return self._tasks[existing_id]
            task_id = f"task-{len(self._tasks) + 1:04d}"
            task = WorkflowTask(task_id, event.event_id, "open", decision.severity.value)
            self._tasks[task_id] = task
            self._event_to_task[event.event_id] = task_id
            return task

    async def apply_callback(self, callback: TaskCallback) -> bool:
        async with self._lock:
            if callback.callback_id in self._callbacks:
                return False
            task = self._tasks.get(callback.task_id)
            if task is None:
                raise KeyError(callback.task_id)
            task.status = callback.status
            self._callbacks.add(callback.callback_id)
            return True
