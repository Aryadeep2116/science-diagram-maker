# Science Diagram Maker

Science Diagram Maker shows built-in animated SVG science diagrams and can ask Gemini for new ones. It runs automatic checks and lets a person record a scientific review. The built-in examples can be viewed without a Gemini key. Live app: <https://science-diagram-maker-ahg7.onrender.com>

## Run locally

1. Create and activate a virtual environment: `python -m venv .venv`, then `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows).
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` for generation. Never commit or share the key.
4. Run `python app.py` and open <http://127.0.0.1:5000>. You can inspect the existing diagrams without a key.
5. Optionally run `python generate_all.py` to replace `results.json`, or `python generate_all.py 3` for one concept. These commands make real API calls and may incur charges.
6. Run tests without an API key: `python -m unittest -v` and `node --test tests/test_issues.js tests/test_review.js`.

## Generation and configuration

Set environment variables locally in `.env`, or in the hosting service's environment settings and restart/redeploy the service:

- `GEMINI_API_KEY`: server-side key. The browser never needs it. A configured key does not guarantee that the key works, the model is accessible, or quota is available.
- `GEMINI_MODEL`: primary model (default `gemini-3.5-flash-lite`). Choose a model actually available to your project; the default is not a guarantee of availability.
- `GEMINI_FALLBACK_MODEL`: optional, different model available to the same project. After a 429, 503 or 404 from the primary, the server tries this model. It does not fall back for invalid keys or permission/request errors. Both models may share a quota, so fallback is not a cure for free-tier limits.
- `GEMINI_FALLBACK_INPUT_PRICE` and `GEMINI_FALLBACK_OUTPUT_PRICE`: optional estimated USD per million tokens for the fallback. Both are needed for a fallback cost estimate. The editable primary price estimates are in `config.py`; update them for the selected model. Costs are estimates, not billing records; unknown fallback prices yield an unavailable estimate.

The status panel reports local configuration and worker state, **not** a provider health check. A live attempt is the only way this app tests the key, access and quota. A 429 means rate limiting or quota exhaustion; the app honors Gemini's retry delay or uses 2/4/8-second backoff, up to three retries. It reports delays over 20 seconds rather than waiting automatically. A 503 means the Gemini service returned an availability error; the app retries and can use a configured fallback, but cannot guarantee that either model is available. The saved illustration remains visible and is not misrepresented as a new Gemini result. If 503 persists, set an accessible `GEMINI_FALLBACK_MODEL` on the server and restart, or try later; 403 can mean access restrictions; 400 can indicate a request or model configuration problem. See the per-diagram message and Current issues panel for errors. A different key in the same project may share the same quota.

## Checks and review

Each concept has specific scientific and layout guidance in its prompt, including precise circuit connections and geometry. The prompt requests readable SVG with meaningful schematic motion rather than opacity-only blinking; generated results still need scientific and bounds review. The pipeline extracts SVG from the response, checks it and, if a check fails, makes one validation retry with the failure reasons and practical correction advice. When a complete prior SVG is available and at most 16,000 characters, the repair prompt includes it as JSON-encoded data; otherwise it requests a fresh SVG. API retries and validation retries are separate. Successful attempts track the actual model and token-based cost estimates; if a later API attempt fails, its retry count may not be included in the saved result.

Automatic checks cover XML/root, static viewBox bounds, title and visible labels, structural animation, concept keywords and SVG safety. They are **not** a scientific correctness test, a circuit connectivity test, or proof that the layout works everywhere.

- The static viewBox check uses shape geometry and a padded `resvg-py` raster with the bundled DejaVu Sans font to detect visible overflow, including text. It no longer marks every text-bearing diagram unverified simply because it contains text. This is a bounded static snapshot, not a proof for all off-screen content or all browser fonts; unsupported/relative geometry, unsafe external resources or renderer failures remain unverified when they cannot be checked reliably. Animated motion is considered separately.
- Animated bounds can pass when the static snapshot passes and a conservative verifier can bound all motion: opacity-only changes, circles travelling along simple straight-line SMIL paths, or fixed-centre rotation of a supported line/circle group. The path and full shape/stroke are checked over the entire motion, not just selected frames. Unsupported paths, effects, transforms or animation options remain **UNVERIFIED**; browser samples are only advisory and can miss frames or overestimate bounds. Neither method proves correct playback, scientific correctness, or absence of overlap, and static text rendering can differ across browsers.
- A reviewer must explicitly choose **Verify & approve** or **Verify & reject** after checking the science. The browser records the decision, optional note and time for that exact SVG. A changed SVG needs a new review. A scientific approval never overrides a failed or unverified automatic check: a failure yields FAIL, and otherwise any uncertainty yields NEEDS REVIEW. Only all passing automatic checks plus a scientific pass yield PASS. Rejection yields FAIL.

### Built-in examples

The five built-in examples are hand-authored in `scripts/build_default_results.py` and saved in `results.json`. They require no Gemini API call. They use looping SMIL motion: coloured markers trace triangle sides, a radius rotates around the centre, markers travel in the conventional-current direction around the circuit, markers show inputs and outputs of photosynthesis, and solid, liquid and gas particles move differently. The motion is schematic, not to scale or a physical simulation. Run `python scripts/build_default_results.py` to rebuild them; this overwrites `results.json` and replaces any batch-generated results.

| Concept | AI-assisted assessment | Key correction |
| --- | --- | --- |
| Pythagoras’ theorem | Pass | Moving dots trace a 3–4–5 triangle; areas use square units. |
| Parts of a circle | Pass | A rotating radius traces the circumference while its length remains fixed. |
| Series circuit | Pass | Cell and both lamps form one loop; moving markers show conventional current direction. |
| Photosynthesis | Pass | Moving markers show inputs, products and light direction at a simplified concept level. |
| States of matter | Pass | Solids vibrate, close liquid particles slide past each other, and gas particles move faster and farther apart. |

These assessments are an **AI assistant's review of the source and sampled animation**, tied to each SVG hash; they are not independent expert certification or the user's personal approval. All five use the supported motion subset; the verifier checks their full animated paths and their overall status is PASS based on the existing AI-assisted scientific assessments. This is not independent expert certification or the user's own approval. A person should still inspect the science and animation before relying on them, and can record their own browser review. A changed SVG invalidates the recorded assessment. Built-in results show zero API cost and calls; old Gemini run costs do not apply to the replacement illustrations.

## Persistence and deployment

Live-generated results and explicit review decisions are stored in the current browser's localStorage, not on the server, and are not shared between users or browsers. They can be cleared by the browser or unavailable due to storage settings. On refresh, live SVGs are rechecked by the server rather than trusting cached automatic results; if rechecking fails they remain unverified. Use **Restore saved diagram** to return to the server's `results.json` version. Live generation does not write that file. Browser-local reviews should not be treated as an authenticated audit trail; use a database and reviewer accounts for shared, durable, attributable records.

The API key stays on the server, and diagram previews use SVG in an image rather than executing it as page markup. The advisory animation sampler uses a script-disabled iframe with a restrictive resource policy. Nevertheless, this application is a demo, not a hardened multi-user service: public generation and recheck endpoints have no authentication or per-user rate limits and can consume resources or API quota. Add access controls, request/rate limits and appropriate isolation before exposing it to untrusted users. The generation lock and cooldown are process-local; the supplied `Procfile` uses one Gunicorn worker, but they do not coordinate across multiple instances. A Render deployment must be updated separately to pick up code and environment changes.

## AI tools used

Claude: guided troubleshooting and repetitive code writing. Arena AI: checking edge cases.
