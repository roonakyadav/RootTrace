from __future__ import annotations

from typing import Callable, Dict

from agents.base import Agent
from agents.llm import LLMAgent
from agents.random_agent import RandomAgent
from agents.rule_based import DependencyAwareAgent


AgentFactory = Callable[[], Agent]


AGENTS: Dict[str, AgentFactory] = {
    "dependency-aware": DependencyAwareAgent,
    "random": RandomAgent,
    "llm": LLMAgent,
}


def register_agent(name: str, factory: AgentFactory) -> None:
    if not name.strip():
        raise ValueError("Agent name cannot be empty")
    if name in AGENTS:
        raise ValueError(f"Agent already registered: {name}")
    AGENTS[name] = factory


def create_agent(name: str) -> Agent:
    try:
        return AGENTS[name]()
    except KeyError as exc:
        available = ", ".join(sorted(AGENTS))
        raise ValueError(f"Unknown agent {name!r}. Available: {available}") from exc


def available_agents():
    return tuple(sorted(AGENTS))
