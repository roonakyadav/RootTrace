from __future__ import annotations

from typing import Optional

from agents.base import Agent
from env.core import IncidentEnv
from env.counterfactual import CounterfactualEvaluator
from env.grader import IncidentGrader
from env.tasks import get_task
from evaluation.trajectory import EpisodeTrace, TraceStep
from models.schemas import Task


class EpisodeRunner:
    def __init__(
        self,
        grader: Optional[IncidentGrader] = None,
        counterfactual_evaluator: Optional[CounterfactualEvaluator] = None,
    ) -> None:
        self.grader = grader or IncidentGrader()
        self.counterfactual_evaluator = counterfactual_evaluator or CounterfactualEvaluator()

    def run(
        self,
        task: Task | str,
        agent: Agent,
        seed: int = 42,
        analyze_counterfactuals: bool = False,
    ) -> EpisodeTrace:
        resolved_task = get_task(task) if isinstance(task, str) else task
        if resolved_task is None:
            raise ValueError(f"Unknown task: {task}")

        agent.reset(seed)
        env = IncidentEnv(resolved_task, seed=seed)
        trace = EpisodeTrace(
            task_id=resolved_task.id,
            agent_name=agent.name,
            seed=seed,
        )

        while not env.runtime.is_done:
            state = env.state()
            action = agent.act(state)

            local_regret = None
            best_counterfactual_reward = None
            if analyze_counterfactuals:
                counterfactuals = self.counterfactual_evaluator.evaluate(
                    env,
                    chosen_action=action,
                )
                local_regret = self.counterfactual_evaluator.regret(
                    action,
                    counterfactuals,
                )
                best_counterfactual_reward = counterfactuals[0].reward

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
                    local_regret=local_regret,
                    best_counterfactual_reward=best_counterfactual_reward,
                )
            )

            if result["done"]:
                break

            if env.runtime.time_step >= env.max_steps:
                break

        trace.result = self.grader.grade_episode(env.state(), resolved_task)
        return trace
