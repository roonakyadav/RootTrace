from models.schemas import Action, ActionType, ServiceStatus, State


class DependencyAwareAgent:
    name = "dependency-aware"

    def reset(self, seed: int | None = None) -> None:
        pass

    def act(self, state: State) -> Action:
        services_by_name = {service.name: service for service in state.services}

        upstream_of = {}
        for root, dependents in state.dependencies.items():
            for dependent in dependents:
                upstream_of[dependent] = root

        unhealthy = [
            service for service in state.services
            if service.status != ServiceStatus.UP
        ]
        if not unhealthy:
            return Action(action_type=ActionType.IGNORE, target="none")

        root_candidates = []
        for service in unhealthy:
            upstream_name = upstream_of.get(service.name)
            upstream = services_by_name.get(upstream_name) if upstream_name else None
            if upstream is None or upstream.status == ServiceStatus.UP:
                root_candidates.append(service)

        target = root_candidates[0] if root_candidates else unhealthy[0]

        if target.name == "db" and target.status == ServiceStatus.DEGRADED:
            return Action(action_type=ActionType.OPTIMIZE_DB, target="db")
        if target.status == ServiceStatus.DOWN:
            return Action(action_type=ActionType.RESTART_SERVICE, target=target.name)
        if target.status == ServiceStatus.DEGRADED:
            return Action(action_type=ActionType.SCALE, target=target.name)

        return Action(action_type=ActionType.IGNORE, target="none")

    def decide_action(self, state: State) -> Action:
        # Backward-compatible name used by older scripts.
        return self.act(state)
