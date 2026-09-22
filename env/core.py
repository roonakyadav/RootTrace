from copy import deepcopy
import random
from typing import List, Dict, Any
from models.schemas import State, Service, ServiceStatus, Action, ActionType, Task, TaskDifficulty
from env.grader import IncidentGrader
from env.dependencies import DependencyGraph
from env.resolution import matching_resolution, missing_diagnosis, is_fix_action
from env.faults import FaultInjector
from env.observability import ObservabilityEngine
from env.dynamics import DynamicsEngine
from env.runtime import RuntimeState
from env.snapshot import EnvironmentSnapshot
from env.telemetry import TelemetryEngine

class IncidentEnv:
    ACTION_COSTS = {
        ActionType.RESTART_SERVICE: 1.0,
        ActionType.SCALE: 3.0,
        ActionType.OPTIMIZE_DB: 5.0,
        ActionType.ROLLBACK_SERVICE: 4.0,
        ActionType.ISOLATE_SERVICE: 2.0,
        ActionType.CHECK_LOGS: 0.1,
        ActionType.CHECK_METRICS: 0.2,
        ActionType.DRAIN_TRAFFIC: 1.5,
        ActionType.RESTORE_TRAFFIC: 0.5,
        ActionType.ESCALATE: 0.0,
        ActionType.IGNORE: 0.0
    }

    def __init__(self, task: Task, seed: int = 42):
        self.task = task
        self.random = random.Random(seed)
        self.max_steps = task.max_steps
        self.true_root_cause = getattr(task, "true_root_cause", None)
        self.surface_symptom_target = getattr(task, "surface_symptom_target", None)
        self.RISK_THRESHOLD = 0.5

        # All mutable episode state lives in one object. Keeping it separate
        # makes reset/replay and future parallel evaluation safer.
        self.runtime = RuntimeState.from_task(task)

        self.dependency_graph = DependencyGraph.for_task(self.task)
        self.dependencies = self.dependency_graph.as_dict()
        self.grader = IncidentGrader()
        self.telemetry = TelemetryEngine(
            self.runtime,
            self.dependency_graph,
            self.random,
            self.RISK_THRESHOLD,
        )
        self.fault_injector = FaultInjector(
            self.runtime,
            self.dependency_graph,
            self.random,
        )
        self.observability = ObservabilityEngine(
            self.runtime,
            self.dependency_graph,
            self.task,
            self.random,
        )
        self.observability.seed_initial_logs()
        self.dynamics = DynamicsEngine(
            self.runtime,
            self.dependency_graph,
            self.task,
            self.fault_injector,
            self.random,
            self.true_root_cause,
            self.surface_symptom_target,
        )
        self._update_metrics()
        self._update_alerts()  # Initial alerts based on status
        self.runtime.system_stability = self._calculate_stability()  # Correctly calculate initial stability
        self.runtime.previous_stability = self.runtime.system_stability  # Store previous stability for reward calculation
        self.runtime.is_done = False  # Track episode termination state

    def _update_metrics(self) -> None:
        # Kept as a compatibility seam for the existin    def snapshot(self) -> EnvironmentSnapshot:
        return EnvironmentSnapshot(
            runtime=deepcopy(self.runtime),
            rng_state=self.random.getstate(),
        )

    def restore(self, snapshot: EnvironmentSnapshot) -> None:
        restored = snapshot.copy()
        self.runtime = restored.runtime
        self.random.setstate(restored.rng_state)

        self.telemetry = TelemetryEngine(
            self.runtime,
            self.dependency_graph,
            self.random,
            self.RISK_THRESHOLD,
        )
        self.fault_injector = FaultInjector(
            self.runtime,
            self.dependency_graph,
            self.random,
        )
        self.observability = ObservabilityEngine(
            self.runtime,
            self.dependency_graph,
            self.task,
            self.random,
        )
        self.dynamics = DynamicsEngine(
            self.runtime,
            self.dependency_graph,
            self.task,
            self.fault_injector,
            self.random,
            self.true_root_cause,
            self.surface_symptom_target,
        )

