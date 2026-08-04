"""Parallel execution of independent specialist agents."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from agents.agent_result import AgentResult
from agents.specialists import SPECIALIST_REGISTRY
from agents.state import Intent

logger = logging.getLogger(__name__)

MAX_PARALLEL_SPECIALISTS = 5


def run_specialists_parallel(
    query: str,
    intent: Intent | None,
    agent_names: Iterable[str],
) -> list[AgentResult]:
    """Run selected specialists concurrently when safe."""
    names = [name for name in agent_names if name in SPECIALIST_REGISTRY]
    if not names:
        return []

    if len(names) == 1:
        agent = SPECIALIST_REGISTRY[names[0]]
        return [agent.run(query, intent)]

    results: list[AgentResult] = []
    with ThreadPoolExecutor(max_workers=min(len(names), MAX_PARALLEL_SPECIALISTS)) as pool:
        futures = {
            pool.submit(SPECIALIST_REGISTRY[name].run, query, intent): name for name in names
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                logger.warning("Specialist %s failed: %s", name, exc)
                results.append(
                    AgentResult(
                        agent=name,
                        confidence=0.0,
                        warnings=[str(exc)],
                    )
                )

    order = {name: index for index, name in enumerate(names)}
    results.sort(key=lambda item: order.get(item.agent, 99))
    return results
