"""
Tests for LLM timeout enforcement in llm_anthropic_client.py.

Verifies that asyncio.wait_for wraps messages.create in both
_call_with_backoff and call_with_images, and that timeout errors
are caught and treated as retriable (not immediately fatal).
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest


@pytest.mark.asyncio
async def test_call_with_backoff_raises_after_timeout():
    """_call_with_backoff must raise RuntimeError when messages.create hangs past LLM_API_TIMEOUT."""
    import llm_anthropic_client

    async def hang_forever(**kwargs):
        await asyncio.sleep(9999)

    mock_client = MagicMock()
    mock_client.messages.create = hang_forever

    with patch.object(llm_anthropic_client, "_get_client", return_value=mock_client):
        with patch.object(llm_anthropic_client, "LLM_API_TIMEOUT", 0.05):
            with pytest.raises(RuntimeError, match="timed out|retries"):
                await llm_anthropic_client._call_with_backoff(
                    messages=[{"role": "user", "content": "test"}],
                    retries=1,
                )


@pytest.mark.asyncio
async def test_call_with_backoff_retries_on_timeout():
    """Timeout on attempt 0 must trigger a retry (not immediately raise)."""
    import llm_anthropic_client

    call_count = 0
    # Use an Event that never gets set — asyncio.wait_for will cancel it via TimeoutError
    never_resolves = asyncio.Event()

    async def hang_then_succeed(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            await never_resolves.wait()  # hangs until wait_for cancels it
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="ok")]
        return mock_resp

    mock_client = MagicMock()
    mock_client.messages.create = hang_then_succeed

    with patch.object(llm_anthropic_client, "_get_client", return_value=mock_client):
        with patch.object(llm_anthropic_client, "LLM_API_TIMEOUT", 0.05):
            # Patch only the module-level sleep so backoff is instant but the hang is real
            with patch("llm_anthropic_client.asyncio.sleep", new_callable=AsyncMock):
                result = await llm_anthropic_client._call_with_backoff(
                    messages=[{"role": "user", "content": "test"}],
                    retries=2,
                )
    assert result == "ok"
    assert call_count == 2


@pytest.mark.asyncio
async def test_call_with_images_raises_after_timeout():
    """call_with_images must raise RuntimeError when messages.create hangs past LLM_API_TIMEOUT."""
    import llm_anthropic_client

    async def hang_forever(**kwargs):
        await asyncio.sleep(9999)

    mock_client = MagicMock()
    mock_client.messages.create = hang_forever

    with patch.object(llm_anthropic_client, "_get_client", return_value=mock_client):
        with patch.object(llm_anthropic_client, "LLM_API_TIMEOUT", 0.05):
            with pytest.raises(RuntimeError, match="timed out|retries"):
                await llm_anthropic_client.call_with_images(
                    text_prompt="describe this",
                    images=[{"data": "abc", "media_type": "image/jpeg"}],
                    retries=1,
                )


def test_get_client_passes_httpx_timeout():
    """_get_client must construct AsyncAnthropic with an httpx.Timeout."""
    import httpx
    import anthropic
    import llm_anthropic_client

    with patch("anthropic.AsyncAnthropic") as mock_cls:
        mock_cls.return_value = MagicMock()
        llm_anthropic_client._get_client()
        call_kwargs = mock_cls.call_args.kwargs
        assert "timeout" in call_kwargs, "AsyncAnthropic must receive a timeout kwarg"
        assert isinstance(call_kwargs["timeout"], httpx.Timeout)
