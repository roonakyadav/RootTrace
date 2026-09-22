# RootTrace Architecture

RootTrace is a deterministic incident-response environment designed to evaluate agents on diagnosis, intervention, and recovery.

## Runtime

    Scenario YAML
         |
         v
    +-----------------+
    |   Task loader   |
    +-----------------+
         |
         v
    +-----------------+
    |   IncidentEnv   |
    +-----------------+
      |      |      |
      v      v      v
  Dynamics Observability Telemetry
      |         |          |
      v         v          v
   Faults    Evidence    Metrics
       \        |        /
        \       |       /
         +------+------/
                |
                v
              State
                |
                v
              Agent
                |
                v
              Action
                |
                v
              Grader
                |
                v
          EpisodeTrace
                |
                v
        BenchmarkReport

## Core boundaries

### Scenarios

Scenario YAML contains incident-specific configuration:

- service initial state
- dependency graph
- root cause and surface symptom metadata
- diagnosis requirements
- valid resolution actions
- autonomous faults
- propagation and periodic dynamics

The loader validates scenarios before exposing them to the runtime.

### Environment runtime

IncidentEnv owns episode orchestration and delegates state mutation to focused components:

- DynamicsEngine: dependency propagation, recovery, autonomous evolution
- FaultInjector: exogenous degradation
- TelemetryEngine: latency/error-rate generation
- ObservabilityEngine: logs, alerts, and evidence
- DependencyGraph: graph queries

RuntimeState contains mutable per-episode state.

### Agent interface

Every agent implements reset(seed) and act(state) methods.

Current implementations:

- DependencyAwareAgent
- RandomAgent
- LLMAgent

### Evaluation

EpisodeRunner records complete trajectories. BenchmarkRunner executes the same agent over multiple tasks and seeds. CounterfactualEvaluator restores snapshots to evaluate alternate actions without mutating the real episode.

## Reproducibility

A benchmark case is identified by (agent, task_id, seed).

The environment and stochastic agents receive that seed explicitly. Environment snapshots also preserve the RNG state.

## Extension points

New scenarios should normally require only a new YAML file.

New agents should implement the Agent protocol and register a factory in agents/registry.py.

New evaluation metrics should be added to evaluation/benchmark.py without changing environment dynamics.