g runtime.
        self.telemetry.refresh()

    def get_state(self) -> State:
        return State(
            services=self.runtime.services,
            logs=self.runtime.logs,
            alerts=self.runtime.alerts,
            time_step=self.runtime.time_step,
            bad_actions=self.runtime.bad_actions,
            history=self.runtime.history,
            system_health=self._calculate_system_health(),
            total_cost=self.runtime.total_cost,
            system_stability=self.runtime.system_stability,
            risky_actions_count=self.runtime.risky_actions_count,
            dependencies=self.dependencies,
            evidence=list(self.runtime.evidence),
            system_strain=self.runtime.system_strain,
            symptom_fix_count=self.runtime.symptom_fix_count,
            root_cause_step=self.runtime.root_cause_step,
            delayed_failure_count=self.runtime.delayed_failure_count,
            wasted_action_count=self.runtime.wasted_action_count,
            diagnosed_targets=list(self.runtime.diagnosed_targets),
            hidden_risk=self.runtime.hidden_risk,
            side_effect_triggered=self.runtime.side_effect_triggered
        )

    def state(self) -> State:
        """Pure read of the current state without side effects."""
        return self.get_state()

    def step(self, action: Action) -> Dict[str, Any]:
        try:
            # Check if episode has already terminated
            if hasattr(self, "is_done") and self.runtime.is_done:
                return {
                    "state": self.get_state(),
                    "reward": 0.0,
                    "done": True,
                    "info": {
                        "message": "Episode already completed. Please reset.",
                        "type": "terminated"
                    }
                }

            self.runtime.time_step += 1

            # Wasted Actions tracking
            if len(self.runtime.history) > 0:
                prev_action = self.runtime.history[-1]
                if action.action_type == prev_action.action_type and action.target == prev_action.target:
                    self.runtime.wasted_action_count += 1

            # BUG FIX 5: Track diagnosis actions more intelligently
            # Only reset consecutive counter on FIX actions, not all non-diagnosis actions
            fix_actions = [ActionType.RESTART_SERVICE, ActionType.SCALE, ActionType.ROLLBACK_SERVICE, 
                          ActionType.OPTIMIZE_DB, ActionType.ISOLATE_SERVICE, ActionType.DRAIN_TRAFFIC]
            
            if action.action_type in [ActionType.CHECK_LOGS, ActionType.CHECK_METRICS]:
                self.runtime.diagnosis_streak += 1
                self.runtime.consecutive_diagnosis_count += 1
                if self.runtime.diagnosis_streak > 3:
                    self.runtime.wasted_action_count += 1
                # Hard penalty: after 3 consecutive diagnosis actions with no fix attempt
                if self.runtime.consecutive_diagnosis_count >= 3 and not self.runtime.diagnosis_penalty_applied:
                    self.runtime.system_strain += 0.25
                    self.runtime.system_stability = max(0.0, self.runtime.system_stability - 0.15)
                    self.runtime.logs.append("WARN: Prolonged observation loop detected — system degrading without intervention")
                    self.runtime.diagnosis_penalty_applied = True
                    self.runtime.consecutive_diagnosis_count = 0  # ISSUE 3 FIX: Reset after penalty to prevent counter from climbing indefinitely
            elif action.action_type in fix_actions:
                # Reset on fix attempts (even wrong ones show intent to act)
                self.runtime.diagnosis_streak = 0
                self.runtime.consecutive_diagnosis_count = 0
                self.runtime.diagnosis_penalty_applied = False
            else:
                # IGNORE, ESCALATE, UNKNOWN don't reset the counter
                # This prevents gaming by interleaving ignore actions
                pass

            # Root Cause Detection Step tracking
            if self.runtime.root_cause_step is None and self.true_root_cause and action.target == self.true_root_cause:
                self.runtime.root_cause_step = self.runtime.time_step

            # Symptom Fix tracking
            fix_actions = [ActionType.RESTART_SERVICE, ActionType.SCALE, ActionType.ROLLBACK_SERVICE, ActionType.OPTIMIZE_DB]
            if action.action_type in fix_actions and self.true_root_cause and action.target != self.true_root_cause:
                self.runtime.symptom_fix_count += 1

            self.runtime.history.append(action)

            # Store previous state before applying action
            prev_state = self.get_state()

            # Store previous stability for reward calculation
            self.runtime.previous_stability = self.runtime.system_stability

            # Add cost
            self.runtime.total_cost += self.ACTION_COSTS.get(action.action_type, 0.0)

            # Apply action and get result
            reward_info = self._apply_action(action)

            # Safely extract action type and increment bad_actions if needed
            action_type = reward_info.get("type", "unknown")

            if action_type in ["wrong_fix", "useless_action", "unknown"]:
                self.runtime.bad_actions += 1
                self.runtime.logs.append(f"Bad action detected: {action_type}")
                self.runtime.system_stability = max(0.0, self.runtime.system_stability - 0.1)
                self.runtime.system_strain += 0.2

            # Decrement re-degradation timers
            for service_name in list(self.runtime.redegrade_timers.keys()):
                self.runtime.redegrade_timers[service_name] -= 1
                if self.runtime.redegrade_timers[service_name] <= 0:
                    target_service = self._get_service(service_name)
                    if target_service and target_service.status == ServiceStatus.UP:
                        payments_service = self._get_service("payments")
                        if payments_service and payments_service.status != ServiceStatus.UP:
                            target_service.status = ServiceStatus.DEGRADED
                            target_service.error_rate = 0.6
                            self.runtime.logs.append(f"WARN: {service_name.capitalize()} degraded again due to unresolved shared dependency")
                    del self.runtime.redegrade_timers[service_name]

            # Handle Hidden Root Cause + Delayed Consequence mechanism
            if self.runtime.fake_recovery_timer is not None:
                self.runtime.fake_recovery_timer -= 1
                if self.runtime.fake_recovery_timer <= 0:
                    self.runtime.delayed_failure_count += 1
                    if self.surface_symptom_target:
                        symptom_service = self._get_service(self.surface_symptom_target)
                        if symptom_service and symptom_service.status == ServiceStatus.UP:
                            symptom_service.status = ServiceStatus.DEGRADED
                            symptom_service.error_rate = 0.7
                            self.runtime.logs.append("WARN: service degraded again due to unresolved underlying dependency")
                            self.runtime.logs.append("WARN: recurring failure detected — root cause unresolved")
                            self.runtime.system_strain += 0.3
                    self.runtime.fake_recovery_timer = None

            # System strain decay
            self.runtime.system_strain = max(0.0, self.runtime.system_strain - 0.05)

            # Deterministic risk for OPTIMIZE_DB
            if action.action_type == ActionType.OPTIMIZE_DB:
                self.runtime.risky_actions_count += 1
                if self.runtime.system_stability < 0.7 or self.runtime.risky_actions_count > 1:
                    penalty = 0.1 * self.runtime.risky_actions_count
                    self.runtime.system_stability = max(0.0, self.runtime.system_stability - penalty)
                    self.runtime.system_strain += 0.1

            # Apply logic updates
            self._apply_cascading_failures()
            self._evolve_env()
            self._update_metrics()
            self._update_alerts()
            self.runtime.system_stability = self._calculate_stability()
            self._update_logs(action, reward_info)

            # BUG FIX 1: Read bad_actions_limit from task definition instead of hardcoded value
            bad_actions_limit = self.task.failure_conditions.get("bad_actions_limit", 2)
            stability_threshold = self.task.failure_conditions.get("system_stability_below", 0.3)
            
            done = (
                self.runtime.time_step >= self.max_steps or
                self.runtime.bad_actions > bad_actions_limit or
                self.runtime.system_stability < stability_threshold or
                self._all_services_up()
            )

            # Update episode termination state
            self.runtime.is_done = done

            # Counterfactual Consequence System logic
            if self.runtime.hidden_risk >= self.RISK_THRESHOLD and not self.runtime.side_effect_triggered:
                self.runtime.side_effect_triggered = True
                healthy_services = [s for s in self.runtime.services if s.status == ServiceStatus.UP]
                if healthy_services:
                    target = self.random.choice(healthy_services)
                    target.status = ServiceStatus.DEGRADED
                    target.error_rate = 0.5
                    self.runtime.logs.append(f"CRITICAL: Unexpected degradation in {target.name} due to system-wide instability")
                    self.runtime.logs.append("INFO: Root cause analysis indicates cascading instability from previous risky actions")

            # Subtle signals based on hidden_risk
            if self.runtime.hidden_risk > (self.RISK_THRESHOLD * 0.4) and self.runtime.time_step % 2 == 0:
                instability_logs = [
                    "WARN: System entropy increasing beyond normal operating parameters",
                    "INFO: Minor synchronization delays detected in secondary cluster",
                    "WARN: Resource contention observed in shared infrastructure"
                ]
                self.runtime.logs.append(self.random.choice(instability_logs))

            # ISSUE 2 FIX: Lucky guess should NOT get extra steps - penalize instead
            if self._all_services_up():
                if reward_info.get("is_lucky_guess"):
                    # DO NOT end episode yet
                    done = False
                    self.runtime.logs.append("Recovery without diagnosis — continue investigation required")
                else:
                    done = True

            # Calculate meaningful reward signal
            reward = self._calculate_reward(reward_info, action)

            # Get state after applying action
            curr_state = self.get_state()

            # Add score breakdown if episode is done
            if done:
                score_result = self.grader.grade_episode(curr_state, self.task)
                reward_info["score_breakdown"] = {
                    "success_score": score_result.root_cause_score,
                    "efficiency_score": score_result.efficiency_score,
                    "cost_efficiency_score": score_result.cost_efficiency_score,
                    "stability_score": score_result.stability_score,
                    "sequence_score": score_result.sequence_score,
                    "final_score": score_result.final_score,
                    "sequence_bonus_applied": score_result.sequence_bonus_applied,
                    "wrong_order_penalty_applied": score_result.wrong_order_penalty_applied
                }
            else:
                score_result = None
                reward_info["score_breakdown"] = None

            # Store trajectory step
            self.runtime.state_history.append({
                "action": action,
                "state_before": prev_state,
                "state_after": curr_state,
                "reward": reward,
                "reward_info": reward_info
            })

            # Add diagnostic metrics to info
            reward_info.update({
                "symptom_fixes": self.runtime.symptom_fix_count,
                "root_cause_step": self.runtime.root_cause_step,
                "delayed_failures": self.runtime.delayed_failure_count,
                "wasted_actions": self.runtime.wasted_action_count,
                "failure_type": score_result.failure_type if score_result else None
            })

            return {
                "state": curr_state,
                "reward": reward,
                "done": done,
                "info": reward_info
            }
        except Exception as e:
            print(f"Error in IncidentEnv.step: {e}")
            return {
                "state": self.get_state(),
                "reward": -0.5,
                "done": False,
                "info": {"type": "error", "message": str(e)}
            }

    def _calculate_reward(self, reward_info: Dict[str, Any], action: Action) -> float:
        """Calculate meaningful reward signal based on action outcomes and system state."""
        reward = self.grader.calculate_step_reward(action, reward_info, self)

        # Apply lucky guess penalty (50% reduction)
        if reward_info.get("is_lucky_guess"):
            reward *= 0.5
            self.runtime.logs.append(f"Lucky guess detected on {action.target}! Reward reduced.")

        # Risk build-up from other actions
        if reward_info.get("type") == "wrong_fix":
            self.runtime.hidden_risk += 0.3
        elif action.action_type == ActionType.SCALE and reward_info.get("type") != "correct_fix":
            self.runtime.hidden_risk += 0.25
        elif action.action_type == ActionType.OPTIMIZE_DB and reward_info.get("type") == "useless_action":
            self.runtime.hidden_risk += 0.2

        # Lucky guesses increase hidden risk
        if reward_info.get("is_lucky_guess"):
            self.runtime.hidden_risk += 0.3

        # Successful fixes SLIGHTLY reduce risk
        if reward_info.get("type") == "correct_fix" and not reward_info.get("is_lucky_guess"):
            self.runtime.hidden_risk = max(0.0, self.runtime.hidden_risk - 0.1)

        # FIX 4: Additional reward penalty for observation loop (no fix after 3 diagnoses)
        if self.runtime.consecutive_diagnosis_count >= 3:
            reward -= 0.15

        # Time penalty per step
        reward -= 0.05

        # Bonus for stability improvement
        stability_change = self.runtime.system_stability - self.runtime.previous_stability
        if stability_change > 0:
            reward += 0.2

        # Bonus for all services UP
        if self._all_services_up() and not reward_info.get("is_lucky_guess"):
            reward += 0.3

        # Penalty for significant system strain increase
        strain_change = self.runtime.system_strain - self.runtime.previous_strain
        if strain_change > 0.2:
            reward -= 0.2

        # Update previous_strain for next step
        self.runtime.previous_strain = self.runtime.system_strain

        # Penalty for excessive bad actions
        if self.runtime.bad_actions > 2:
            reward -= 0.3

        # Clip reward between [-1, 1]
        reward = max(-1.0, min(1.0, reward))

        return reward

    def _calculate_stability(self) -> float:
        service_scores = []
        for s in self.runtime.services:
            if s.status == ServiceStatus.UP:
                service_scores.append(1.0)
            elif s.status == ServiceStatus.DEGRADED:
                service_scores.append(0.5)
            else:
                service_scores.append(0.0)

        base_stability = sum(service_scores) / len(self.runtime.services) if self.runtime.services else 1.0

        critical_alerts = sum(1 for a in self.runtime.alerts if "CRITICAL" in a or "ERROR" in a)
        stability = base_stability - (0.1 * critical_alerts)

        if any(s.name == "db" and s.status == ServiceStatus.UP for s in self.runtime.services):
            stability += 0.1

        stability -= (0.1 * self.runtime.system_strain)

        if stability > 0.7:
            stability = 0.7 + (stability - 0.7) * 0.5

        return max(0.0, min(1.0, stability))

    def _get_service(self, name: str) -> Service:
        return next((s for s in self.runtime.services if s.name == name), None)

    def _apply_cascading_failures(self) -> None:
        self.dynamics._apply_cascading_failures()

    def _update_logs(self, action: Action, reward_info: Dict[str, Any]) -> None:
        self.observability.record_action(action, reward_info)

    def _apply_action(self, action: Action) -> Dict[str, Any]:
        target_service = next((s for s in self.runtime.services if s.name == action.target), None)

        # Resolution policy comes from the scenario definition, not its task ID.
        resolution = matching_resolution(self.task, action)
        if self.true_root_cause and action.target == self.true_root_cause and resolution:
            missing = missing_diagnosis(self.task, self.runtime.history)
            if missing:
                if target_service:
                    target_service.error_rate = max(0.4, target_service.error_rate - 0.3)
                self.runtime.logs.append(
                    f"{action.target.capitalize()} resolution blocked: required diagnosis incomplete"
                )
                return {
                    "type": "partial_fix",
                    "target": action.target,
                    "missing_diagnosis": missing,
                }

            self.runtime.fake_recovery_timer = None
            self.runtime.root_cause_fixed = True

            if target_service:
                target_service.status = ServiceStatus.UP
                target_service.error_rate = 0.01

            if self.surface_symptom_target:
                symptom_service = self._get_service(self.surface_symptom_target)
                if symptom_service:
                    symptom_service.status = ServiceStatus.UP
                    symptom_service.error_rate = 0.01

            is_lucky_guess = action.target not in self.runtime.diagnosed_targets
            return {
                "type": "correct_fix",
                "target": action.target,
                "root_cause_fixed": True,
                "is_lucky_guess": is_lucky_guess,
            }

        if (
            self.surface_symptom_target
            and action.target == self.surface_symptom_target
            and is_fix_action(action)
            and target_service
            and target_service.status != ServiceStatus.UP
        ):
            target_service.status = ServiceStatus.UP
            target_service.error_rate = 0.05
            self.runtime.fake_recovery_timer = 2
            return {
                "type": "temporary_fix",
                "target": action.target,
                "surface_symptom_fixed": True,
            }

        root_cause_service = self._get_service(self.true_root_cause) if self.true_root_cause else None

        if (
            root_cause_service
            and root_cause_service.status != ServiceStatus.UP
            and action.target != root_cause_service.name
            and is_fix_action(action)
        ):
            wrong_target_count = sum(
                1
                for past_action in self.runtime.history
                if past_action.target != root_cause_service.name
                and is_fix_action(past_action)
            )
            if wrong_target_count >= 2:
                self.runtime.system_strain += 0.15
                self.runtime.logs.append(
                    "Repeated incorrect mitigation detected - focusing on symptoms instead of root cause"
                )

        # A non-declared fix on the true root cause may produce only partial recovery.
        if (
            self.true_root_cause
            and action.target == self.true_root_cause
            and is_fix_action(action)
            and target_service
            and action.action_type != ActionType.CHECK_LOGS
        ):
            if target_service.status != ServiceStatus.UP:
                target_service.status = ServiceStatus.DEGRADED
                if target_service.name not in self.runtime.partial_fixes:
                    self.runtime.partial_fixes.append(target_service.name)
                return {"type": "partial_fix", "target": action.target}

        if action.action_type == ActionType.RESTART_SERVICE:
            if not target_service:
                return {"type": "unknown", "target": action.target}

            for root, dependents in self.dependency_graph.items():
                if action.target in dependents:
                    upstream = next((s for s in self.runtime.services if s.name == root), None)
                    if upstream and upstream.status != ServiceStatus.UP:
                        return {"type": "wrong_fix", "target": action.target}

            if target_service.status == ServiceStatus.DOWN:
                target_service.status = ServiceStatus.UP
                is_lucky_guess = action.target not in self.runtime.diagnosed_targets
                return {"type": "correct_fix", "target": action.target, "is_lucky_guess": is_lucky_guess}
            elif target_service.status == ServiceStatus.DEGRADED:
                return {"type": "wrong_fix", "target": action.target}
            else:
                return {"type": "useless_action", "target": action.target}

        elif action.action_type == ActionType.ROLLBACK_SERVICE:
            if not target_service:
                return {"type": "unknown", "target": action.target}

            self.runtime.system_stability = max(0.0, self.runtime.system_stability - 0.1)
            return {"type": "wrong_fix", "target": action.target}

        elif action.action_type == ActionType.ISOLATE_SERVICE:
            if not target_service:
                return {"type": "unknown", "target": action.target}

            if target_service.name not in self.runtime.isolated_services:
                self.runtime.isolated_services.append(target_service.name)
                return {"type": "tactical_move", "target": action.target}
            else:
                return {"type": "useless_action", "target": action.target}

        elif action.action_type == ActionType.DRAIN_TRAFFIC:
            if not target_service:
                return {"type": "unknown", "target": action.target}

            if target_service.name not in self.runtime.drained_services:
                self.runtime.drained_services.append(target_service.name)
                return {"type": "tactical_move", "target": action.target}
            else:
                return {"type": "useless_action", "target": action.target}

        elif action.action_type == ActionType.RESTORE_TRAFFIC:
            if not target_service:
                return {"type": "unknown", "target": action.target}

            if target_service.name in self.runtime.drained_services:
                self.runtime.drained_services.remove(target_service.name)
                return {"type": "tactical_move", "target": action.target}
            else:
                return {"type": "wrong_fix", "target": action.target}

        elif action.action_type == ActionType.ESCALATE:
            self.runtime.is_done = True
            return {"type": "escalate", "target": "all"}

        elif action.action_type == ActionType.SCALE:
            if not target_service:
                return {"type": "unknown", "target": action.target}

            if root_cause_service and root_cause_service.status != ServiceStatus.UP and action.target != root_cause_service.name:
                self.runtime.total_cost += 2.0
                self.runtime.system_strain += 0.1

            if target_service.status == ServiceStatus.DEGRADED:
                target_service.status = ServiceStatus.UP
                is_lucky_guess = action.target not in self.runtime.diagnosed_targets
                return {"type": "correct_fix", "target": action.target, "is_lucky_guess": is_lucky_guess}
            else:
                return {"type": "useless_action", "target": action.target}

        elif action.action_type == ActionType.OPTIMIZE_DB:
            if target_service and target_service.name == "db" and target_service.status == ServiceStatus.DEGRADED:
                target_service.status = ServiceStatus.UP
                is_lucky_guess = action.target not in self.runtime.diagnosed_targets
                return {"type": "correct_fix", "target": action.target, "is_lucky_guess": is_lucky_guess}
            elif self.task.id == "hard-bad-deployment" and target_service and target_service.name == "db":
                # FIX 1: Honeypot — DB is healthy, optimizing it makes things worse
                self.runtime.system_strain += 0.3
                self.runtime.system_stability = max(0.0, self.runtime.system_stability - 0.15)
                auth_service = self._get_service("auth")
                if auth_service:
                    auth_service.error_rate = min(1.0, auth_service.error_rate + 0.1)
                self.runtime.logs.append("DB: INFO - optimize_db completed, no issues found in database layer")
                self.runtime.logs.append("Auth service: ERROR - error rate unchanged after DB optimization — DB is not the cause")
                return {"type": "wrong_fix", "target": action.target}
            else:
                return {"type": "useless_action", "target": action.target}

        elif action.action_type == ActionType.CHECK_LOGS or action.action_type == ActionType.CHECK_METRICS:
            self.runtime.diagnosed_targets.add(action.target)
            return {"type": "diagnosis", "target": action.target}

        elif action.action_type == ActionType.IGNORE:
            return {"type": "ignore", "target": action.target}

        return {"type": "unknown", "target": action.target}

    def _evolve_env(self) -> None:
        self.dynamics._evolve_env()

    def _autonomous_degradation(self):
        return self.dynamics._autonomous_degradation()

    def _all_services_up(self) -> bool:
        # BUG FIX 2: Only block termination if timer is actively counting down (> 0)
        # None means timer expired or was never set, so don't block
        if self.runtime.fake_recovery_timer is not None and self.runtime.fake_recovery_timer > 0:
            return False
        return all(s.status == ServiceStatus.UP for s in self.runtime.services)

    def _calculate_system_health(self) -> float:
        up_services = sum(1 for s in self.runtime.services if s.status == ServiceStatus.UP)
        return up_services / len(self.runtime.services) if self.runtime.services else 0.0

    def _update_alerts(self) -> None:
        self.observability.refresh_alerts()

