from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def passed(self) -> bool:
        return self.status == CheckStatus.PASSED

    def failed(self) -> bool:
        return self.status == CheckStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


class BaseCheck:
    name: str = "base_check"

    def run(self, rows: list[dict[str, Any]]) -> CheckResult:
        raise NotImplementedError


def passed(name: str, details: Optional[dict] = None) -> CheckResult:
    return CheckResult(
        name=name,
        status=CheckStatus.PASSED,
        message="Check passed",
        details=details or {},
    )


def failed(name: str, message: str, details: Optional[dict] = None) -> CheckResult:
    return CheckResult(
        name=name,
        status=CheckStatus.FAILED,
        message=message,
        details=details or {},
    )


def warned(name: str, message: str, details: Optional[dict] = None) -> CheckResult:
    return CheckResult(
        name=name,
        status=CheckStatus.WARNING,
        message=message,
        details=details or {},
    )
