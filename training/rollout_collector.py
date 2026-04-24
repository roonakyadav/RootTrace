import os
import json
import copy
import requests
from typing import List, Dict, Any, Optional
import openai
from dotenv import load_dotenv

load_dotenv()

# --- Environment configuration ---
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")
MAX_STEPS = 15

# Safety check for API key
if not API_KEY:
    raise RuntimeError("GROQ_API_KEY not found in environment variables")

# Initialize OpenAI client
try:
    from openai import OpenAI
    client = OpenAI(
        api_key=API_KEY,
        base_url=API_BASE_URL
    )
except ImportError:
    client = None


def test_llm_connection():
    if not client:
        print("[ERROR] OpenAI client not initialized")
        return

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Reply ONLY with OK"}
            ],
            temperature=0.0
        )

        output = response.choices[0].message.content.strip()
        print(f"[SUCCESS] LLM Response: {output}")

    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")


# --- Valid actions ---
VALID_ACTIONS = [
    "restart_service", "rollback_service", "isolate_service", "check_logs",
    "check_metrics", "scale_service", "drain_traffic", "restore_traffic",
    "optimize_db", "escalate", "ignore"
]

# --- Action mapping ---
ACTION_MAPPING = {
    "scale_service": "scale",
    "scale": "scale",
    "restart_service": "restart_service",
    "rollback_service": "rollback_service",
    "isolate_service": "isolate_service",
    "check_logs": "check_logs",
    "check_metrics": "check_metrics",
    "drain_traffic": "drain_traffic",
    "restore_traffic": "restore_traffic",
    "optimize_db": "optimize_db",
    "escalate": "escalate",
    "ignore": "ignore"
}


def build_prompt(state: Dict[str, Any], task_objective: str, last_action=None, last_reward=None) -> str:
    """Build a prompt string from the state (same format as inference.py's get_model_message())."""
    step = state.get("time_step", 0)

    services_text = "\n".join([
        f"  {s['name']}: {s['status'].upper()} | latency={s['latency']:.0f}ms | error_rate={s['error_rate']:.2f}"
        for s in state.get("services", [])
    ])

    logs = state.get("logs", [])
    recent_logs = "\n".join([f"  {log}" for log in logs[-5:]]) if logs else "  No recent logs."

    alerts = "\n".join([f"  {alert}" for alert in state.get("alerts", [])]) if state.get("alerts") else "  No active alerts."

    available_actions = ", ".join(VALID_ACTIONS)

    diagnosed = state.get("diagnosed_targets", [])
    diagnosed_str = ", ".join(diagnosed) if diagnosed else "None"

    # Build feedback section
    feedback_section = ""
    if last_action is not None:
        feedback_section = f"""
PREVIOUS STEP:
Action Taken: {last_action}
Reward Received: {last_reward:.2f}

Use this feedback to adjust your strategy. Avoid repeating ineffective actions.
"""

    # Add decision hint
    decision_hint = """
IMPORTANT:
- If a service is clearly DOWN → take action immediately (do NOT keep checking logs)
- Do NOT repeat diagnostic actions more than 2 times
- If you already have enough evidence → FIX the issue
"""

    prompt = f"""--- INCIDENT RESPONSE TASK ---
Objective: {task_objective}
Step: {step} / {MAX_STEPS}

{feedback_section}
{decision_hint}

As a senior SRE, your goal is to restore all services to a healthy state. Analyze the service status, logs, and alerts to identify the root cause and take action. Prioritize actions that resolve the underlying issue. Available actions are: {available_actions}.

**Analyze the following data and provide the best next action to resolve the incident. If you are stuck, try a different action. Do not repeat the same action twice in a row.**

SERVICES:
{services_text}

RECENT LOGS (last 5):
{recent_logs}

ALERTS:
{alerts}

ALREADY DIAGNOSED: {diagnosed_str}

What is your next action? Reply with ONLY a JSON object:
{{"action_type": "...", "target": "..."}}
If the action has no target, omit the target field or set it to null."""
    return prompt


def get_task_objective(task_id: str) -> str:
    """Get task objective based on task_id."""
    if "cascading-ambiguous" in task_id:
        return "Restore all services to UP with error_rate < 0.1"
    elif "bad-deployment" in task_id:
        return "Roll back the faulty deployment to restore service stability."
    elif "auth-down" in task_id:
        return "Restore authentication service to UP state."
    elif "payments-degraded" in task_id:
        return "Restore payments service to healthy state with minimal error rate."
    elif "cascading-failure" in task_id:
        return "Stop cascading failure and restore all services to healthy state."
    elif "latent-root-cause" in task_id:
        return "Identify and fix the latent root cause affecting service stability."
    else:
        return "Restore all services to UP state with minimal error rate."


