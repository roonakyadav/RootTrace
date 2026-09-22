from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.session import SessionStore
from env.core import IncidentEnv
from env.grader import IncidentGrader
from env.tasks import TASKS, get_task
from models.schemas import Action, ActionType, EpisodeResult, State, StepResult


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("========================================")
    print("ROOTTRACE SERVER STARTED")
    print("PORT: 7860")
    print("========================================")
    yield


app = FastAPI(
    title="RootTrace Agent Evaluation Environment",
    version="1.0.0",
    lifespan=lifespan,
)

session_store = SessionStore()


class ResetRequest(BaseModel):
    task_id: Optional[str] = "easy"
    seed: Optional[int] = 42


class StepRequest(BaseModel):
    action_type: str
    target: Optional[str] = None
    task_id: Optional[str] = "easy"
    session_id: Optional[str] = None


TASK_ALIASES = {
    "easy": "easy-auth-down",
    "medium": "medium-payments-degraded",
    "hard": "hard-cascading-failure",
    "deployment": "hard-bad-deployment",
}


def _resolve_session(
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
):
    if session_id:
        session = session_store.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    resolved_task = task_id or "easy"
    session = session_store.get_latest_for_task(resolved_task)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Call /reset first.",
        )
    return session


def _reset_task(task_id: Optional[str], seed: Optional[int]) -> Dict[str, Any]:
    requested = task_id or "easy"
    actual_id = TASK_ALIASES.get(requested.lower(), requested)
    task = get_task(actual_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Task not found",
                "invalid_id": requested,
                "available_tasks": [task.id for task in TASKS],
                "aliases": list(TASK_ALIASES.keys()),
            },
        )

    env = IncidentEnv(task, seed=seed if seed is not None else 42)
    session = session_store.create(actual_id, env)
    return {
        "session_id": session.session_id,
        "task_id": actual_id,
        "state": env.get_state().model_dump(),
    }


@app.get("/tasks")
async def list_tasks():
    return {
        "available_ids": [task.id for task in TASKS],
        "aliases": TASK_ALIASES,
        "tasks": TASKS,
    }


@app.post("/reset")
async def reset_generic(request: Optional[ResetRequest] = None):
    request = request or ResetRequest()
    return _reset_task(request.task_id, request.seed)


@app.post("/reset/{task_id}")
async def reset(task_id: str, seed: Optional[int] = Query(42)):
    return _reset_task(task_id, seed)


@app.post("/step", response_model=StepResult)
async def step_generic(request: StepRequest):
    session = _resolve_session(request.session_id, request.task_id)
    env = session.env

    if env.runtime.is_done:
        raise HTTPException(
            status_code=400,
            detail="Episode already terminated. Please reset.",
        )

    try:
        action_type = ActionType(request.action_type)
    except ValueError:
        action_type = ActionType.UNKNOWN

    action = Action(
        action_type=action_type,
        target=request.target or "none",
    )
    result = env.step(action)
    return StepResult(
        state=result["state"],
        reward=result["reward"],
        done=result["done"],
        info=result.get("info"),
    )


@app.post("/step/{task_id}", response_model=StepResult)
async def step(task_id: str, action: Action):
    session = _resolve_session(task_id=task_id)
    return await step_generic(
        StepRequest(
            action_type=action.action_type.value,
            target=action.target,
            task_id=task_id,
            session_id=session.session_id,
        )
    )


@app.get("/state")
async def get_current_state(
    session_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query("easy"),
):
    session = _resolve_session(session_id=session_id, task_id=task_id)
    return session.env.state().model_dump()


@app.get("/state/{task_id}")
async def get_state(task_id: str):
    return _resolve_session(task_id=task_id).env.get_state().model_dump()


@app.get("/validate")
async def validate():
    results = {}
    for task in TASKS:
        try:
            env = IncidentEnv(task, seed=42)
            result = env.step(
                Action(
                    action_type=ActionType.CHECK_LOGS,
                    target=task.initial_services[0].name,
                )
            )
            results[task.id] = "ok" if result["reward"] is not None else "fail"
        except Exception as exc:
            results[task.id] = f"error: {exc}"
    return {"validation": results}


@app.post("/grade/{task_id}", response_model=EpisodeResult)
async def grade(task_id: str):
    session = _resolve_session(task_id=task_id)
    return session.grader.grade_episode(
        session.env.get_state(),
        session.env.task,
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/trajectory/{task_id}")
async def get_trajectory(task_id: str):
    session = _resolve_session(task_id=task_id)
    env = session.env

    return {
        "session_id": session.session_id,
        "steps": [
            {
                "action": item["action"].model_dump(),
                "state_before": item["state_before"].model_dump(),
                "state_after": item["state_after"].model_dump(),
                "reward": item["reward"],
                "reward_info": item["reward_info"],
            }
            for item in env.runtime.state_history
        ],
        "total_steps": len(env.runtime.state_history),
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if not session_store.delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "session_id": session_id}


@app.get("/baseline")
async def run_baseline():
    from agents.rule_based import DependencyAwareAgent

    agent = DependencyAwareAgent()
    results = {}
    total_score = 0.0

    for task in TASKS[:3]:
        env = IncidentEnv(task, seed=42)
        agent.reset()

        while not env.runtime.is_done and env.runtime.time_step < env.max_steps:
            result = env.step(agent.act(env.get_state()))
            if result["done"]:
                break

        episode = IncidentGrader().grade_episode(env.get_state(), env.task)
        results[task.id] = round(episode.final_score, 3)
        total_score += episode.final_score

    average_score = total_score / len(results) if results else 0.0
    return {
        "tasks": results,
        "average_score": round(average_score, 3),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
