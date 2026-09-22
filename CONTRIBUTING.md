# Contributing to RootTrace

## Development setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    pip install -e .

## Validate before opening a PR

    roottrace validate
    python -m unittest discover -s tests -p "test_*.py"

The CI matrix runs the same validation on Python 3.10 and 3.12.

## Adding a scenario

Create a YAML file under env/scenarios/.

A valid scenario should declare:

- id, difficulty, description, goal, max_steps
- services
- dependencies
- resolution_actions
- diagnosis_requirements when diagnosis should be required
- fault_policy and dynamics when the incident evolves over time

Scenario loading performs structural validation automatically.

## Adding an agent

Implement reset() and act() in agents/, then register a factory in agents/registry.py.

Agents should be deterministic for a fixed seed whenever stochastic behavior is used.

## Benchmarking

    roottrace benchmark --agent dependency-aware --seed 42 --seed 43
    roottrace compare --agent dependency-aware --agent random --seed 42

Use JSON output files when a benchmark result needs to be committed or compared later.

## Pull requests

Keep changes focused. Prefer one conceptual change per commit. Include tests for new runtime behavior and keep roottrace validate green.