def call_llm(prompt: str) -> Optional[Dict[str, Any]]:
    """Call the LLM to get an action JSON."""
    if not client:
        print("Error: OpenAI client is not available. Please check your API key and network connection.")
        return None

    for attempt in range(2):  # Retry once if JSON fails
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a senior SRE agent. Respond only with the requested JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling LLM (attempt {attempt + 1}): {e}")
            if attempt == 0:
                continue
            return None

        # Parse JSON
        try:
            if "{" in content and "}" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            action_data = json.loads(content)

            action_type = action_data.get("action_type", "ignore")
            mapped_action_type = ACTION_MAPPING.get(action_type, "ignore")

            return {
                "action_type": mapped_action_type,
                "target": action_data.get("target") or "none"
            }
        except Exception as e:
            print(f"Error parsing JSON from LLM (attempt {attempt + 1}): {e}. Content: {content}")
            if attempt == 0:
                continue
            return None

    return None


def generate_command(action):
    action_type = action.get("action_type")
    target = action.get("target")

    if action_type == "check_logs":
        return f"journalctl -u {target} --no-pager | tail -n 50"
    elif action_type == "restart_service":
        return f"systemctl restart {target}"
    elif action_type == "rollback_service":
        return f"deploy rollback {target}"
    elif action_type == "check_metrics":
        return f"curl `http://metrics/{target}` "
    elif action_type == "scale":
        return f"kubectl scale deployment {target} --replicas=3"
    else:
        return "noop"


