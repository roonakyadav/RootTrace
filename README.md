---
title: AI Incident OpenEnv
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
- openenv
- incident-response
- sre
- devops
- multi-step-reasoning
- llm-evaluation
---

# AI Incident Response — OpenEnv Environment

**When distributed systems fail, AI agents must reason like senior SREs — not pattern-match.** This environment tests whether AI can identify root causes amid misleading logs, cascading failures, and time pressure. Most agents fail because they chase symptoms instead of reasoning through dependencies.

**Live Demo:** https://roonakyadav-ai-incident-openenv-final.hf.space  
**GitHub:** https://github.com/roonakyadav/meta-hackathon

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Hugging Face token (get one at https://huggingface.co/settings/tokens)
export HF_TOKEN=your_huggingface_token

# 3. Start the environment server
python3 -m api.main

# 4. Validate all tasks are working
curl http://localhost:7860/validate

# 5. Run LLM agent evaluation
python3 inference.py
```

**That's it!** The environment defaults to Hugging Face's inference router — no Groq or OpenAI keys required.

---

## The Problem

Modern AI agents excel at straightforward tasks: "find the broken service and restart it." But real incident response is harder. Logs lie. Failures cascade. The obvious fix often makes things worse.

This environment simulates **distributed system incident response** where agents must:
- **Suppress misleading signals** (8 out of 12 log lines blame the wrong service)
- **Race against time** (healthy services autonomously degrade while the agent deliberates)
- **Diagnose before acting** (blind fixes produce partial recovery or actively worsen the system)
- **Reason through dependencies** (fixing symptoms before root causes triggers re-degradation)

The goal: separate agents that genuinely reason from those that pattern-match.

---

## Design Philosophy

Three core principles differentiate this from typical "find-and-fix" environments:

### 1. Misleading Signal Over Correct Signal

In `hard-bad-deployment`, the logs produce **8 lines implicating the database for every 1 line implicating auth**. A correct agent must suppress the dominant false signal and reason from weaker evidence.

### 2. Dynamic Environment Degradation

Every 2–3 steps on hard tasks, a healthy service **autonomously degrades** due to the unresolved root cause spreading. The agent races against a deteriorating system, not a static puzzle. Waiting to observe is punished by the environment itself.

### 3. Diagnosis Gates and Honeypot Actions

On `hard-bad-deployment`, running `optimize_db` on the database — the intuitively "correct" action given the logs — **actively worsens the system** (increases auth error rate, raises system strain). A successful rollback of auth requires prior diagnosis (`check_logs auth` + `check_metrics auth`). Blind fixes produce only partial recovery.

---

## Key Features

- **6 Task Scenarios**: Easy, medium, and hard difficulty levels testing different reasoning capabilities
- **Realistic Service Topology**: 4 interconnected services (db, auth, payments, frontend) with dependency chains
- **Anti-Reward-Hacking**: Three explicit mechanisms prevent agents from gaming the system
- **Multi-Component Scoring**: Final score based on success, efficiency, cost, stability, and action sequence
- **Episode Classification**: Automatically classifies agent behavior (Efficient Reasoner, Symptom Chaser, Lucky Guesser, etc.)
- **Dynamic Degradation**: Services autonomously degrade every 2-3 steps on hard tasks if root cause unresolved
- **Comprehensive API**: RESTful endpoints for reset, step, state, validation, and baseline evaluation
- **LLM Integration**: Works with Hugging Face, Groq, or OpenAI (defaults to HF router)
- **Baseline Agent**: Strong dependency-based root cause analysis for comparison

---

## System Architecture

### Service Topology

```
┌─────────┐
│    db   │ ← Root cause in cascading-failure
└────┬────┘
     │ depends on
     ▼
┌─────────┐     ┌──────────┐
│  auth   │◄────│ payments │ ← Shared DB pool (ambiguous task)
└────┬────┘     └────┬─────┘
     │               │
     └───────┬───────┘
             │
             ▼
       ┌──────────┐
       │ frontend │ ← User-facing, depends on both
       └──────────┘
```

| Service | Role | Dependencies |
|:---|:---|:---|
| **db** | Persistence layer | Root cause in `cascading-failure` |
| **auth** | Authentication gateway | Depends on `db` |
| **payments** | Transaction processing | Depends on `db`, shares pool with `auth` |
| **frontend** | User interface | Depends on `auth` + `payments` |

---

## Observation & Action Space

| Field | Type | Description |
|:---|:---|:---|
| `services` | list | Per-service state: `name`, `status`, `latency`, `error_rate` |
| `logs` | list[str] | Last 10 log lines — may contain misleading entries |
| `alerts` | list[str] | Active alerts (CRITICAL / WARNING / INFO) |
| `system_health` | float 0–1 | Fraction of services currently UP |
| `system_stability` | float 0–1 | Composite stability score (service states + strain + alerts) |
| `system_strain` | float 0–1 | Infrastructure stress from bad actions and unresolved failures |
| `dependencies` | dict | Live dependency graph for the current task |
| `time_step` | int | Current step in the episode |

### Available Actions

| Action | Target | Effect |
|:---|:---|:---|
| `restart_service` | service name | Restarts a DOWN service. Does NOT fix DEGRADED state. |
| `rollback_service` | service name | Rolls back to last stable version. Required fix for bad deployments. On `hard-bad-deployment`, requires prior diagnosis to fully succeed. |
| `scale` | service name | Scales a DEGRADED service up. Costs 3.0. |
| `optimize_db` | `db` | Fixes a degraded DB. **Honeypot on `hard-bad-deployment`** — worsens state if DB is healthy. |
| `check_logs` | service name | Adds target to `diagnosed_targets`. Returns updated log tail. |
| `check_metrics` | service name | Returns latency + error_rate per service. Required for diagnosis gate on `hard-bad-deployment`. |
| `isolate_service` | service name | Removes service from dependency graph temporarily. Increases latency on dependents. |
| `drain_traffic` | service name | Redirects traffic away from a degraded service. Reduces frontend error rate. |
| `restore_traffic` | service name | Reverses drain. |
| `escalate` | — | Ends episode immediately. Returns partial score proportional to system health. |
| `ignore` | — | Takes no action. System continues to degrade. |

---

## Scoring & Reward Design

Step-level rewards are calculated per action outcome:

| Outcome | Reward |
|:---|:---|
| Correct fix (root cause) | +0.40 to +0.75 |
| Temporary / partial fix | +0.05 to +0.20 |
| Diagnosis (check_logs / check_metrics) | +0.05 to +0.10 |
| Wrong fix | −0.20 to −0.40 |
| Useless action | −0.20 |
| All services UP | +0.30 bonus |
| Stability improvement | +0.20 bonus |

**Episode final score formula:**

```
final_score = 0.40 × success        # Did you fix the root cause?
            + 0.15 × efficiency      # How quickly?
            + 0.20 × cost_efficiency # Did you avoid waste?
            + 0.05 × stability       # Did you keep the system stable?
            + 0.20 × sequence        # Did you act in the right order?
```

The **sequence score** is the most discriminating component. It rewards early root cause identification, correct fix ordering, and penalises:
- Fixing symptoms before the root cause
- Spamming diagnosis actions without fixing anything (≥3 consecutive → hard cap at 0.35 final score)
- Rolling back without prior diagnosis on gated tasks

### Anti-Reward-Hacking Mechanisms

Three explicit protections prevent agents from gaming the reward signal:

1. **Observation loop penalty.** After 3 consecutive `check_logs`/`check_metrics` with no fix attempt, system strain increases (+0.25), stability drops (−0.15), and a warning log is emitted. Final score is hard-capped at 0.35 for agents that never attempt a fix.

2. **Diagnosis gate.** On `hard-bad-deployment`, `rollback_service auth` without prior `check_logs auth` + `check_metrics auth` produces only a `partial_fix` (reward +0.05, service remains DEGRADED). The `root_cause_fixed` success condition awards only 0.5× credit for blind rollbacks.

3. **Honeypot action.** `optimize_db` on a healthy database (as in `hard-bad-deployment`) is scored as `wrong_fix`, increases auth error rate by +0.10, and raises system strain by +0.30. It counts toward the bad action limit.

---

## Agent Behavior Classification

The grader classifies each episode into one of five failure types, visible in the score breakdown:

| Type | Behavior | Condition |
|:---|:---|:---|
| **Efficient Reasoner** ✅ | Root cause fixed within 2 steps, no symptom fixes, no observation loop | Ideal performance |
| **Symptom Chaser** ❌ | Fixed downstream services before root cause, triggered re-degradation | Common failure mode |
| **Lucky Guesser** ⚠️ | Fixed root cause without prior diagnosis | Partial credit only |
| **Stuck in Observation Loop** 🔄 | ≥3 consecutive diagnosis actions with no fix attempt | Hard-capped at 0.35 |
| **Late Corrector** ⏰ | Root cause eventually fixed, but after step 5 | Reduced efficiency score |

---

## Task Scenarios

Six scenarios across three difficulty levels, each testing different reasoning capabilities:

### Easy: Single Service Failure

#### easy-auth-down
**Max steps:** 5 | **Objective:** Restart the failed auth service

- **Setup:** `auth=DOWN`, `payments=UP`, `frontend=UP`
- **Success:** All services UP, error_rate < 0.05
- **Failure:** >2 bad actions or steps exceeded
- **Correct path:** `check_logs auth` → `restart_service auth`

---

### Medium: Load Degradation

#### medium-payments-degraded
**Max steps:** 8 | **Objective:** Scale payments without overspending

- **Setup:** `auth=UP`, `payments=DEGRADED`, `frontend=UP`
- **Success:** No service DOWN, latency < 200ms, total cost < 15
- **Failure:** >3 bad actions or stability < 0.4
- **Correct path:** `check_metrics payments` → `scale payments`

---

### Hard: Complex Reasoning

#### hard-bad-deployment ⚠️
**Max steps:** 10 | **Objective:** Rollback faulty auth deployment after proper diagnosis

A new `auth-v2.1.0` deployment introduced a goroutine leak. **8 of 12 initial log lines blame the database.** The DB is perfectly healthy. Running `optimize_db` makes things worse.

- **Setup:** `auth=DEGRADED (error_rate=0.9)`, `db=UP`, `payments=UP`, `frontend=UP`
- **Success:** All services UP, root cause fixed (with diagnosis gate)
- **Failure:** >3 bad actions or stability < 0.3
- **Correct path:** `check_logs auth` → `check_metrics auth` → `check_logs db` → `rollback_service auth`
- **Trap:** `optimize_db db` → **wrong_fix**, strain +0.30, auth error rate worsens

---

#### hard-cascading-failure
**Max steps:** 10 | **Objective:** Fix DB degradation causing cascading failures

DB degradation is causing auth to go DOWN and payments to degrade. **Misleading logs blame payments and auth throughout the episode.** Environment autonomously degrades healthy services every 2 steps if root cause is unresolved.

- **Setup:** `db=DEGRADED`, `auth=DOWN`, `payments=DEGRADED`, `frontend=UP`
- **Success:** Stability ≥ 0.9, root cause (db) fixed, strain < 0.3
- **Failure:** >3 bad actions or stability < 0.3
- **Correct path:** `check_logs db` → `optimize_db db` → wait for cascading recovery

---

#### hard-cascading-ambiguous
**Max steps:** 15 | **Objective:** Identify shared dependency and rollback correct service

Both auth and payments are DEGRADED, frontend is DOWN. A `payments-v3.4.1` deployment broke a shared connection pool. **Fixing auth first causes it to re-degrade within 2 steps.**

- **Setup:** `auth=DEGRADED`, `payments=DEGRADED`, `db=UP`, `frontend=DOWN`
- **Success:** All services UP, error_rate < 0.1
- **Failure:** >4 bad actions or stability < 0.25
- **Correct path:** `check_logs payments` → `check_metrics payments` → `rollback_service payments`
- **Wrong path:** `restart_service auth` → auth recovers → re-degrades at step +2

---

#### hard-latent-root-cause
**Max steps:** 12 | **Objective:** Find hidden root cause invisible to surface logs

Auth is visibly DEGRADED. Payments is UP. **Every surface log blames auth.** The true root cause is a latent issue in the payments persistence layer that is not directly visible. Fixing auth produces a fake recovery that degrades again in 2 steps.

- **Setup:** `auth=DEGRADED (error_rate=0.5)`, `payments=UP`, `frontend=UP`
- **True root cause:** `payments` | **Surface symptom:** `auth`
- **Success:** All services UP, root cause fixed
- **Failure:** >4 bad actions or stability < 0.25
- **Correct path:** `check_logs payments` → `check_metrics payments` → `restart_service payments` or `rollback_service payments`

---

## Example Trajectories

### Success Trajectory (hard-bad-deployment)

```
Step 1  check_logs auth       → diagnosed_targets: {auth}
        Logs reveal goroutine leak at 8,412 goroutines (expected <500)

Step 2  check_metrics auth    → diagnosis gate condition 1 satisfied
        Metrics: auth error_rate=0.91, latency=1100ms

Step 3  check_logs db         → diagnosed_targets: {auth, db}
        Logs: DB active_connections=42/200, replication_lag=2ms — healthy

Step 4  rollback_service auth → diagnosis gate passed → correct_fix
        auth recovers: status=UP, error_rate=0.01
        Episode ends. Final score: ~0.82
```

**Trap Trajectory (same task):**

```
Step 1  optimize_db db        → wrong_fix (DB is healthy)
        auth error_rate: 0.90 → 1.00, system_strain +0.30

Step 2  restart_service auth  → partial_fix (rollback required)
        auth remains DEGRADED

Step 3  rollback_service auth → partial_fix (diagnosis gate not passed)
        auth remains DEGRADED

Step 4  bad_actions=3 → episode terminates, final score capped at 0.30
```

---

## Baseline Performance

Evaluated on `llama-3.1-8b-instant`:

| Task | Baseline Score | Notes |
|:---|:---|:---|
| easy-auth-down | **0.82** | Solves reliably |
| medium-payments-degraded | **0.71** | Occasional over-scaling |
| hard-bad-deployment | **0.41** | Frequently hits honeypot |
| hard-cascading-ambiguous | **0.31** | Re-degradation confuses agent |
| hard-latent-root-cause | **0.28** | Surface symptom dominates |

*Reproduce with:* `python3 inference.py`

**Key insight:** Performance drops sharply on hard tasks, demonstrating that current LLMs struggle with:
- Suppressing misleading signals
- Multi-step causal reasoning
- Resisting intuitive but wrong actions (honeypots)

---

## Setup & Deployment

### Local

```bash
git clone https://github.com/roonakyadav/meta-hackathon
cd meta-hackathon
pip install -r requirements.txt
python3 -m api.main
```

### Docker Deployment

```bash
docker build -t ai-incident-openenv .
docker run -p 7860:7860 ai-incident-openenv
```

### Inference (Hugging Face Space)

```bash
API_BASE_URL=https://roonakyadav-ai-incident-openenv-final.hf.space \
MODEL_NAME=llama-3.1-8b-instant \
HF_TOKEN=your_key \
python3 inference.py
```

---

## API Reference

The environment exposes a RESTful API for agent interaction. All endpoints run on port 7860.

### Core Endpoints

| Endpoint | Method | Body | Description |
|:---|:---|:---|:---|
| `/tasks` | GET | — | List all available tasks with metadata |
| `/reset` | POST | `{"task_id": "...", "seed": 42}` | Start a new episode |
| `/step` | POST | `{"action_type": "...", "target": "..."}` | Take one action |
| `/step/{task_id}` | POST | `Action` object | Take action (alternative endpoint) |
| `/state` | GET | `?task_id=easy` | Read current state (no side effects) |
| `/state/{task_id}` | GET | — | Read state by task ID |
| `/validate` | GET | — | Quick sanity check for all 6 tasks |
| `/baseline/{task_id}` | POST | — | Run baseline agent on task |

### Example Usage

**List all tasks:**
```bash
curl http://localhost:7860/tasks
```

**Reset environment:**
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "hard-bad-deployment", "seed": 42}'
```

**Take an action:**
```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "check_logs", "target": "auth", "task_id": "hard-bad-deployment"}'
```

**Validate all tasks:**
```bash
curl http://localhost:7860/validate
```

**Response:**
```json
{
  "validation": {
    "easy-auth-down": "ok",
    "medium-payments-degraded": "ok",
    "hard-bad-deployment": "ok",
    "hard-cascading-failure": "ok",
    "hard-cascading-ambiguous": "ok",
    "hard-latent-root-cause": "ok"
  }
}
```

**Run baseline agent:**
```bash
curl -X POST http://localhost:7860/baseline/easy-auth-down
```

---

## Project Structure

```
openenv/
├── api/
│   └── main.py                 # FastAPI server with all endpoints
├── baseline/
│   ├── baseline_agent.py       # Dependency-based root cause agent
│   ├── reasoning_agent.py      # Advanced reasoning agent
│   ├── run_agent.py            # Agent runner utilities
│   ├── test_grader.py          # Grader unit tests
│   └── test_termination.py     # Termination logic tests
├── env/
│   ├── core.py                 # Core environment engine (900+ lines)
│   ├── grader.py               # Episode grading and scoring
│   └── tasks.py                # Task definitions and scenarios
├── models/
│   └── schemas.py              # Pydantic data models
├── tests/
│   ├── e2e_test.py             # End-to-end integration tests
│   ├── full_system_test.py     # Full system validation
│   ├── stress_test_latent.py   # Stress testing for latent causes
│   ├── latent_root_cause_test.py # Latent root cause scenarios
│   ├── diagnostic_benchmark.py # Diagnostic capability tests
│   └── run_all_tests.py        # Test runner
├── static/
│   └── index.html              # Web UI for interaction
├── inference.py                # LLM agent evaluation script
├── openenv.yaml                # Environment configuration
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container deployment
├── .env.example                # Environment variable template
└── README.md                   # This file
```

---

## Environment Variables

Only **one** environment variable is required:

| Variable | Required | Default | Description |
|:---|:---|:---|:---|
| `HF_TOKEN` | **Yes** | — | Hugging Face API token for LLM inference |
| `MODEL_NAME` | No | `meta-llama/Llama-3.1-8B-Instruct` | LLM model to use |
| `API_BASE_URL` | No | `https://router.huggingface.co/v1` | LLM API endpoint |
| `ENV_URL` | No | `http://localhost:7860` | Environment server URL |

**Setup:**
```bash
cp .env.example .env
# Edit .env and add your HF_TOKEN
export HF_TOKEN=your_token_here
```

**Get your HF token:** https://huggingface.co/settings/tokens

---

## Testing

The project includes comprehensive test suites covering all functionality:

### Run All Tests
```bash
python3 tests/run_all_tests.py
```

### Individual Test Suites
```bash
# End-to-end integration tests
python3 tests/e2e_test.py

# Full system validation
python3 tests/full_system_test.py

# Stress testing for latent root causes
python3 tests/stress_test_latent.py

# Latent root cause scenarios
python3 tests/latent_root_cause_test.py

# Diagnostic capability benchmark
python3 tests/diagnostic_benchmark.py
```

### Test Coverage
- ✅ All 6 task scenarios
- ✅ Environment reset and step operations
- ✅ Grading and scoring logic
- ✅ Episode termination conditions
- ✅ Baseline agent performance
- ✅ Anti-reward-hacking mechanisms
- ✅ Dynamic environment degradation
- ✅ Dependency chain cascading

---

## Troubleshooting

### Server won't start
```bash
# Check if port 7860 is already in use
lsof -i:7860

# Kill existing process
kill -9 <PID>

# Restart server
python3 -m api.main
```

### LLM inference fails
```bash
# Verify HF token is set
echo $HF_TOKEN

# Test API connectivity
python3 -c "from inference import client; print('OK' if client else 'FAIL')"

# Check .env file exists
cat .env
```

### Tasks not validating
```bash
# Run validation endpoint
curl http://localhost:7860/validate

# Check server logs
tail -f /tmp/server.log
```

### Import errors
```bash
# Ensure you're in the project root
cd /path/to/openenv

# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH if needed
export PYTHONPATH=$PWD
```

---

## Deployment Options

### Local Development
```bash
git clone https://github.com/roonakyadav/meta-hackathon
cd meta-hackathon
pip install -r requirements.txt
python3 -m api.main
```

### Docker
```bash
docker build -t ai-incident-openenv .
docker run -p 7860:7860 ai-incident-openenv
```

### Hugging Face Spaces
1. Push to GitHub repository
2. Create new Space on Hugging Face
3. Select "Docker" as SDK
4. Set environment variables in Space settings
5. Deploy automatically

---

## Contributing

We welcome contributions! Here's how to help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Development Guidelines
- Follow PEP 8 style guide for Python code
- Add tests for new features
- Update documentation accordingly
- Ensure all tests pass before submitting PR

---

## Research & Citation

If you use this environment in your research, please cite:

```bibtex
@misc{ai-incident-openenv-2024,
  title={AI Incident Response OpenEnv: Evaluating LLM Agents on Distributed System Incidents},
  author={Roonak Yadav},
  year={2024},
  url={https://github.com/roonakyadav/meta-hackathon}
}
```

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Acknowledgments

- **OpenEnv Framework**: Base environment specification
- **Hugging Face**: Inference router and model hosting
- **FastAPI**: High-performance web framework
- **Pydantic**: Data validation and serialization

---

## Contact

- **GitHub**: https://github.com/roonakyadav
- **Hugging Face**: https://huggingface.co/roonakyadav
- **Live Demo**: https://roonakyadav-ai-incident-openenv-final.hf.space

---

**Built with ❤️ for the AI safety and SRE communities**
