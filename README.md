# RootTrace

[![CI](https://github.com/roonakyadav/RootTrace/actions/workflows/ci.yml/badge.svg)](https://github.com/roonakyadav/RootTrace/actions/workflows/ci.yml)

**A causal incident environment for evaluating AI agents under noisy telemetry, cascading failures, and operational risk.**

RootTrace gives an agent a dynamic distributed-system world and asks it to diagnose the **root cause**, choose actions, and recover the system without wasting time or making the incident worse.

The project is built around one question:

> **Can an AI agent diagnose and safely resolve a system failure when the obvious signal is not necessarily the cause?**

## Why RootTrace exists

Simple agent benchmarks often make the correct action obvious. RootTrace is designed around harder operational properties:

- misleading logs and alerts
- service dependencies and cascading failures
- delayed consequences
- partial recovery
- action costs and operational strain
- hidden or latent root causes
- diagnosis-before-action requirements
- trajectory-level evaluation

The agent is evaluated on **how** it solved an incident, not only whether the final state recovered.

## Quick start

The current prototype models four services:

```text
                    ┌──────────┐
                    │    db    │
                    └────┬─────┘
                         │
                    ┌────▼────┐
                    │  auth   │
                    └────┬────┘
                         │
                  ┌──────▼──────┐
                  │  payments   │
                  └──────┬──────┘
                         │
                    ┌────▼────┐
                    │ frontend │
                    └─────────┘
```

The environment exposes state such as service health, latency, error rate, logs, alerts, dependencies, system stability, strain, diagnostic history, and trajectory history.

Actions currently include:

```text
restart_service
rollback_service
scale
optimize_db
isolate_service
check_logs
check_metrics
drain_traffic
restore_traffic
escalate
ignore
```

## Evaluation

RootTrace currently scores episodes across multiple dimensions:

- root-cause resolution
- efficiency
- cost efficiency
- stability
- action sequence
- operational damage
- wasted actions
- delayed failures

It also detects behavioral patterns such as symptom chasing, lucky guessing, observation loops, and late correction.

## Repository structure

```text
RootTrace/
├── api/                 # HTTP interface
├── agents/              # Interchangeable agent implementations
├── env/                 # Environment dynamics, tasks, and grading
├── models/              # Typed state/action schemas
├── tests/               # Environment and system tests
├── training/            # Rollout collection and GRPO experiments
├── static/              # Lightweight demo UI
├── cli.py               # Public command-line interface
├── openenv.yaml         # Optional ecosystem metadata
├── pyproject.toml       # Python package metadata
├── requirements.txt     # Runtime dependencies
└── Dockerfile           # Container deployment
```

## Quick start

```bash
git clone https://github.com/roonakyadav/RootTrace.git
cd RootTrace

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Validate the bundled scenarios:

```bash
roottrace validate
```

Run a benchmark:

```bash
roottrace benchmark --agent dependency-aware --seed 42 --seed 43
```

Compare agents:

```bash
roottrace compare --agent dependency-aware --agent random --seed 42
```

Start the HTTP API:

```bash
roottrace serve
```

### Run a benchmark

Use the public CLI:

```bash
python -m cli validate
python -m cli benchmark --agent dependency-aware --seed 42 --seed 43
```

Available agents currently include `dependency-aware`, `random`, and `llm`.

For LLM evaluation, set `LLM_API_KEY` (or `HF_TOKEN`) and optionally override `LLM_BASE_URL` and `LLM_MODEL`.


## Design direction

RootTrace is being evolved from a handcrafted incident-response environment into a reusable agent-evaluation system.

The planned architecture separates:

```text
Scenario generation
       ↓
Environment runtime
       ↓
Telemetry / observations
       ↓
Agent actions
       ↓
State transitions
       ↓
Trajectory recording
       ↓
Evaluation / benchmarking
```

The goal is to make scenarios declarative, failures reproducible, agents interchangeable, and benchmark results comparable across models and seeds.

## License

MIT