class RolloutCollector:
    """Collects rollouts from the incident response environment for GRPO training."""

    def __init__(self):
        if not client:
            raise RuntimeError("OpenAI client is not available. Please check your API key and configuration.")

    def collect_rollouts(self, task_ids: List[str], num_rollouts_per_task: int) -> List[Dict[str, Any]]:
        rollouts = []
        total_rollouts = 0
        saved_rollouts = 0

        for task_id in task_ids:
            for rollout_idx in range(num_rollouts_per_task):
                try:
                    rollout = self._collect_single_rollout(task_id, rollout_idx)
                    if rollout is not None:
                        total_rollouts += 1

                        step_count = rollout.get("steps", 0)

                        # Reject only extreme junk
                        if rollout["final_score"] < 0.05 and rollout["total_reward"] < -2.0:
                            print(f"[FILTER] Rejected {task_id} rollout {rollout_idx}: extreme junk")
                            continue

                        # Reject trivial 1-step lucky guesses on ALL tasks (not just hard)
                        if step_count == 1 and rollout["final_score"] < 0.7:
                            print(f"[FILTER] Rejected {task_id} rollout {rollout_idx}: 1 step, low score")
                            continue

                        # Keep all meaningful trajectories (2+ steps)
                        if step_count >= 2:
                            rollouts.append(rollout)
                            saved_rollouts += 1
                            continue

                        rollouts.append(rollout)
                        saved_rollouts += 1
                except Exception as e:
                    print(f"Warning: Failed to collect rollout {rollout_idx} for task {task_id}: {e}")
                    continue

        # Fallback: keep everything if we got almost nothing
        if saved_rollouts < 5:
            print(f"[WARNING] Only {saved_rollouts} rollouts passed filter. Saving all without filtering.")
            rollouts = []
            for task_id in task_ids:
                for rollout_idx in range(num_rollouts_per_task):
                    try:
                        rollout = self._collect_single_rollout(task_id, rollout_idx)
                        if rollout is not None:
                            rollouts.append(rollout)
                    except Exception as e:
                        continue

        print(f"\nTotal collected: {total_rollouts} | Saved after filter: {saved_rollouts}")
        return rollouts

    def _collect_single_rollout(self, task_id: str, rollout_idx: int) -> Optional[Dict[str, Any]]:
        # Step 1: Reset environment
        try:
            response = requests.post(f"{ENV_URL}/reset/{task_id}")
            if response.status_code != 200:
                print(f"Warning: Failed to reset task {task_id}: {response.text}")
                return None
            state = response.json()
        except Exception as e:
            print(f"Warning: HTTP error resetting task {task_id}: {e}")
            return None

        # Step 2: Build initial prompt
        task_objective = get_task_objective(task_id)
        original_prompt = build_prompt(state, task_objective)

        # Step 3: Run episode
        done = False
        steps = 0
        action_sequence = []
        trajectory = []
        last_action = None
        last_reward = None

        while not done and steps < MAX_STEPS:
            state_before = copy.deepcopy(state)
            prompt = build_prompt(state, task_objective, last_action, last_reward)

            action = call_llm(prompt)
            if action is None:
                action = {"action_type": "check_logs", "target": "none"}
                print(f"Warning: LLM call failed at step {steps}, using fallback")

            try:
                response = requests.post(f"{ENV_URL}/step/{task_id}", json=action)
                if response.status_code != 200:
                    print(f"Warning: Step failed for task {task_id}: {response.text}")
                    break
                result = response.json()

                state_after = result['state']
                base_reward = result['reward']
                done = result['done']
                steps += 1

                # ── Reward shaping ─────────────────────────────────────────────
                shaped_reward = base_reward

                # Penalize repeating the exact same action back-to-back
                if last_action is not None and action["action_type"] == last_action.get("action_type"):
                    shaped_reward -= 0.2

                # Penalize hallucinated service targets
                valid_services = [s["name"] for s in state_before.get("services", [])]
                if action.get("target") not in valid_services and action.get("target") not in ["none", None]:
                    shaped_reward -= 0.3

                # Reward decisive fix actions
                if action["action_type"] in ["restart_service", "rollback_service", "scale"]:
                    shaped_reward += 0.15

                # Penalize check_logs/check_metrics after step 3 (observation loop)
                if action["action_type"] in ["check_logs", "check_metrics"] and steps > 3:
                    shaped_reward -= 0.15

                # Penalize optimize_db when db is UP (honeypot trap on hard-bad-deployment)
                db_status = next(
                    (s["status"] for s in state_before.get("services", []) if s["name"] == "db"),
                    None
                )
                if action["action_type"] == "optimize_db" and db_status == "up":
                    shaped_reward -= 0.4

                # --- Root-cause-aware reward shaping ---
                # Bonus: early diagnostic actions (encourage reasoning before fixing)
                if steps <= 2 and action["action_type"] in ["check_logs", "check_metrics"]:
                    shaped_reward += 0.1
                # Penalty: fixing too early without diagnosis (likely lucky guess)
                if steps <= 2 and action["action_type"] in ["restart_service", "rollback_service", "scale"]:
                    shaped_reward -= 0.1
                # Strong penalty: repeated observation loop (already partially handled but reinforce)
                if action["action_type"] in ["check_logs", "check_metrics"] and steps > 5:
                    shaped_reward -= 0.2

                # ── End reward shaping ─────────────────────────────────────────
                reward = shaped_reward

                enriched_action = {
                    "action_type": action.get("action_type"),
                    "target": action.get("target"),
                    "reason": f"Step {steps}: decision based on service state and logs",
                    "command": generate_command(action)
                }

                action_sequence.append(json.dumps(enriched_action))
                trajectory.append({
                    "state": state_before,
                    "action": action,
                    "reward": reward,
                    "done": done,
                    "next_state": state_after
                })

                state = state_after
                last_action = action
                last_reward = reward

            except Exception as e:
                print(f"Warning: HTTP error during step for task {task_id}: {e}")
                break

        # Step 4: Get final score from grader
        final_score = 0.0
        try:
            grade_resp = requests.post(f"{ENV_URL}/grade/{task_id}")
            if grade_resp.status_code == 200:
                graded_score = grade_resp.json().get("final_score", None)
                if graded_score is not None:
                    final_score = max(0.0, min(1.0, float(graded_score)))
        except Exception as e:
            print(f"Warning: Failed to get grade for task {task_id}: {e}")

        total_reward = sum(step["reward"] for step in trajectory)
        completion = "\n".join(action_sequence)

        print(f"[ROLLOUT] task={task_id} steps={steps} final_score={final_score:.2f} total_reward={total_reward:.2f}")

        return {
            "task_id": task_id,
            "prompt": original_prompt,
            "completion": completion,
            "final_score": final_score,
            "total_reward": total_reward,
            "steps": steps
        }


if __name__ == "__main__":
    print("=== TESTING LLM CONNECTION ===")
    test_llm_connection()
    print("=" * 60)
    print("Starting rollout collection...\n")

    task_ids = [
        "easy-auth-down",
        "medium-payments-degraded",
        "hard-bad-deployment",
        "hard-cascading-ambiguous",
        "hard-latent-root-cause",
    ]
    num_rollouts_per_task = 8

    print(f"Total expected rollouts: {len(task_ids) * num_rollouts_per_task}")

    collector = RolloutCollector()
    rollouts = collector.collect_rollouts(task_ids, num_rollouts_per_task)

    for idx, rollout in enumerate(rollouts):
        print(f"Rollout {idx}: task_id={rollout['task_id']}, score={rollout['final_score']:.2f}, steps={rollout.get('steps', 0)}")

    os.makedirs("training", exist_ok=True)

    with open("training/rollouts_sample.json", "w") as f:
        json.dump(rollouts, f, indent=2)

    print(f"\nSaved {len(rollouts)} rollouts to training/rollouts_sample.json")