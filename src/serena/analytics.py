from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from copy import copy
from dataclasses import asdict, dataclass
from enum import Enum

from anthropic.types import MessageParam, MessageTokensCount
from dotenv import load_dotenv

log = logging.getLogger(__name__)


class TokenCountEstimator(ABC):
    @abstractmethod
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text.
        This is an abstract method that should be implemented by subclasses.
        """


class TiktokenCountEstimator(TokenCountEstimator):
    """
    Approximate token count using tiktoken.
    
    Note: The tokenizer models will be downloaded from OpenAI's servers on first use.
    This is a one-time download and does not send your source code to external servers.
    """

    def __init__(self, model_name: str = "gpt-4o", allow_network_access: bool = True):
        """
        The tokenizer will be downloaded on the first initialization, which may take some time.

        :param model_name: see `tiktoken.model` to see available models.
        :param allow_network_access: Allow downloading tokenizer models from OpenAI
        """
        import tiktoken

        if not allow_network_access:
            try:
                # Try to use cached encoding if available
                self._encoding = tiktoken.encoding_for_model(model_name)
            except Exception as e:
                raise ValueError(
                    f"TikToken tokenizer model '{model_name}' not found locally and network access is disabled. "
                    "Either enable network access or use a different token estimator. "
                    f"Original error: {e}"
                )
        else:
            log.info(f"Loading tiktoken encoding for model {model_name}, this may take a while on the first run.")
            log.info("Note: This will download tokenizer models from OpenAI but does not send your code to external servers.")
            self._encoding = tiktoken.encoding_for_model(model_name)

    def estimate_token_count(self, text: str) -> int:
        return len(self._encoding.encode(text))


class AnthropicTokenCount(TokenCountEstimator):
    """
    The exact count using the Anthropic API.
    
    ⚠️  SECURITY WARNING: This feature sends your source code/text to Anthropic's servers for token counting.
    This creates a potential privacy risk as your code will be transmitted to external servers.
    
    Counting is free, but has a rate limit and will require an API key,
    (typically, set through an env variable).
    See https://docs.anthropic.com/en/docs/build-with-claude/token-counting
    
    To use this feature safely:
    1. Only use with non-sensitive code
    2. Ensure compliance with your organization's data policies
    3. Consider using TiktokenCountEstimator instead for offline token estimation
    """

    def __init__(self, model_name: str = "claude-sonnet-4-20250514", api_key: str | None = None, allow_network_access: bool = False):
        import anthropic

        if not allow_network_access:
            raise ValueError(
                "AnthropicTokenCount requires explicit permission for network access. "
                "Set allow_network_access=True to acknowledge that your code will be sent to Anthropic's servers. "
                "Consider using TiktokenCountEstimator for offline token estimation instead."
            )

        self._model_name = model_name
        if api_key is None:
            load_dotenv()
        self._anthropic_client = anthropic.Anthropic(api_key=api_key)

    def _send_count_tokens_request(self, text: str) -> MessageTokensCount:
        return self._anthropic_client.messages.count_tokens(
            model=self._model_name,
            messages=[MessageParam(role="user", content=text)],
        )

    def estimate_token_count(self, text: str) -> int:
        return self._send_count_tokens_request(text).input_tokens


_registered_token_estimator_instances_cache: dict[RegisteredTokenCountEstimator, TokenCountEstimator] = {}


class RegisteredTokenCountEstimator(Enum):
    TIKTOKEN_GPT4O = "TIKTOKEN_GPT4O"
    ANTHROPIC_CLAUDE_SONNET_4 = "ANTHROPIC_CLAUDE_SONNET_4"

    @classmethod
    def get_valid_names(cls) -> list[str]:
        """
        Get a list of all registered token count estimator names.
        """
        return [estimator.name for estimator in cls]

    def _create_estimator(self, allow_network_access: bool = False) -> TokenCountEstimator:
        match self:
            case RegisteredTokenCountEstimator.TIKTOKEN_GPT4O:
                return TiktokenCountEstimator(model_name="gpt-4o", allow_network_access=allow_network_access)
            case RegisteredTokenCountEstimator.ANTHROPIC_CLAUDE_SONNET_4:
                return AnthropicTokenCount(model_name="claude-sonnet-4-20250514", allow_network_access=allow_network_access)
            case _:
                raise ValueError(f"Unknown token count estimator: {self.value}")

    def load_estimator(self, allow_network_access: bool = False) -> TokenCountEstimator:
        estimator_instance = _registered_token_estimator_instances_cache.get(self)
        if estimator_instance is None:
            estimator_instance = self._create_estimator(allow_network_access=allow_network_access)
            _registered_token_estimator_instances_cache[self] = estimator_instance
        return estimator_instance


class ToolUsageStats:
    """
    A class to record and manage tool usage statistics.
    """

    def __init__(
        self, 
        token_count_estimator: RegisteredTokenCountEstimator = RegisteredTokenCountEstimator.TIKTOKEN_GPT4O,
        allow_network_token_counting: bool = False,
        allow_model_downloads: bool = True
    ):
        # For TikToken, we allow model downloads by default (they're just tokenizer models, not sending code)
        # For Anthropic, we require explicit permission since it sends code to external servers
        network_access = allow_network_token_counting if token_count_estimator == RegisteredTokenCountEstimator.ANTHROPIC_CLAUDE_SONNET_4 else allow_model_downloads
        
        self._token_count_estimator = token_count_estimator.load_estimator(allow_network_access=network_access)
        self._token_estimator_name = token_count_estimator.value
        self._tool_stats: dict[str, ToolUsageStats.Entry] = defaultdict(ToolUsageStats.Entry)
        self._tool_stats_lock = threading.Lock()

    @property
    def token_estimator_name(self) -> str:
        """
        Get the name of the registered token count estimator used.
        """
        return self._token_estimator_name

    @dataclass(kw_only=True)
    class Entry:
        num_times_called: int = 0
        input_tokens: int = 0
        output_tokens: int = 0

        def update_on_call(self, input_tokens: int, output_tokens: int) -> None:
            """
            Update the entry with the number of tokens used for a single call.
            """
            self.num_times_called += 1
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens

    def _estimate_token_count(self, text: str) -> int:
        return self._token_count_estimator.estimate_token_count(text)

    def get_stats(self, tool_name: str) -> ToolUsageStats.Entry:
        """
        Get (a copy of) the current usage statistics for a specific tool.
        """
        with self._tool_stats_lock:
            return copy(self._tool_stats[tool_name])

    def record_tool_usage(self, tool_name: str, input_str: str, output_str: str) -> None:
        input_tokens = self._estimate_token_count(input_str)
        output_tokens = self._estimate_token_count(output_str)
        with self._tool_stats_lock:
            entry = self._tool_stats[tool_name]
            entry.update_on_call(input_tokens, output_tokens)

    def get_tool_stats_dict(self) -> dict[str, dict[str, int]]:
        with self._tool_stats_lock:
            return {name: asdict(entry) for name, entry in self._tool_stats.items()}

    def clear(self) -> None:
        with self._tool_stats_lock:
            self._tool_stats.clear()
