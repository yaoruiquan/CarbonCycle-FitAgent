from app.llm.errors import classify_llm_exception


class FakeProviderException(Exception):
    status_code = 400
    body = {
        "error": {
            "message": "Access denied",
            "type": "Arrearage",
            "code": "Arrearage",
        },
        "request_id": "req-1",
    }


def test_classify_arrearage_error():
    error = classify_llm_exception(FakeProviderException("raw provider error"))

    assert error.code == "Arrearage"
    assert error.error_type == "Arrearage"
    assert error.status_code == 400
    assert error.request_id == "req-1"
    assert "欠费" in error.message
    assert error.to_dict()["available"] is False


def test_classify_error_preserves_provider():
    error = classify_llm_exception(FakeProviderException("raw provider error"), provider="gemini")

    assert error.provider == "gemini"
    assert error.to_dict()["provider"] == "gemini"


class FakeResponse:
    headers = {"retry-after": "12.5"}


class FakeRateLimitException(Exception):
    status_code = 429
    response = FakeResponse()
    body = {"error": {"message": "Too many requests"}}


def test_classify_rate_limit_includes_retry_after():
    error = classify_llm_exception(FakeRateLimitException("rate limited"), provider="gemini")

    assert error.code == "rate_limited"
    assert error.retry_after_seconds == 12.5
    assert error.to_dict()["retry_after_seconds"] == 12.5
