from __future__ import annotations

from abc import ABC, abstractmethod

from packages.domain import AnalysisResult, Document


class BaseAgent(ABC):
    @abstractmethod
    def analyze(self, document: Document) -> AnalysisResult:
        raise NotImplementedError

