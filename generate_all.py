# generate_all.py
# Runs the pipeline for the concepts and writes results.json.
#   python generate_all.py        -> all 5 concepts
#   python generate_all.py 3 5    -> only concepts 3 and 5 (merged into the existing file)
# results.json is saved after EVERY concept, so a rate-limit error never loses finished work.
# A failed new run never overwrites an older PASS.

import json
import os
import sys
import time

import config
from concepts import CONCEPTS, get_concept
from gemini_client import GeminiError
from pipeline import generate_one
from verification import assess_result

PREVIEW_FOLDER = "previews"


def load_existing():
    """Read results.json if it exists. Returns {concept_id: result}."""
    if not os.path.exists(config.RESULTS_FILE):
        return {}
    with open(config.RESULTS_FILE, encoding="utf-8") as file:
        data = json.load(file)
    return {item["id"]: assess_result(item, get_concept(item["id"]))
            if get_concept(item["id"]) else item for item in data}


def save_results(results_by_id):
    """Write all results, ordered by id, to results.json (UTF-8 so symbols like ² are kept)."""
    ordered = [results_by_id[concept_id] for concept_id in sorted(results_by_id)]
    with open(config.RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(ordered, file, ensure_ascii=False, indent=2)


def save_preview(result):
    """Save the SVG as a file so you can open it in a browser and look at it."""
    if not result["svg"]:
        return
    os.makedirs(PREVIEW_FOLDER, exist_ok=True)
    path = os.path.join(PREVIEW_FOLDER, f"concept_{result['id']}.svg")
    with open(path, "w", encoding="utf-8") as file:
        file.write(result["svg"])


def describe(result):
    """One readable log line for a finished concept."""
    failed = [name for name, outcome in result["checks"].items() if outcome["passed"] is False]
    line = (f"  -> {result['final_status'].upper()} | validation retries: {result['validation_retries']} "
            f"| api retries: {result['api_retries']} | tokens: {result['input_tokens']} in / "
            f"{result['output_tokens']} out | est. cost: ${result['cost_usd']} | {result['latency_seconds']}s")
    line += "\n     checks: " + ", ".join(
        f"{name}={'PASS' if outcome['passed'] is True else 'FAIL' if outcome['passed'] is False else 'UNVERIFIED'}"
        for name, outcome in result["checks"].items())
    if failed:
        line += "\n     failed checks: " + ", ".join(failed)
        for name, outcome in result["checks"].items():     # print WHY each check failed
            if outcome["passed"] is False:
                line += f"\n       {name}: {outcome['reason']}"
    return line


def main():
    if len(sys.argv) > 1:
        wanted_ids = [int(arg) for arg in sys.argv[1:]]        # ids given on the command line
    else:
        wanted_ids = [concept["id"] for concept in CONCEPTS]   # otherwise all of them

    results_by_id = load_existing()

    for position, concept_id in enumerate(wanted_ids):
        concept = get_concept(concept_id)
        if concept is None:
            print(f"No concept with id {concept_id}, skipping.")
            continue

        print(f"[{concept_id}] {concept['name']} ...")
        try:
            result = generate_one(concept)
        except GeminiError as error:                           # e.g. rate limit: report and carry on
            print(f"  -> API ERROR: {error}")
            print(f"     Re-run later with: python generate_all.py {concept_id}")
            continue

        print(describe(result))                                # always show what happened

        # Never let a failed new run replace an older PASS.
        old = results_by_id.get(concept_id)
        if old and old["final_status"] == "pass" and result["final_status"] == "fail":
            print("  -> New run failed; keeping the previous PASS result.")
            continue

        results_by_id[concept_id] = result
        save_results(results_by_id)                            # save immediately
        save_preview(result)

        if position < len(wanted_ids) - 1:                     # pause to respect free-tier limits
            time.sleep(config.PAUSE_BETWEEN_CONCEPTS_SECONDS)

    print(f"\nDone. {len(results_by_id)} of {len(CONCEPTS)} concepts saved in {config.RESULTS_FILE}.")


if __name__ == "__main__":
    main()
    