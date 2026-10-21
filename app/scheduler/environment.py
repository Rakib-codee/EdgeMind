"""Dynamic node-state simulation.

Models time-varying network latency, CPU load, and queue length for
each node. States evolve via a mean-reverting random walk, so
experiments can reproduce latency spikes, overload, and congestion
without real infrastructure.
"""

import random
from dataclasses import dataclass, field

from app.scheduler.nodes import NodeProfile

MIN_LOAD_FACTOR = 0.3
MAX_LOAD_FACTOR = 2.0


@dataclass
class NodeState:
    profile: NodeProfile
    network_latency_ms: float
    load_factor: float = 1.0
    queue_length: int = 0

    @property
    def name(self) -> str:
        return self.profile.name

    @property
    def compute_rate(self) -> float:
        """Effective compute rate under current load."""
        return self.profile.compute_rate / max(self.load_factor, 1e-6)

    @classmethod
    def steady(cls, profile: NodeProfile) -> "NodeState":
        return cls(
            profile=profile,
            network_latency_ms=profile.network_latency_ms,
        )


class DynamicEnvironment:
    """Evolves node states over simulated time steps."""

    def __init__(
        self,
        profiles: tuple[NodeProfile, ...],
        rng: random.Random | None = None,
    ):
        self.rng = rng or random.Random(0)
        self.time_ms = 0.0
        self._states = {
            p.name: NodeState.steady(p) for p in profiles
        }

    def observe(self, name: str) -> NodeState:
        return self._states[name]

    def states(self) -> list[NodeState]:
        return list(self._states.values())

    def enqueue(self, name: str) -> None:
        self._states[name].queue_length += 1

    def dequeue(self, name: str) -> None:
        state = self._states[name]
        state.queue_length = max(0, state.queue_length - 1)

    def tick(self, steps: int = 1, step_ms: float = 100.0) -> None:
        """Advance simulated time and evolve every node's state."""
        for _ in range(steps):
            self.time_ms += step_ms
            for state in self._states.values():
                self._evolve(state)

    def _evolve(self, state: NodeState) -> None:
        # Mean-reverting network latency with noise (latency spikes).
        baseline = state.profile.network_latency_ms
        pull = 0.1 * (baseline - state.network_latency_ms)
        noise = self.rng.gauss(0, max(baseline * 0.2, 0.5))
        state.network_latency_ms = max(0.0, state.network_latency_ms + pull + noise)

        # Load factor random walk, clamped to a plausible range.
        drift = self.rng.gauss(0, 0.08)
        state.load_factor = min(
            MAX_LOAD_FACTOR,
            max(MIN_LOAD_FACTOR, state.load_factor + drift),
        )
