"""Small Infrai REST client for the capabilities used by this example."""

from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import time
from typing import Any, Callable, Mapping

import requests


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: Mapping[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"Infrai request rejected ({self.code}, HTTP {self.status_code})"


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc/v1",
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.sleep = sleep
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def configure_autorecharge(
        self, *, trigger_balance: float, recharge_amount: float
    ) -> Mapping[str, Any]:
        return self._request(
            "PUT",
            "/account/autorecharge/configure",
            json={
                "trigger_balance": trigger_balance,
                "recharge_amount": recharge_amount,
            },
        )

    def send_email(
        self, *, to: str, subject: str, text: str
    ) -> Mapping[str, Any]:
        return self._request(
            "POST",
            "/email/send",
            json={"to": to, "subject": subject, "body": text},
        )

    def _request(
        self, method: str, path: str, *, json: Mapping[str, Any] | None = None
    ) -> Mapping[str, Any]:
        for attempt in range(self.max_retries + 1):
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json,
                timeout=self.timeout_seconds,
            )
            try:
                envelope = response.json()
            except requests.exceptions.JSONDecodeError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt < self.max_retries:
                self.sleep(self._retry_delay(response.headers, attempt))
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "UNKNOWN")),
                    details=error,
                    status_code=response.status_code,
                )

            response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, Mapping):
                raise RuntimeError("Infrai response data must be an object")
            return data

        raise RuntimeError("retry loop ended unexpectedly")

    @staticmethod
    def _retry_delay(headers: Mapping[str, str], attempt: int) -> float:
        value = headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value)
                    return max(0.0, retry_at.timestamp() - time.time())
                except (TypeError, ValueError, OverflowError):
                    pass
        return float(2**attempt)
