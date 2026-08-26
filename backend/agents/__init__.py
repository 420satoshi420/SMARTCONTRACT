"""
Agent definitions and LLM wrappers for Eth-Hunter.
"""
from .base import (
    BaseLLMClient,
    MockLLMBackend,
    GeminiBackend,
    OpenAIBackend,
    AnthropicBackend,
    NvidiaNimBackend,
    get_llm_backend,
    get_llm_for_task,
)
from .red_team import RedTeamAgent
from .blue_team import BlueTeamAgent
from .openclaw import OpenClawAgent
from .hermes import HermesAgent

__all__ = [
    "BaseLLMClient",
    "MockLLMBackend",
    "GeminiBackend",
    "OpenAIBackend",
    "AnthropicBackend",
    "NvidiaNimBackend",
    "get_llm_backend",
    "get_llm_for_task",
    "RedTeamAgent",
    "BlueTeamAgent",
    "OpenClawAgent",
    "HermesAgent",
]
