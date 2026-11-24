# gemini_client.py
# Talks to the Gemini REST API. Handles rate limits (429) and overload (503)
# by waiting and retrying, and turns every other problem into a clear error.

import time
import requests
import config


# ---------- Custom errors (each has a human-readable message for the UI) ----------
class GeminiError(Exception):
    """Base class: any problem calling Gemini."""


class GeminiKeyError(GeminiError):
    """The API key is missing or rejected."""


class GeminiRateLimitError(GeminiError):
    """Still rate-limited / overloaded after all retries."""


def _wait_time(response, attempt):
    """How many seconds to wait before retry number `attempt` (0, 1, 2).

    If the server sent a Retry-After header we respect it; otherwise we use
    exponential backoff: 2s, 4s, 8s (base * 2^attempt).
    """
    header = response.headers.get("Retry-After")
    if header and header.isdigit():                     # header is only usable if it's a plain number
        return int(header)
    return config.BACKOFF_BASE_SECONDS * (2 ** attempt)


def _post_once(prompt):
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
            config.GEMINI_URL, headers=headers, json=body,
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


def call_gemini(prompt):
    """Call Gemini with retries on 429/503.

    Returns a dict: text, input_tokens, output_tokens, api_retries.
    api_retries counts how many times we had to wait and retry (separate from
    validation retries, which pipeline.py counts).
    """
    if not config.GEMINI_API_KEY:
        raise GeminiKeyError("The server has no GEMINI_API_KEY set.")

    api_retries = 0
    while True:
        response = _post_once(prompt)

        if response.status_code == 200:                 # success
            result = _parse_response(response)
            result["api_retries"] = api_retries
            return result

        if response.status_code in config.API_RETRY_STATUS_CODES:
            if api_retries >= config.MAX_API_RETRIES:   # used up all 3 retries
                raise GeminiRateLimitError(
                    "The AI is busy or the free rate limit was hit. Please wait a minute and try again."
                )
            time.sleep(_wait_time(response, api_retries))   # wait, then loop to try again
            api_retries += 1
            continue

        if response.status_code in (400, 401, 403):     # bad/invalid key or bad request
            raise GeminiKeyError("The API key was rejected. Check GEMINI_API_KEY.")
        if response.status_code == 404:
            raise GeminiError(f"Model '{config.GEMINI_MODEL}' was not found. Check GEMINI_MODEL.")
        raise GeminiError(f"The AI service returned an unexpected error (HTTP {response.status_code}).")


if __name__ == "__main__":
    # Smoke test: run `python gemini_client.py`
    result = call_gemini("Draw a simple red circle as SVG. Return only SVG code.")
    print(result["text"])
    print(f"\nModel: {config.GEMINI_MODEL} | in: {result['input_tokens']} | "
          f"out: {result['output_tokens']} | api retries: {result['api_retries']}")