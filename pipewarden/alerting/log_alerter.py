"""Simple alerter that writes alert details to a Python logger."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class LogAlerter(BaseAlerter):
    """Emits alert information via the standard logging module."""

    logger_name: str = "pipewarden.alerts"
    level: int = logging.ERROR
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(self.logger_name)

    def send(self, context: AlertContext) -> None:
        header = (
            f"[PipeWarden] Pipeline '{context.pipeline_name}' alert — "
            f"{len(context.failed)} failed, {len(context.warned)} warned."
        )
        self._logger.log(self.level, header)

        for result in context.failed:
            self._logger.log(
                self.level,
                "  FAILED  %s: %s",
                result.check_name,
                result.details,
            )

        for result in context.warned:
            self._logger.log(
                logging.WARNING,
                "  WARNING %s: %s",
                result.check_name,
                result.details,
            )
