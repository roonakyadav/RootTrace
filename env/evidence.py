from __future__ import annotations

from itertools import count

from env.runtime import RuntimeState
from models.schemas import Evidence, EvidenceType


class EvidenceStore:
    def __init__(self, runtime: RuntimeState) -> None:
        self.runtime = runtime
        self._sequence = count()

    def add(
        self,
        evidence_type: EvidenceType,
        content: str,
        timestamp: int,
        reliability: float,
        source: str | None = None,
    ) -> Evidence:
        source_name = source or self._infer_source(content)
        evidence = Evidence(
            id=f"{evidence_type.value}-{timestamp}-{next(self._sequence)}",
            type=evidence_type,
            source=source_name,
            content=content,
            timestamp=timestamp,
            reliability=max(0.0, min(1.0, reliability)),
        )
        self.runtime.evidence.append(evidence)
        return evidence

    def ingest_log(self, content: str, timestamp: int, reliability: float = 0.7) -> Evidence:
        return self.add(EvidenceType.LOG, content, timestamp, reliability)

    def ingest_alert(self, content: str, timestamp: int, reliability: float = 0.9) -> Evidence:
        return self.add(EvidenceType.ALERT, content, timestamp, reliability)

    @staticmethod
    def _infer_source(content: str) -> str:
        if ":" in content:
            prefix = content.split(":", 1)[0].strip()
            if prefix:
                return prefix.lower()
        return "system"
