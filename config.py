# config.py
# Every tunable setting lives HERE and only here.
# For live changes (retry count, model, prices) this is the file you edit.

import os                      # to read environment variables
from dotenv import load_dotenv # to load the local .env file

load_dotenv()  # reads .env into environment variables (does nothing on Render, where they are set in the dashboard)

# ---------- Gemini settings ----------
# The key comes ONLY from the environment. It is never written in code.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Model name; can be overridden with the GEMINI_MODEL environment variable.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# The REST endpoint we call (built from the model name).
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# Max seconds to wait for one HTTP response before giving up.
REQUEST_TIMEOUT_SECONDS = 120

# Max tokens the model may write back (SVGs can be long).
MAX_OUTPUT_TOKENS = 8192

# ---------- Price estimates (USD per 1,000,000 tokens) ----------
# IMPORTANT: these are EDITABLE ESTIMATES, not confirmed prices.
# Check the current price for your model on Google's Gemini API pricing page
# and update the two numbers below. On the FREE tier the real cost is $0;
# we show the estimated paid-tier cost so cost tracking is meaningful.
PRICE_PER_MILLION_INPUT_USD = 0.10
PRICE_PER_MILLION_OUTPUT_USD = 0.40

# ---------- Retry settings ----------
# API errors (429 rate limit / 503 overloaded): wait and try again, up to 3 times.
MAX_API_RETRIES = 3
API_RETRY_STATUS_CODES = (429, 503)
BACKOFF_BASE_SECONDS = 2   # waits will be 2s, 4s, 8s (doubling each time)

# Validation failures (a check failed): retry ONCE, telling the model why.
MAX_VALIDATION_RETRIES = 1

# Pause between concepts in generate_all.py, to respect free-tier limits.
PAUSE_BETWEEN_CONCEPTS_SECONDS = 5

# ---------- SVG settings ----------
VIEWBOX_WIDTH = 800
VIEWBOX_HEIGHT = 600
MIN_TEXT_LABELS = 3        # the assignment requires at least 3 <text> labels

# ---------- File paths ----------
RESULTS_FILE = "results.json"