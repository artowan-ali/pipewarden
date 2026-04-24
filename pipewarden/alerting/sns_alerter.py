from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from pipewarden.alerting.base import BaseAlerter, AlertContext


@dataclass
class SNSAlerter(BaseAlerter):
    """Alerter that publishes pipeline health notifications to AWS SNS."""

    topic_arn: str = ""
    region_name: str = "us-east-1"
    subject: str = "PipeWarden Alert"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    # Injected in tests to avoid real boto3 calls
    _client: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.topic_arn:
            raise ValueError("SNSAlerter requires a 'topic_arn'.")

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "boto3 is required for SNSAlerter. "
                "Install it with: pip install boto3"
            ) from exc
        kwargs = {"region_name": self.region_name}
        if self.aws_access_key_id and self.aws_secret_access_key:
            kwargs["aws_access_key_id"] = self.aws_access_key_id
            kwargs["aws_secret_access_key"] = self.aws_secret_access_key
        return boto3.client("sns", **kwargs)

    def _build_message(self, context: AlertContext) -> str:
        status = "HEALTHY" if context.is_healthy() else "UNHEALTHY"
        lines = [
            f"Pipeline status: {status}",
            f"Total checks : {len(context.results)}",
            f"Failed        : {len(context.failed)}",
            f"Warnings      : {len(context.warned)}",
            "",
        ]
        for result in context.failed + context.warned:
            lines.append(f"  [{result.status.value.upper()}] {result.check_name}: {result.message}")
        return "\n".join(lines)

    def send(self, context: AlertContext) -> None:
        if context.is_healthy():
            return
        client = self._get_client()
        message = self._build_message(context)
        client.publish(
            TopicArn=self.topic_arn,
            Subject=self.subject,
            Message=message,
        )
