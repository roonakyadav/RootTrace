from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from models.schemas import Action, ActionType, State


class ChatClient(Protocol):
    def chat(self, prompt: str) -> str:
        ...


class OpenAICompatibleClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
    ) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an incident-response agent. "
                        "Return only the requested JSON action."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return (response.choices[0].message.content or "").strip()


def build_prompt(state: State) -> str:
    services = "\n".join(
        f"- {service.name}: {service.status.value.upper()} "
        f"latency={service.latency:.1f}ms error_rate={service.error_rate:.3f}"
        for service in state.services
    )
    logs = "\n".join(f"- {log}" for log in state.logs[-8:]) or "- none"
    alerts = "\n".join(f"- {alert}" for alert in state.alerts) or "- none"
    evidence = "\n".join(
        f"- [{item.type.value}] {item.source} "
        f"reliability={item.reliability:.2f}: {item.content}"
        for item in state.evidence[-8:]
    ) or "- none"

    actions = ", ".join(
        action.value for action in ActionType if action != ActionType.UNKNOWN
    )

    return f"""ROOTTRACE INCIDENT

Step: {state.time_step}
System health: {state.system_health:.3f}
System stability: {state.system_stability:.3f}
System strain: {state.system_strain:.3f}

SERVICES
{services}

DEPENDENCIES
{json.dumps(state.dependencies, sort_keys=True)}

ALERTS
{alerts}

RECENT LOGS
{logs}

RECENT EVIDENCE
{evidence}

AVAILABLE ACTIONS
{actions}

Choose the safest useful next action. Prioritize root-cause diagnosis over symptom treatment.
Return ONLY valid JSON:
{{"action_type":"<action>","target":"<service or none>"}}
"""


def parse_action(text: str) -> Action:
    match = re.search(r"{.*}", text, re.DOTALL)
    if not match:
        raise ValueError("LLM response did not contain a JSON object")

    payload = json.loads(match.group(0))
    action_type = ActionType(payload.get("action_type", "unknown"))
    target = payload.get("target") or "none"
    if action_type == ActionType.UNKNOWN:
        raise ValueError("LLM returned an unknown action")
    return Action(action_type=action_type, target=target)


class LLMAgent:
    name = "llm"

    def __init__(
        self,
        client: ChatClient | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        if client is not None:
            self.client = client
            return

        key = api_key or os.getenv("LLM_API_KEY") or os.getenv("HF_TOKEN")
        url = (
            base_url
            or os.getenv("LLM_BASE_URL")
            or os.getenv("API_BASE_URL")
            or "https://router.huggingface.co/v1"
        )
        model_name = (
            model
            or os.getenv("LLM_MODEL")
            or os.getenv("MODEL_NAME")
            or "meta-llama/Llama-3.1-8B-Instruct"
        )

        if not key:
            raise ValueError(
                "LLM API key is required. Set LLM_API_KEY or HF_TOKEN."
            )

        self.client = OpenAICompatibleClient(
            api_key=key,
            base_url=url,
            model=model_name,
        )

    def reset(self, seed: int | None = None) -> None:
        return None

    def act(self, state: State) -> Action:
        return parse_action(self.client.chat(build_prompt(state)))
