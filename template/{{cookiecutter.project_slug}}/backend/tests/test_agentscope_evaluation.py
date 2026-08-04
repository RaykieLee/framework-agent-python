{%- if cookiecutter.use_agentscope %}
"""Deterministic and mocked-HTTP tests for AgentScope runtime evaluation."""

import asyncio

import httpx
import pytest

from app.services.agentscope_evaluation import (
    DEFAULT_SCENARIOS,
    DeterministicMockModel,
    EvaluationRunner,
    GLMChatModel,
    GLMEvaluatorConfig,
    LiveEvaluatorDisabled,
    LiveEvaluatorNotConfigured,
    MalformedModelResponse,
    RateLimitError,
)


@pytest.mark.anyio
async def test_mock_suite_is_repeatable_and_meets_quality_gate() -> None:
    model = DeterministicMockModel()
    runner = EvaluationRunner(model)
    first = await runner.run(tenant_id="tenant-a")
    second = await runner.run(tenant_id="tenant-a")

    assert first.to_json() == second.to_json()
    assert first.quality_gate_passed
    assert first.category_rate("semantic") == 1.0
    assert model.seen_tenants == ["tenant-a"] * (len(DEFAULT_SCENARIOS) * 2)


def test_report_is_redacted_and_stable() -> None:
    report = asyncio.run(EvaluationRunner(DeterministicMockModel()).run())
    serialized = report.to_json()
    assert "tenant-b-secret" not in serialized
    assert "api_key" not in serialized
    assert serialized == report.to_json()


def test_live_configuration_is_environment_only_and_redacted() -> None:
    config = GLMEvaluatorConfig.from_env(
        {
            "AGENTSCOPE_EVAL_ENABLED": "true",
            "AGENTSCOPE_EVAL_BASE_URL": "https://example.test/v4/",
            "AGENTSCOPE_EVAL_MODEL": "glm-test",
            "AGENTSCOPE_EVAL_API_KEY": "secret-value",
        }
    )
    assert config.base_url == "https://example.test/v4"
    assert config.redacted()["api_key_configured"] is True
    assert "secret-value" not in repr(config.redacted())

    with pytest.raises(LiveEvaluatorDisabled):
        GLMEvaluatorConfig().validate()
    with pytest.raises(LiveEvaluatorNotConfigured):
        GLMEvaluatorConfig(enabled=True).validate()


@pytest.mark.anyio
async def test_mocked_http_success_and_auth_header() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers["authorization"]
        seen["body"] = request.read()
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "helpful"}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = GLMChatModel(
        GLMEvaluatorConfig(enabled=True, api_key="test-secret"),
        client=client,
    )
    try:
        assert await model.complete("hello", tenant_id="tenant-a") == "helpful"
    finally:
        await client.aclose()
    assert seen["authorization"] == "Bearer test-secret"
    assert b'"model":"glm-5.2"' in seen["body"]  # type: ignore[operator]


@pytest.mark.anyio
async def test_timeout_retries_then_fails_without_secret_in_error() -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out")

    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = GLMChatModel(
        GLMEvaluatorConfig(enabled=True, api_key="test-secret", max_retries=2),
        client=client,
        sleep=fake_sleep,
    )
    try:
        with pytest.raises(Exception, match="failed after retries"):
            await model.complete("hello", tenant_id="tenant-a")
    finally:
        await client.aclose()
    assert calls == 3
    assert sleeps == [0.25, 0.5]


@pytest.mark.anyio
async def test_rate_limit_honors_retry_after_and_raises_after_budget() -> None:
    calls = 0
    sleeps: list[float] = []

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"retry-after": "0.5"})

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = GLMChatModel(
        GLMEvaluatorConfig(enabled=True, api_key="test-secret", max_retries=1),
        client=client,
        sleep=fake_sleep,
    )
    try:
        with pytest.raises(RateLimitError):
            await model.complete("hello", tenant_id="tenant-a")
    finally:
        await client.aclose()
    assert calls == 2
    assert sleeps == [0.5]


@pytest.mark.anyio
async def test_malformed_response_is_rejected() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = GLMChatModel(GLMEvaluatorConfig(enabled=True, api_key="test-secret"), client=client)
    try:
        with pytest.raises(MalformedModelResponse):
            await model.complete("hello", tenant_id="tenant-a")
    finally:
        await client.aclose()
{%- else %}
"""AgentScope evaluation tests are not selected for this generated project."""
{%- endif %}
