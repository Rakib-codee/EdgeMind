"""Request and scheduling data models."""

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    task_id: str
    compute_units: float = Field(gt=0)
    max_latency_ms: float = Field(gt=0)
