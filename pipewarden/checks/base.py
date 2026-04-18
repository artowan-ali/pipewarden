from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    check_name: str
    status: CheckStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None

    def passed(self) -> bool:
        return self.status == CheckStatus.PASSED

    def failed(self) -> bool:
        return self.status == CheckStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
        }


class BaseCheck(ABC):
    """Abstract base class for all pipeline health checks."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    def run(self) -> CheckResult:
        """Execute the check and return a result."""
        ...

    def _make_result(
        self,
        status: CheckStatus,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> CheckResult:
        return CheckResult(
            check_name=self.name,
            status=status,
            message=message,
            details=details or {},
        )
