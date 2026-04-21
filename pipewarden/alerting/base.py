"""Base classes and types for the alerting system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from pipewarden.checks.base import CheckResult, CheckStatus


@dataclass
class AlertContext:
    """Contextual information passed to alert handlers."""

    pipeline_name: str
    results: List[CheckResult]
    failed: List[CheckResult] = field(init=False)
    warned: List[CheckResult] = field(init=False)

    def __post_init__(self) -> None:
        self.failed = [
            r for r in self.results if r.status == CheckStatus.FAILED
        ]
        self.warned = [
            r for r in self.results if r.status == CheckStatus.WARNING
        ]

    @property
    def is_healthy(self) -> bool:
        return len(self.failed) == 0


class BaseAlerter(ABC):
    """Abstract base class for all alerters."""

    @abstractmethod
    def send(self, context: AlertContext) -> None:
        """Send an alert based on the given context."""
        ...

    def should_alert(self, context: AlertContext) -> bool:
        """Return True if an alert should be sent. Override to customise."""
        return not context.is_healthy

    def notify(self, context: AlertContext) -> None:
        """Conditionally send an alert."""
        if self.should_alert(context):
            self.send(context)
