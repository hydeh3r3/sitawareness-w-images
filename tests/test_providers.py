"""Live safety gates and official API wire-format tests, without paid calls."""

import json
from pathlib import Path

import httpx
import pytest

from veup.io import EventLog
from veup.providers import AnthropicProvider, Ledger, LimitError
from veup.schemas import Action, Config


def test_live_requires_opt_in_and_caps(tmp_path: Path) -> None:
    """A configured adapter cannot accidentally opt itself into paid execution."""
    config = Config()
    ledger = Ledger(config, EventLog(tmp_path / "events.jsonl"))
    with pytest.raises(LimitError):
        AnthropicProvider(config, ledger, False, config.model)
    with pytest.raises(LimitError):
        AnthropicProvider(config, ledger, True, config.model)


def test_adapter_records_real_wire_response_with_stub_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Check response parsing and request tools with a local HTTP stub, not a claimed API call."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-real-key")
    config = Config(max_calls=1, max_spend_usd=1)
    ledger = Ledger(config, EventLog(tmp_path / "events.jsonl"))

    def handler(request: httpx.Request) -> httpx.Response:
        """Inspect the allowlisted provider endpoint and return a fixture response."""
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        payload = json.loads(request.content)
        assert [tool["name"] for tool in payload["tools"]] == ["submit"]
        return httpx.Response(
            200,
            json={
                "model": "stub-snapshot",
                "content": [{"type": "tool_use", "name": "submit", "input": {"tool": "inspect"}}],
                "usage": {"input_tokens": 20, "output_tokens": 10},
            },
        )

    provider = AnthropicProvider(config, ledger, True, config.model, httpx.MockTransport(handler))
    reply = provider.generate({"role": "task"}, Action.model_json_schema())
    assert reply.model == "stub-snapshot" and reply.trace is None
    assert reply.input_tokens == 20 and ledger.calls == 1
    assert "test-not-a-real-key" not in ledger.log.path.read_text()
    with pytest.raises(LimitError):
        provider.generate({}, Action.model_json_schema())


def test_failed_requests_keep_their_budget_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provider errors cannot trigger free retries or invented successful responses."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    config = Config(max_calls=1, max_spend_usd=1)
    ledger = Ledger(config, EventLog(tmp_path / "events.jsonl"))

    def handler(request: httpx.Request) -> httpx.Response:
        """Return a provider failure without network access."""
        del request
        return httpx.Response(500, json={"error": "fixture"})

    provider = AnthropicProvider(config, ledger, True, config.model, httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        provider.generate({}, Action.model_json_schema())
    assert ledger.calls == 1 and ledger.reserved > 0
    with pytest.raises(LimitError):
        provider.generate({}, Action.model_json_schema())


def test_byte_and_dollar_caps_reject_before_dispatch(tmp_path: Path) -> None:
    """The request-size and dollar limits also bind when calls remain."""
    config = Config(max_calls=10, max_spend_usd=0.1)
    ledger = Ledger(config, EventLog(tmp_path / "events.jsonl"))
    with pytest.raises(LimitError, match="spending"):
        ledger.reserve(100)
    assert ledger.calls == 0
    with pytest.raises(LimitError, match="byte"):
        ledger.reserve(config.max_request_bytes + 1)
    assert ledger.calls == 0


def test_malformed_billed_response_keeps_reported_cost(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A billed response that lacks a tool result still contributes to measured cost."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    config = Config(max_calls=1, max_spend_usd=1)
    ledger = Ledger(config, EventLog(tmp_path / "events.jsonl"))

    def handler(request: httpx.Request) -> httpx.Response:
        """Return usage with an invalid structured response."""
        del request
        return httpx.Response(
            200,
            json={
                "model": "stub",
                "content": [],
                "usage": {"input_tokens": 100, "output_tokens": 10},
            },
        )

    provider = AnthropicProvider(config, ledger, True, config.model, httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="submit"):
        provider.generate({}, Action.model_json_schema())
    assert ledger.estimated == pytest.approx(0.00045)
