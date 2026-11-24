# app.py
# Flask server: shows saved results (no API call) and runs Part A live for one concept.
import json
import os
import threading
import time

from flask import Flask, jsonify, render_template

import config
from concepts import get_concept
from gemini_client import GeminiError, GeminiKeyError, GeminiRateLimitError, GeminiOverloadedError
from pipeline import generate_one
from verification import assess_result

app = Flask(__name__)

generate_lock = threading.Lock()   # only ONE live generation at a time (stops double-clicks)
COOLDOWN_SECONDS = 5               # minimum gap between live generations
last_finished = 0.0


def load_results():
    """Read results.json from disk. Returns [] if missing. No API call here."""
    if not os.path.exists(config.RESULTS_FILE):
        return []
    with open(config.RESULTS_FILE, encoding="utf-8") as file:
        results = json.load(file)
    return [assess_result(result, get_concept(result["id"]))
            if get_concept(result["id"]) else result for result in results]


@app.route("/")
def index():
    # Saved results are embedded in the page, so it works with no API call.
    return render_template("index.html", results=load_results(), model=config.GEMINI_MODEL)


@app.route("/api/results")
def api_results():
    return jsonify(load_results())


@app.route("/api/generate/<int:concept_id>", methods=["POST"])
def generate(concept_id):
    """Run the full pipeline for one concept. Always returns JSON, never a stack trace."""
    global last_finished
    concept = get_concept(concept_id)
    if concept is None:
        return jsonify(error="Unknown concept."), 404

    if not generate_lock.acquire(blocking=False):      # someone is already generating
        return jsonify(error="Another generation is already running. Please wait."), 429
    started = False
    try:
        wait = COOLDOWN_SECONDS - (time.time() - last_finished)
        if wait > 0:
            return jsonify(error=f"Please wait {int(wait) + 1} seconds and try again."), 429
        started = True
        return jsonify(generate_one(concept))          # NOT saved to results.json
    except GeminiRateLimitError as error:
        return jsonify(error=str(error)), 429
    except GeminiOverloadedError as error:
        return jsonify(error=str(error)), 503
    except GeminiKeyError as error:
        return jsonify(error=str(error)), 500
    except GeminiError as error:
        return jsonify(error=str(error)), 502
    except Exception:                                  # anything unexpected: friendly message
        return jsonify(error="Something went wrong on the server. Please try again."), 500
    finally:
        if started:
            last_finished = time.time()
        generate_lock.release()


if __name__ == "__main__":
    app.run(debug=True)


    