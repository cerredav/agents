"""HTTP connection for the OpenAI-compatible model server."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml


Message = dict[str, str]
CONFIG_PATH = Path(__file__).with_name("config.yml")


class ModelConnectionError(RuntimeError):
    """Raised when the model server cannot return a valid response."""


def load_config(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    """Load and minimally validate the model connection configuration."""
    path = Path(config_path)

    try:
        with path.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
    except (OSError, yaml.YAMLError) as error:
        raise ModelConnectionError(f"Could not read model config at {path}: {error}") from error

    if not isinstance(config, dict):
        raise ModelConnectionError(f"Model config at {path} must contain a mapping.")

    missing = [key for key in ("location", "model") if not config.get(key)]
    if missing:
        raise ModelConnectionError(
            f"Model config is missing required field(s): {', '.join(missing)}"
        )

    return config


def stream_model_response(
    messages: Sequence[Message],
    *,
    config_path: str | Path = CONFIG_PATH,
    timeout: float = 120,
) -> Iterator[str]:
    """POST a chat request and yield response text as the model streams it.

    The configured ``location`` is treated as an OpenAI-compatible API base
    URL. The server is expected to return Server-Sent Events (SSE), with each
    event containing a chat-completion chunk.
    """
    config = load_config(config_path)
    base_url = str(config.pop("location")).rstrip("/")
    endpoint = f"{base_url}/chat/completions"

    # These fields are accepted by the OpenAI-compatible chat endpoint.
    allowed_fields = {
        "model",
        "temperature",
        "max_tokens",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "stop",
        "n",
        "logprobs",
    }
    payload = {key: value for key, value in config.items() if key in allowed_fields}
    payload["messages"] = list(messages)
    payload["stream"] = True

    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line or line.startswith(":"):
                    continue

                if not line.startswith("data:"):
                    continue

                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    return

                try:
                    chunk = json.loads(data)
                    text = chunk["choices"][0]["delta"].get("content")
                except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
                    raise ModelConnectionError(
                        f"Model server returned an invalid stream event: {data}"
                    ) from error

                if text:
                    yield text
    except HTTPError as error:
        try:
            details = error.read().decode("utf-8", errors="replace")
        except OSError:
            details = str(error)
        raise ModelConnectionError(
            f"Model server returned HTTP {error.code}: {details}"
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise ModelConnectionError(
            f"Request to model server at {endpoint} failed: {error}"
        ) from error
