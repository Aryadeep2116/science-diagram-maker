# gemini_client.py
# Talks to the Gemini REST API. Handles rate limits (429) and overload (503)
# by waiting and retrying, and turns every other problem into a clear error.

import math
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests
import config


# ---------- Custom errors (each has a human-readable message for the UI) ----------
class GeminiError(Exception):
    """Base class: any problem calling Gemini."""


class GeminiKeyError(GeminiError):
    """The API key is missing or rejected."""


class GeminiRateLimitError(GeminiError):
    """Rate-limited after retries, or retry delay exceeds the interactive limit."""


class GeminiModelNotFoundError(GeminiError):
    """The configured model is not available to this project."""


class GeminiOverloadedError(GeminiError):
    """The upstream service is temporarily unavailable."""


def _error_data(response):
    """Read structured error metadata without returning upstream text to the user."""
    try:
        data = response.json()
    except (ValueError, TypeError):
        return {}
    return data.get("error", {}) if isinstance(data, dict) and isinstance(data.get("error"), dict) else {}


def _retry_delay(response):
    """Return the provider's retry delay, including RetryInfo and HTTP-date headers."""
    header = response.headers.get("Retry-After", "").strip()
    if header.isdigit():
        return int(header)
    if header:
        try:
            date = parsedate_to_datetime(header)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            return max(0, math.ceil((date - datetime.now(timezone.utc)).total_seconds()))
        except (TypeError, ValueError, OverflowError):
            pass
    details = _error_data(response).get("details", [])
    if isinstance(details, list):
        for detail in details:
            if not isinstance(detail, dict) or not str(detail.get("@type", "")).endswith("RetryInfo"):
                continue
            match = re.fullmatch(r"(\d+(?:\.\d+)?)s", str(detail.get("retryDelay", "")))
            if match:
                return math.ceil(float(match.group(1)))
    return None


def _wait_time(response, attempt):
    """Respect a provider delay, otherwise use exponential backoff."""
    delay = _retry_delay(response)
    return delay if delay is not None else config.BACKOFF_BASE_SECONDS * (2 ** attempt)


def _is_invalid_key(response):
    error = _error_data(response)
    details = error.get("details", [])
    if isinstance(details, list) and any(isinstance(item, dict) and item.get("reason") in
                                         ("API_KEY_INVALID", "API_KEY_EXPIRED") for item in details):
        return True
    # Some API responses omit structured details. Do not echo the provider message.
    message = str(error.get("message", "")).lower()
    return "api key not valid" in message or "api key expired" in message


def _temporary_error(status, retry_delay=None):
    if status == 429:
        message = "Gemini rate limit or quota reached. Check the project's Gemini quota and try again later."
        error_type = GeminiRateLimitError
    else:
        message = "Gemini is temporarily unavailable (HTTP 503). Try again later."
        if not config.GEMINI_FALLBACK_MODEL or config.GEMINI_FALLBACK_MODEL == config.GEMINI_MODEL:
            message += " If this persists, configure an accessible GEMINI_FALLBACK_MODEL on the server."
        message += " The saved diagram remains available."
        error_type = GeminiOverloadedError
    if retry_delay is not None and retry_delay > 0:
        message += f" Suggested wait: at least {retry_delay} seconds."
    return error_type(message)


def _post_once(prompt, model=None):
    """Send ONE HTTP request to Gemini. Returns the raw response object."""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": config.MAX_OUTPUT_TOKENS},
    }
    headers = {
        "x-goog-api-key": config.GEMINI_API_KEY,   # key goes in a header, never in the URL or logs
        "Content-Type": "application/json",
    }
    try:
        return requests.post(
            (config.GEMINI_URL if model is None else
             "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"),
            headers=headers, json=body,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        raise GeminiError("The AI took too long to respond (timeout). Please try again.")
    except requests.exceptions.RequestException:
        raise GeminiError("Could not reach the AI service. Check the internet connection.")


def _parse_response(response):
    """Pull text and token counts out of a successful response."""
    try:
        data = response.json()
    except ValueError:                                  # body was not JSON
        raise GeminiError("The AI returned a response that was not valid JSON.")

    candidates = data.get("candidates")
    if not candidates:                                  # e.g. blocked by safety filters
        raise GeminiError("The AI returned no answer (it may have been blocked by safety filters).")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts)   # join all text pieces
    if not text.strip():
        raise GeminiError("The AI returned an empty answer.")

    usage = data.get("usageMetadata", {})               # token counts reported by the API
    return {
        "text": text,
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
    }


def _call_model(prompt, model=None):
    """Call Gemini with retries on 429/503.

    Returns a dict: text, input_tokens, output_tokens, api_retries.
    api_retries counts how many times we had to wait and retry (separate from
    validation retries, which pipeline.py counts).
    """
    if not config.GEMINI_API_KEY:
        raise GeminiKeyError("The server has no GEMINI_API_KEY set.")

    api_retries = 0
    while True:
        response = _post_once(prompt) if model is None else _post_once(prompt, model)

        if response.status_code == 200:                 # success
            result = _parse_response(response)
            result["api_retries"] = api_retries
            return result

        if response.status_code in config.API_RETRY_STATUS_CODES:
            delay = _wait_time(response, api_retries)
            if api_retries >= config.MAX_API_RETRIES:
                error = _temporary_error(response.status_code, _retry_delay(response))
                error.api_retries = api_retries
                raise error
            if delay > config.MAX_AUTOMATIC_RETRY_WAIT_SECONDS:
                # Never retry before the provider's requested reset time.
                error = _temporary_error(response.status_code, delay)
                error.api_retries = api_retries
                raise error
            time.sleep(delay)
            api_retries += 1
            continue

        if response.status_code in (400, 401, 403):
            if response.status_code == 401 or _is_invalid_key(response):
                raise GeminiKeyError("Gemini rejected the API key. Check GEMINI_API_KEY in the server environment.")
            if response.status_code == 403:
                raise GeminiError("Gemini denied access (HTTP 403). Check the project's API access and model permissions.")
            raise GeminiError("Gemini rejected the request (HTTP 400). Check the model and request configuration.")
        if response.status_code == 404:
            error = GeminiModelNotFoundError(f"Model '{model or config.GEMINI_MODEL}' was not found. Check the model configuration.")
            error.api_retries = api_retries
            raise error
        raise GeminiError(f"The AI service returned an unexpected error (HTTP {response.status_code}).")


def call_gemini(prompt):
    """Try the primary model, then an explicitly configured fallback for quota/availability errors."""
    try:
        result = _call_model(prompt)
        result["model"] = config.GEMINI_MODEL
        return result
    except (GeminiRateLimitError, GeminiOverloadedError, GeminiModelNotFoundError) as primary:
        fallback = config.GEMINI_FALLBACK_MODEL
        if not fallback or fallback == config.GEMINI_MODEL:
            raise
        try:
            result = _call_model(prompt, fallback)
        except GeminiError as error:
            # Preserve the actionable fallback error without exposing provider response text.
            raise type(error)(f"Primary model unavailable; fallback model also failed: {error}") from error
        result["api_retries"] += getattr(primary, "api_retries", 0)
        result["model"] = fallback
        result["fallback_from"] = config.GEMINI_MODEL
        return result


if __name__ == "__main__":
    # Smoke test: run `python gemini_client.py`
    result = call_gemini("Draw a simple red circle as SVG. Return only SVG code.")
    print(result["text"])
    print(f"\nModel: {config.GEMINI_MODEL} | in: {result['input_tokens']} | "
          f"out: {result['output_tokens']} | api retries: {result['api_retries']}")