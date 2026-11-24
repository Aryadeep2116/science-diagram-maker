# Science Diagram Maker

Asks Gemini for 5 animated SVG science diagrams, checks each in code, and lets a reviewer approve or reject them.
Live app: <https://science-diagram-maker-ahg7.onrender.com>

## Run locally
1. `python -m venv venv` then `venv\Scripts\activate` (Windows) or `source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` (and optionally `GEMINI_MODEL`)
4. `python generate_all.py` regenerates `results.json` (`python generate_all.py 3` for one concept)
5. `python app.py` then open http://127.0.0.1:5000
6. `python -m unittest -v` runs the check tests (no API needed)


Model: gemini-3.5-flash-lite. Costs are ESTIMATES from editable prices in `config.py`; the free tier actually costs $0.
Concepts 2 to 5 were generated with the first prompt; concept 1 was regenerated after I tightened the prompt.

## How it works
Prompt builder, then Gemini call (429/503: wait 2s, 4s, 8s, max 3), then 5 checks, then one retry that tells the model exactly which checks failed. Tokens and cost are summed across attempts. API retries and validation retries are counted separately.
Checks: valid XML; basic viewBox bounds; title and 3+ text labels; at least one animation; required science keywords and a safety check. These checks do **not** verify scientific correctness or circuit connectivity. A diagram that passes them is marked **NEEDS REVIEW**, not PASS, until scientific verification is recorded for that exact SVG. Any automatic or scientific failure gives FAIL. The saved series circuit is marked FAIL: its right-hand wire has a gap, and its component symbols do not show clear connections. Changing the SVG invalidates a recorded scientific verdict. Browser Approve/Reject decisions are separate from the recorded scientific verification and are tied to the exact diagram.

## Decisions
- **Persistence:** browser localStorage, keyed by concept id. Simplest to explain and works on Render's free tier, whose disk is wiped on redeploy. Trade-off: decisions are per browser and not shared. With more time I'd use a database such as Postgres or SQLite on a persistent disk.
- **Safety:** the API key is only an environment variable, and Gemini is only called from the server. SVGs are shown inside `<img>` data URIs, so scripts cannot run.
- Generate results are shown in the browser only; they never overwrite `results.json`.

## What failed and how I fixed it
- Gemini wraps SVG in markdown fences (```xml). Fixed with `extract_svg`.
- Rate limits: 429/503 happened on <concepts> and the backoff recovered (see API retries).
- Concept 1 first run FAILED `in_viewbox` even after its retry (<5598> output tokens, $<0.002313>). A fresh run passed.
- Concept 1 then passed all checks but looked wrong: clipped squares, covered title, overlapping labels. Cause: my viewBox check skips elements with a `transform`, and the model used transforms. Fix: the prompt now bans transforms and reserves a title band. This is why Approve/Reject matters: code cannot judge layout.
- Known limitations: no text-width or overlap detection; curved paths and transformed elements are not bounds-checked.

## One more day
- Evaluate simple translate/rotate transforms and add a text-overlap check.
- Render the SVG to an image and ask a vision model to judge it.
- Store review decisions in a database, add reviewer login.
- Save live generations, cache results, add more tests (pipeline with a mocked API).

## AI tools used
Claude: guided troubleshooting and repetitive code writing.

## Current issues
The Current issues panel lists failed automatic checks, recorded scientific-review failures, and live-generation errors for each diagram. It updates after generation, links to the relevant row, and distinguishes diagrams awaiting scientific review from failures. Live-generation errors remain visible until another attempt for that diagram; they are not persisted.

## Scientific review of the saved diagrams
These verdicts apply only to the exact SVGs in `results.json`; a changed or newly generated SVG requires a new review. Review used SVG source and static renders, and inspected animation paths in source; it did not verify playback in every browser.

- **Pythagoras — FAIL:** the geometry is correct, but area labels use “units” instead of square units, an animated label overlaps the side label, and the accessible title has a typo.
- **Circle — PASS:** centre, radius, diameter and circumference are correctly depicted and described.
- **Series circuit — FAIL:** the right-hand wire has a gap and component connections are unclear.
- **Photosynthesis — PASS:** the inputs, light energy and products are represented correctly at the level of the concept; the word equation is simplified.
- **States of matter — FAIL:** liquid particles are drawn widely separated, contradicting the close spacing described in the concept.

These are reviews of the saved examples, not an automated scientific validator. Local browser Approve/Reject decisions remain separate from these recorded verdicts.
