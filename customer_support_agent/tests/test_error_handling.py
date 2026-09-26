import httpx
import pytest

from openai import (
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
)


def make_request() -> httpx.Request:
    return httpx.Request(
        "POST",
        "https://api.openai.com/v1/responses",
    )


def make_response(status_code: int) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        request=make_request(),
        json={
            "error": {
                "message": "test error",
                "type": "test_error",
            }
        },
    )


class FakeAgent:
    """
    Minimal fake for testing exception propagation at the agent boundary.

    This intentionally does not test main() itself.
    """

    def __init__(self, exception: Exception):
        self.exception = exception

    def run_stream(self, *args, **kwargs):
        raise self.exception


def test_agent_rate_limit_error_propagates():
    error = RateLimitError(
        "OpenAI API rate limit reached.",
        response=make_response(429),
        body={
            "error": {
                "message": "rate limited",
                "type": "rate_limit_error",
            }
        },
    )

    agent = FakeAgent(error)

    with pytest.raises(RateLimitError) as exc_info:
        agent.run_stream(
            "test request",
            deps=None,
        )

    assert exc_info.value is error
    assert exc_info.value.status_code == 429


def test_agent_api_connection_error_propagates():
    error = APIConnectionError(
        message="Unable to connect to OpenAI API.",
        request=make_request(),
    )

    agent = FakeAgent(error)

    with pytest.raises(APIConnectionError) as exc_info:
        agent.run_stream(
            "test request",
            deps=None,
        )

    assert exc_info.value is error
    assert exc_info.value.message == "Unable to connect to OpenAI API."


def test_agent_authentication_error_propagates():
    error = AuthenticationError(
        "Authentication failed.",
        response=make_response(401),
        body={
            "error": {
                "message": "invalid API key",
                "type": "authentication_error",
            }
        },
    )

    agent = FakeAgent(error)

    with pytest.raises(AuthenticationError) as exc_info:
        agent.run_stream(
            "test request",
            deps=None,
        )

    assert exc_info.value is error
    assert exc_info.value.status_code == 401


def test_rate_limit_error_remains_rate_limit_error():
    error = RateLimitError(
        "OpenAI API rate limit reached.",
        response=make_response(429),
        body={
            "error": {
                "message": "rate limited",
                "type": "rate_limit_error",
            }
        },
    )

    agent = FakeAgent(error)

    with pytest.raises(RateLimitError):
        agent.run_stream(
            "test request",
            deps=None,
        )


def test_api_connection_error_remains_api_connection_error():
    error = APIConnectionError(
        message="Unable to connect to OpenAI API.",
        request=make_request(),
    )

    agent = FakeAgent(error)

    with pytest.raises(APIConnectionError):
        agent.run_stream(
            "test request",
            deps=None,
        )


def test_authentication_error_remains_authentication_error():
    error = AuthenticationError(
        "Authentication failed.",
        response=make_response(401),
        body={
            "error": {
                "message": "invalid API key",
                "type": "authentication_error",
            }
        },
    )

    agent = FakeAgent(error)

    with pytest.raises(AuthenticationError):
        agent.run_stream(
            "test request",
            deps=None,
        )