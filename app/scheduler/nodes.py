"""Node profiles for simulated execution targets.

These values are development assumptions for a simulated environment,
not measurements of physical hardware.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeProfile:
    name: str
    network_latency_ms: float
    compute_rate: float  # compute units per ms


DEFAULT_NODES: tuple[NodeProfile, ...] = (
    NodeProfile(name="local", network_latency_ms=0, compute_rate=10),
    NodeProfile(name="edge", network_latency_ms=8, compute_rate=30),
    NodeProfile(name="cloud", network_latency_ms=35, compute_rate=100),
)
