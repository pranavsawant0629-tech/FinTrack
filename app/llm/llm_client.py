"""
LLM Client abstraction layer for Finova AI.
Encapsulates communication with Ollama, providing domain-level exception handling,
temperature controls, multi-turn message formatting, and connection timeouts.
"""

from typing import Any
import httpx
import ollama

from config.settings import settings


class LLMError(Exception):
    """Base domain exception for all LLM client failures."""
    pass


class LLMConnectionError(LLMError):
    """Raised when the LLM service cannot be reached or connection is refused."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when an LLM operation exceeds the configured timeout."""
    pass


class LLMResponseError(LLMError):
    """Raised when the LLM backend returns an error response (e.g. model not found, crash)."""
    pass


class LLMClient:
    """
    Abstraction layer over the LLM provider.
    Rest of the app should only talk to this class, never to `ollama` directly.
    """

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        timeout: float = 60.0,
        default_temperature: float = 0.1,
        default_num_predict: int = 600,
        default_keep_alive: str = "60m",
    ):
        self.model = model or settings.ollama_model
        self.host = host or settings.ollama_host
        self.timeout = timeout
        self.default_temperature = default_temperature
        self.default_num_predict = default_num_predict
        self.default_keep_alive = default_keep_alive
        self._client = ollama.Client(host=self.host, timeout=self.timeout)

    def chat(
        self,
        message: str | None = None,
        system: str | None = None,
        messages: list[dict[str, str]] | None = None,
        temperature: float | None = None,
        num_predict: int | None = None,
        keep_alive: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """
        Send a chat completion request to the LLM.

        Args:
            message: User message text (single-turn or latest turn).
            system: Optional system prompt to guide LLM behavior.
            messages: Optional conversation history or pre-formatted message list.
                      Each item should be a dict with 'role' and 'content' keys.
            temperature: Sampling temperature (defaults to self.default_temperature = 0.1).
            num_predict: Maximum generated tokens limit (defaults to self.default_num_predict = 600).
            timeout: Optional per-request timeout in seconds.

        Returns:
            The generated assistant text response.

        Raises:
            ValueError: If neither message nor messages is provided.
            LLMConnectionError: If connection to Ollama fails.
            LLMTimeoutError: If the request times out.
            LLMResponseError: If Ollama returns a model/inference error.
            LLMError: For other unexpected LLM failures.
        """
        if message is None and not messages:
            raise ValueError("Either 'message' or 'messages' must be provided to LLMClient.chat().")

        # Assemble the message sequence
        formatted_messages: list[dict[str, str]] = []

        if system:
            formatted_messages.append({"role": "system", "content": system})

        if messages:
            if system and messages[0].get("role") == "system":
                formatted_messages = list(messages)
            else:
                formatted_messages.extend(messages)

        if message:
            formatted_messages.append({"role": "user", "content": message})

        # Options for Ollama
        temp = self.default_temperature if temperature is None else temperature
        n_predict = self.default_num_predict if num_predict is None else num_predict
        options: dict[str, Any] = {
            "temperature": temp,
            "num_predict": n_predict,
        }

        # Select client (use per-call timeout if specified and different from default)
        client = self._client
        if timeout is not None and timeout != self.timeout:
            client = ollama.Client(host=self.host, timeout=timeout)

        effective_timeout = timeout if timeout is not None else self.timeout
        effective_keep_alive = keep_alive or self.default_keep_alive

        try:
            response = client.chat(
                model=self.model,
                messages=formatted_messages,
                options=options,
                keep_alive=effective_keep_alive,
            )
            if hasattr(response, "message") and hasattr(response.message, "content"):
                return response.message.content or ""
            return response["message"]["content"] or ""

        except httpx.TimeoutException as err:
            raise LLMTimeoutError(
                f"LLM request timed out after {effective_timeout}s: {err}"
            ) from err

        except (ConnectionError, httpx.ConnectError) as err:
            raise LLMConnectionError(
                f"Failed to connect to LLM service at {self.host}: {err}"
            ) from err

        except ollama.ResponseError as err:
            err_msg = str(getattr(err, "error", err))
            status_code = getattr(err, "status_code", None)

            if "timed out" in err_msg.lower():
                raise LLMTimeoutError(f"LLM request timed out: {err_msg}") from err
            if "connect" in err_msg.lower() or status_code == 503:
                raise LLMConnectionError(
                    f"LLM service connection failed at {self.host}: {err_msg}"
                ) from err
            raise LLMResponseError(
                f"LLM backend error (status {status_code}): {err_msg}"
            ) from err

        except ollama.RequestError as err:
            raise LLMConnectionError(
                f"LLM request error connecting to {self.host}: {err}"
            ) from err

        except httpx.HTTPError as err:
            raise LLMConnectionError(
                f"LLM HTTP transport error: {err}"
            ) from err

        except Exception as err:
            if isinstance(err, LLMError):
                raise
            raise LLMError(f"Unexpected LLM error: {err}") from err


llm_client = LLMClient()