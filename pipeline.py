# pipeline.py
# Generates ONE diagram for ONE concept: call the model, run the checks,
# retry once with feedback if a check failed, and log tokens, cost and retries.

import time
from datetime import datetime, timezone

import config
from gemini_client import call_gemini, GeminiError
from prompts import build_prompt, build_retry_prompt
from svg_utils import extract_svg
from checks import run_all_checks, failed_checks
from verification import assess_result


def estimate_cost(input_tokens, output_tokens):
    """Estimated USD cost, using the editable prices in config.py."""
    cost = (input_tokens * config.PRICE_PER_MILLION_INPUT_USD
            + output_tokens * config.PRICE_PER_MILLION_OUTPUT_USD) / 1_000_000
    return round(cost, 6)


def generate_one(concept):
    """Run the full Part A process for one concept and return a result dict.

    Two retry counters are kept SEPARATE:
      api_retries        = waits caused by 429/503 errors (counted inside call_gemini)
      validation_retries = new attempts because a check failed (max 1)
    Tokens are summed across ALL attempts, so cost includes the retry.
    """
    start_time = time.time()
    total_input = 0
    total_output = 0
    api_retries = 0
    validation_retries = 0
    note = ""                                        # extra message if something went wrong on the retry

    prompt = build_prompt(concept)                   # first attempt uses the normal prompt
    svg = ""
    checks = {}

    while True:
        try:
            reply = call_gemini(prompt)
        except GeminiError as error:
            if validation_retries == 0:              # first attempt failed: nothing to show, so raise
                raise
            note = f"The retry call failed: {error}"   # keep the first attempt's result instead
            break

        # Add this attempt's numbers to the running totals.
        total_input += reply["input_tokens"]
        total_output += reply["output_tokens"]
        api_retries += reply["api_retries"]

        # Clean the reply and run every check.
        svg = extract_svg(reply["text"]) or ""
        checks = run_all_checks(svg, concept)
        failures = failed_checks(checks)

        if not failures:                             # all checks passed: done
            break
        if validation_retries >= config.MAX_VALIDATION_RETRIES:   # already retried: give up honestly
            break

        validation_retries += 1                      # build a retry prompt that names the failures
        prompt = build_retry_prompt(concept, failures)

    result = {
        "id": concept["id"],
        "name": concept["name"],
        "subject": concept["subject"],
        "svg": svg,
        "checks": checks,
        "model": config.GEMINI_MODEL,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cost_usd": estimate_cost(total_input, total_output),
        "validation_retries": validation_retries,
        "api_retries": api_retries,
        "latency_seconds": round(time.time() - start_time, 1),
        "note": note,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return assess_result(result, concept)


if __name__ == "__main__":
    # Smoke test: `python pipeline.py` runs concept 1 once (1-2 API calls).
    from concepts import get_concept
    result = generate_one(get_concept(1))
    print("status:", result["final_status"], "| retries:", result["validation_retries"],
          "| tokens:", result["input_tokens"], "in /", result["output_tokens"], "out",
          "| cost: $", result["cost_usd"], "|", result["latency_seconds"], "s")
    for name, outcome in result["checks"].items():
        print(("PASS " if outcome["passed"] else "FAIL ") + name + ": " + outcome["reason"])
        