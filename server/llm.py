"""Gemini access shared by every agent.

All network I/O to the model lives here so that retries, JSON extraction and
error reporting behave identically for the specialists and the synthesizer.
Failures raise ``LLMError`` instead of returning an empty result: an agent that
could not run must never look the same as an agent that found nothing.
"""
import json
import logging
import os
import time
from functools import lru_cache

from google import genai
from google.genai import types
from json_repair import repair_json

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.1-flash-lite"
MAX_ATTEMPTS = 3
RETRY_DELAYS = (2, 4, 8)  # seconds slept after attempt 1, 2, 3


class LLMError(RuntimeError):
    """The model could not produce a usable answer."""


def model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    try:
        return genai.Client()
    except Exception as e:  # missing or malformed credentials
        raise LLMError(f"Gemini client could not be created: {e}") from e


def _generate_text(client: genai.Client, system_prompt: str, user_message: str) -> str:
    response = client.models.generate_content(
        model=model_name(),
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0,
            response_mime_type="application/json",
        ),
    )
    if not response.text:
        raise LLMError("model returned an empty response")
    return response.text


def parse_json(raw: str, expect: type):
    """Extract a JSON ``list`` or ``dict`` from a model response.

    Tolerates a wrapping markdown fence and chatter around the payload, and
    falls back to ``json_repair`` for malformed JSON. Raises ``LLMError`` when
    nothing of the expected type can be recovered.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]

    opener, closer = ("[", "]") if expect is list else ("{", "}")
    start, end = text.find(opener), text.rfind(closer)
    if start == -1 or end <= start:
        raise LLMError(f"no JSON {expect.__name__} found in model response")
    text = text[start:end + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = json.loads(repair_json(text))
        except Exception as e:
            raise LLMError(f"model returned unparseable JSON: {e}") from e

    if not isinstance(parsed, expect):
        raise LLMError(f"expected a JSON {expect.__name__}, got {type(parsed).__name__}")
    return parsed


def generate_json(system_prompt: str, user_message: str, expect: type):
    """Call the model and return parsed JSON of type ``expect`` (list or dict).

    Retries transient API errors and unparseable answers with backoff. Missing
    credentials are not retried.
    """
    client = _client()
    last_error: Exception | None = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            return parse_json(_generate_text(client, system_prompt, user_message), expect)
        except Exception as e:
            last_error = e
            logger.warning("LLM attempt %d/%d failed: %s", attempt + 1, MAX_ATTEMPTS, e)
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(RETRY_DELAYS[attempt])

    raise LLMError(f"LLM call failed after {MAX_ATTEMPTS} attempts: {last_error}") from last_error
