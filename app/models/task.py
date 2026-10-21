"""Request and scheduling data models."""

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    task_id: str
    compute_units: float = Field(gt=0)
    max_latency_ms: float = Field(gt=0)


class TaskResult(BaseModel):
    task_id: str
    target: str
    success: bool
    network_latency_ms: float
    compute_duration_ms: float
    total_latency_ms: float
    deadline_met: bool
