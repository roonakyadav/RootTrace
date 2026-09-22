from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from uuid import uuid4

from env.core import IncidentEnv
from env.grader import IncidentGrader


@dataclass
class Session:
    session_id: str
    task_id: str
    env: IncidentEnv
    grader: IncidentGrader


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._latest_by_task: dict[str, str] = {}
        self._lock = RLock()

    def create(self, task_id: str, env: IncidentEnv) -> Session:
        with self._lock:
            session_id = uuid4().hex
            session = Session(
                session_id=session_id,
                task_id=task_id,
                env=env,
                grader=IncidentGrader(),
            )
            self._sessions[session_id] = session
            self._latest_by_task[task_id] = session_id
            return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_latest_for_task(self, task_id: str) -> Session | None:
        with self._lock:
            session_id = self._latest_by_task.get(task_id)
            return self._sessions.get(session_id) if session_id else None

    def delete(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is None:
                return False
            if self._latest_by_task.get(session.task_id) == session_id:
                self._latest_by_task.pop(session.task_id, None)
            return True

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._latest_by_task.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)
