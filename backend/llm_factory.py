"""
LLM client factory for selecting between dummy and real LLM implementations.

Provides factory functions that select the appropriate LLMClient
implementation based on configuration settings and availability.
"""

from llm_interfaces import LLMClient, DummyLLMClient, SyncDummyLLMClient
from config import USE_LLM, LLM_PROVIDER


def get_llm_client() -> LLMClient:
    """
    Get the configured LLMClient implementation.
    
    Returns DummyLLMClient by default, or a real LLM client if configured.
    Falls back to DummyLLMClient if real LLM initialization fails.
    
    Returns:
        An LLMClient instance (Dummy or real provider)
    """
    if not USE_LLM:
        return DummyLLMClient()
    
    if LLM_PROVIDER == "openai":
        try:
            from llm_openai_client import OpenAILLMClient
            return OpenAILLMClient()
        except Exception as e:
            print(f"Warning: Failed to initialize OpenAI LLM client: {e}")
            print("Falling back to DummyLLMClient")
            return DummyLLMClient()
    
    # Unknown provider or explicitly set to "dummy"
    return DummyLLMClient()


def get_sync_llm_client() -> LLMClient:
    """
    Get a synchronous LLMClient for use in sync contexts (FastAPI endpoints).
    
    Returns DummyLLMClient by default, or a sync wrapper around a real LLM client.
    
    Returns:
        A synchronous LLMClient instance
    """
    if not USE_LLM:
        return SyncDummyLLMClient()
    
    if LLM_PROVIDER == "openai":
        try:
            from llm_openai_client import SyncOpenAILLMClient
            return SyncOpenAILLMClient()
        except Exception as e:
            print(f"Warning: Failed to initialize OpenAI LLM client: {e}")
            print("Falling back to DummyLLMClient")
            return SyncDummyLLMClient()
    
    # Unknown provider or explicitly set to "dummy"
    return SyncDummyLLMClient()


# Cached LLM client instances
_llm_client: LLMClient | None = None
_sync_llm_client: LLMClient | None = None


def get_cached_llm_client() -> LLMClient:
    """
    Get the cached async LLM client instance.
    
    Creates the client on first call, then returns the cached instance
    for subsequent calls.
    
    Returns:
        The configured async LLMClient instance
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = get_llm_client()
    return _llm_client


def get_cached_sync_llm_client() -> LLMClient:
    """
    Get the cached sync LLM client instance.
    
    Creates the client on first call, then returns the cached instance
    for subsequent calls.
    
    Returns:
        The configured sync LLMClient instance
    """
    global _sync_llm_client
    if _sync_llm_client is None:
        _sync_llm_client = get_sync_llm_client()
    return _sync_llm_client


def reset_llm_clients() -> None:
    """
    Reset cached LLM client instances.
    
    Useful for testing when configuration changes or when switching providers.
    After calling this, the next get_cached_*_llm_client() call will create fresh instances.
    """
    global _llm_client, _sync_llm_client
    _llm_client = None
    _sync_llm_client = None
