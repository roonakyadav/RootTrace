from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Mapping, Tuple


@dataclass(frozen=True)
class DependencyGraph:
    # Directed graph of service dependencies.
    # Edges use service -> dependents so cascading effects propagate downstream.
    # The graph is independent of a running incident episode.

    edges: Mapping[str, Tuple[str, ...]]

    @classmethod
    def from_mapping(cls, edges: Mapping[str, Iterable[str]]) -> "DependencyGraph":
        normalized = {
            str(source): tuple(dict.fromkeys(str(target) for target in targets))
            for source, targets in edges.items()
        }
        return cls(normalized)

    @classmethod
    def for_task(cls, task) -> "DependencyGraph":
        if getattr(task, "dependencies", None):
            return cls.from_mapping(task.dependencies)

        # Compatibility fallback for older Task objects.
        return cls.from_mapping({
            "auth": ("frontend",),
            "payments": ("frontend",),
        })

    def items(self):
        return self.edges.items()

    def as_dict(self) -> Dict[str, List[str]]:
        return {source: list(targets) for source, targets in self.edges.items()}

    def dependents_of(self, service: str) -> Tuple[str, ...]:
        return self.edges.get(service, ())

    def upstreams_of(self, service: str) -> Tuple[str, ...]:
        return tuple(
            source
            for source, targets in self.edges.items()
            if service in targets
        )

    def roots(self) -> Tuple[str, ...]:
        targets = {target for values in self.edges.values() for target in values}
        return tuple(source for source in self.edges if source not in targets)

    def leaves(self) -> Tuple[str, ...]:
        return tuple(source for source, targets in self.edges.items() if not targets)

    def services(self) -> Tuple[str, ...]:
        names = set(self.edges)
        names.update(target for values in self.edges.values() for target in values)
        return tuple(sorted(names))

    def transitive_dependents_of(self, service: str) -> Tuple[str, ...]:
        seen = set()
        queue = list(self.dependents_of(service))
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            queue.extend(self.dependents_of(current))
        return tuple(sorted(seen))

    def transitive_upstreams_of(self, service: str) -> Tuple[str, ...]:
        seen = set()
        queue = list(self.upstreams_of(service))
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            queue.extend(self.upstreams_of(current))
        return tuple(sorted(seen))
