"""
Structured LLM provider error handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMProviderError(RuntimeError):
    """Stable error shape for upstream model provider failures."""

    message: str
    code: str = "provider_error"
    error_type: str = "provider_error"
    status_code: Optional[int] = None
    request_id: Optional[str] = None
    provider: str = "dashscope"
    retry_after_seconds: Optional[float] = None

    def __str__(self) -> str:
        parts = [self.message]
        if self.code:
            parts.append(f"code={self.code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " | ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe diagnostic payload without secrets."""
        return {
            "available": False,
            "provider": self.provider,
            "status_code": self.status_code,
            "code": self.code,
            "type": self.error_type,
            "message": self.message,
            "request_id": self.request_id,
            "retry_after_seconds": self.retry_after_seconds,
        }


def _payload_from_exception(exc: Exception) -> dict[str, Any]:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        return body

    response = getattr(exc, "response", None)
    if response is not None:
        try:
            data = response.json()
            if isinstance(data, dict):
                return data
        except Exception:
            return {}

    return {}


def _retry_after_from_exception(exc: Exception) -> Optional[float]:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    retry_after = None
    try:
        retry_after = headers.get("retry-after") or headers.get("Retry-After")
    except Exception:
        retry_after = None
    if retry_after is None:
        return None
    try:
        return max(float(retry_after), 0)
    except (TypeError, ValueError):
        return None


def classify_llm_exception(exc: Exception, provider: str = "dashscope") -> LLMProviderError:
    """Convert SDK exceptions into a stable provider diagnostic."""
    payload = _payload_from_exception(exc)
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else payload

    status_code = getattr(exc, "status_code", None)
    request_id = (
        getattr(exc, "request_id", None)
        or payload.get("request_id")
        or payload.get("id")
    )
    retry_after_seconds = _retry_after_from_exception(exc)
    code = str(error_payload.get("code") or getattr(exc, "code", None) or "provider_error")
    error_type = str(error_payload.get("type") or getattr(exc, "type", None) or "provider_error")
    message = str(error_payload.get("message") or getattr(exc, "message", None) or str(exc))

    if code == "Arrearage" or error_type == "Arrearage":
        message = "模型供应商拒绝请求：DashScope/百炼账号欠费或账户状态异常，请处理账单后重试。"
    elif status_code == 401:
        code = code if code != "provider_error" else "unauthorized"
        error_type = error_type if error_type != "provider_error" else "authentication_error"
        message = "模型供应商认证失败：请检查 LLM_API_KEY 是否有效。"
    elif status_code == 429:
        code = code if code != "provider_error" else "rate_limited"
        error_type = error_type if error_type != "provider_error" else "rate_limit_error"
        message = "模型供应商限流：请求过多或额度不足，请稍后重试。"

    return LLMProviderError(
        message=message,
        code=code,
        error_type=error_type,
        status_code=status_code,
        request_id=str(request_id) if request_id else None,
        provider=provider,
        retry_after_seconds=retry_after_seconds,
    )
