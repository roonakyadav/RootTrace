from agents.rule_based import DependencyAwareAgent


# Backward-compatible export for existing scripts.
BaselineAgent = DependencyAwareAgent

__all__ = ["BaselineAgent"]
