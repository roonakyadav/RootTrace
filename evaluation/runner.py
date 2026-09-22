from __future__ import annotations

from typing import Optional

from agents.base import Agent
from env.core import IncidentEnv
from env.grader import IncidentGrader
from env.tasks import get_task
from evaluation.trajectory import EpisodeTrace, TraceStep
from models.schemas import Task


class EpisodeRunner:
    def __init__(self, grader: Optional[IncidentGrader] = None) -> None:
        self.grader = grader or IncidentGrader()

    def run(
        self,
        task: Task | str,
        agent: Agent,
        seed: int = 42,
    ) -> EpisodeTrace:
        resolved_task = get_task(task) if isinstance(task, str) else task
        if resolved_task is None:
            raise ValueError(f"Unknown task: {task}")

        agent.reset()
        env = IncidentEnv(resolved_task, seed=seed)
        trace = EpisodeTrace(
            task_id=resolved_task.id,
            agent_name=agent.name,
            seed=seed,
        )

        while not env.runtime.is_done:
            state = env.state()
            action = agent.act(state)
            result = env.step(action)

            trace.steps.append(
                TraceStep(
                    step=state.time_step + 1,
                    state_before=state.model_dump(),
                    action=action.model_dump(),
                    reward=float(result["reward"]),
                    state_after=result["state"].model_dump(),
                    done=bool(result["done"]),
                    info=result.get("info") or {},
                )
            )

            if result["done"]:
                break

            if env.runtime.time_step >= env.max_steps:
                break

        trace.result = self.grader.grade_episode(env.state(), resolved_task)
        return trace
