import json
import re
import hashlib
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from trl import GRPOTrainer, GRPOConfig

# ── Load rollout data ──────────────────────────────────────────────────────────
with open("training/rollouts_sample.json") as f:
    data = json.load(f)

# ── Build prompt → rollout lookup (keyed by prompt hash) ──────────────────────
# This is critical: GRPOTrainer shuffles samples and calls reward_funcs with
# batches of (prompt, generated_completion). We cannot use list indices.
prompt_to_rollout = {}
for rollout in data:
    key = hashlib.md5(rollout["prompt"].encode()).hexdigest()
    prompt_to_rollout[key] = rollout

# ── Dataset: only prompts — GRPOTrainer generates its own completions ─────────
# The "completion" column from your rollout data is NOT used by GRPOTrainer.
# GRPO generates G completions per prompt at training time and scores them live.
train_data = [{"prompt": r["prompt"]} for r in data]
dataset = Dataset.from_list(train_data)

# ── Valid action types (must match your env's ActionType enum) ─────────────────
VALID_ACTIONS = {
    "restart_service", "rollback_service", "isolate_service",
    "check_logs", "check_metrics", "scale", "drain_traffic",
    "restore_traffic", "optimize_db", "escalate", "ignore"
}

KNOWN_SERVICES = {"auth", "payments", "frontend", "db"}

# ── Reward function ────────────────────────────────────────────────────────────
# GRPOTrainer calls this with:
#   prompts:     list[str]  — the prompt strings for this batch
#   completions: list[str]  — the model's generated completions (one per prompt)
# Must return: list[float]
def incident_reward(prompts, completions, **kwargs):
    rewards = []
    for prompt, completion in zip(prompts, completions):

        # Look up the rollout context for this prompt
        key = hashlib.md5(prompt.encode()).hexdigest()
        ctx = prompt_to_rollout.get(key, {})
        rollout_score = ctx.get("final_score", 0.3)  # baseline from teacher rollout

        score = 0.0
        completion = completion.strip()

        # ── Rule 1: Must be valid JSON ──────────────────────────────────────
        # Your env expects {"action_type": "...", "target": "..."}
        # If the model can't produce this, it gets a hard penalty.
        try:
            # Strip markdown code fences if model produces them
            clean = re.sub(r"```(?:json)?|```", "", completion).strip()
            # Extract first JSON object if model produces extra text
            match = re.search(r"\{.*?\}", clean, re.DOTALL)
            if not match:
                rewards.append(-0.5)
                continue
            action = json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            rewards.append(-0.5)
            continue

        action_type = action.get("action_type", "")
        target = action.get("target", "")

        # ── Rule 2: action_type must be from the valid set (+0.2) ───────────
        if action_type in VALID_ACTIONS:
            score += 0.2
        else:
            score -= 0.3  # hallucinated action type

        # ── Rule 3: target must be a real service or null (+0.2) ────────────
        if target in KNOWN_SERVICES:
            score += 0.2
        elif target in ("none", "", None):
            score += 0.05  # acceptable for escalate/ignore
        else:
            score -= 0.3   # hallucinated service name

        # ── Rule 4: Early diagnosis is good, late diagnosis is wasteful ──────
        # Parse step number from prompt (format: "Step: N / MAX")
        step_match = re.search(r"Step:\s*(\d+)", prompt)
        step = int(step_match.group(1)) if step_match else 0

        if action_type in ("check_logs", "check_metrics"):
            if step <= 2:
                score += 0.15   # diagnosing early = good SRE behavior
            elif step > 4:
                score -= 0.15   # still checking logs at step 5+ = observation loop

        # ── Rule 5: Penalize optimize_db when db is UP ───────────────────────
        # This catches the "hard-bad-deployment" honeypot trap.
        # If "db: UP" appears in the prompt, optimizing db is wrong.
        if action_type == "optimize_db" and re.search(r"db:\s*UP", prompt, re.IGNORECASE):
            score -= 0.5

        # ── Rule 6: Penalize fixing the symptom target instead of root cause ─
        # For tasks where logs blame "db" but real cause is "auth"
        # We embed this signal by checking the alert context in the prompt.
        # If prompt has "auth-v2" or goroutine leak, fixing db is wrong.
        if action_type in ("optimize_db", "restart_service") and target == "db":
            if "goroutine leak" in prompt or "auth-v2" in prompt:
                score -= 0.4

        # ── Rule 7: Use the teacher rollout's final_score as a soft bonus ────
        # This keeps the model anchored to known-good trajectories without
        # overriding the per-step structural rewards above.
        score += rollout_score * 0.3

        # Clamp to [-1, 1]
        rewards.append(float(max(-1.0, min(1.0, score))))

    return rewards


# ── Model setup ───────────────────────────────────────────────────────────────
device = "cuda" if torch.cuda.is_available() else "cpu"
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float32
).to(device)

# ── GRPO config ───────────────────────────────────────────────────────────────
config = GRPOConfig(
    learning_rate=5e-5,
    per_device_train_batch_size=1,
    num_train_epochs=3,
    max_prompt_length=512,
    max_completion_length=64,
    num_generations=4,
    temperature=0.9,
    logging_steps=1,
)

# ── Trainer ───────────────────────────────────────────────────────────────────
trainer = GRPOTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=config,
    reward_funcs=[incident_reward],   # ← This was completely missing before
)

# ── Train ─────────────────────────────────────────────────────────────────────
trainer.train()

# ── Save ──────────────────────────────────────────────────────────────────────
trainer.save_model("training/grpo_model")
print("Done.")