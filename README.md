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


Model: gemini-3.5-flash-lite. Costs are estimates from editable prices in `config.py`; actual cost depends on your plan and usage.
Concepts 2 to 5 were generated with the first prompt; concept 1 was regenerated after I tightened the prompt.

## How it works
Prompt builder, then Gemini call (429/503: retry up to 3 times, using the provider’s retry delay or 2s, 4s, 8s backoff), then 5 checks, then one retry that tells the model exactly which checks failed. Tokens and cost are summed across attempts. API retries and validation retries are counted separately.
Checks: valid XML; basic viewBox bounds; title and 3+ text labels; at least one animation; required science keywords and a safety check. These checks do **not** verify scientific correctness or circuit connectivity. The viewBox result is **UNVERIFIED** when text extent, CSS, references or animation require renderer review. A diagram with an unverified check or without scientific verification for the exact SVG is marked **NEEDS REVIEW**, not PASS. Any automatic or scientific failure gives FAIL. The saved series circuit is marked FAIL: its right-hand wire has a gap, and its component symbols do not show clear connections. Changing the SVG invalidates a recorded scientific verdict. Browser Approve/Reject decisions are separate from the recorded scientific verification and are tied to the exact diagram.

## Troubleshooting live generation

- Live generation runs on the server and needs `GEMINI_API_KEY` in its environment. On Render, set it in the service’s Environment settings and redeploy/restart the service; do not paste the key into the page, repository, logs or chat. Optionally set `GEMINI_MODEL` to a model available to that project.
- A 429 means Gemini rate limiting or quota exhaustion. The app respects `Retry-After` or Gemini `RetryInfo`; if the suggested wait exceeds 20 seconds, it reports the delay instead of retrying too early. Check the project’s Gemini quota and try again after the reset. A new key in the same project may still share the same quota.
- A 503 is a temporary upstream availability issue, a 403 may indicate project/model access, and a 400 may be a request/model configuration issue; these are not automatically treated as invalid keys.
- The button shows progress and errors beside the affected diagram. The original saved diagram remains visible after an error. A live result is only kept in the current page and is not written to `results.json`.

## Saved results

| Concept | Overall | Scientific review | Estimated USD | Validation / API retries |
| --- | --- | --- | ---: | ---: |
| Pythagoras’ theorem | FAIL | Fail | $0.000973 | 0 / 0 |
| Parts of a circle | NEEDS REVIEW | Pass | $0.000741 | 0 / 0 |
| Series circuit | FAIL | Fail | $0.001627 | 1 / 1 |
| Photosynthesis | NEEDS REVIEW | Pass | $0.001860 | 0 / 0 |
| States of matter | FAIL | Fail | $0.001802 | 0 / 2 |

The overall outcomes are not the same as scientific review: all five saved SVGs also need renderer-based bounds review. Costs and retry counts reflect the saved runs; `results.json` is the source of truth if diagrams are regenerated.

## Decisions
- **Persistence:** browser localStorage, keyed by concept id. Simplest to explain and works on Render's free tier, whose disk is wiped on redeploy. Trade-off: decisions are per browser and not shared. With more time I'd use a database such as Postgres or SQLite on a persistent disk.
- **Safety:** the API key is only an environment variable, and Gemini is only called from the server. SVGs are shown inside `<img>` data URIs, so scripts cannot run.
- Generate results are shown in the browser only; they never overwrite `results.json`.

## What failed and how I fixed it
- Gemini wraps SVG in markdown fences (```xml). Fixed with `extract_svg`.
- Rate limits: the saved series circuit and states-of-matter results report 1 and 2 API retries respectively. A retry count alone does not identify the HTTP status.
- Concept 1 first run FAILED `in_viewbox` even after its retry (5,598 output tokens, estimated $0.002313). A fresh run passed.
- Concept 1 then passed all checks but looked wrong: clipped squares, covered title, overlapping labels. Cause: the original viewBox check skipped transformed elements. The check now handles basic static transformed shapes and the prompt reserves a title band. This is why Approve/Reject matters: code cannot judge layout.
- Known limitations: no browser-based text-width, overlap, CSS, reference or animated-bounds verification. The bounds result is unverified rather than passed when these need a renderer. Animation and visibility checks are structural and cannot prove browser playback or resolve all CSS.

## One more day
- Add renderer-based verification for text extents, overlapping labels, CSS and animation over time.
- Render the SVG to an image and ask a vision model to judge it.
- Store review decisions in a database, add reviewer login.
- Save live generations, cache results, add more tests (pipeline with a mocked API).

## AI tools used
Claude: guided troubleshooting and repetitive code writing.

## Current issues
The Current issues panel lists failed automatic checks, recorded scientific-review failures, and live-generation errors for each diagram. It updates after generation, links to the relevant row, and distinguishes diagrams awaiting verification from failures. Live-generation errors remain visible until another attempt for that diagram; they are not persisted.

## Scientific review of the saved diagrams
These verdicts apply only to the exact SVGs in `results.json`; a changed or newly generated SVG requires a new review. Review used SVG source and static renders, and inspected animation paths in source; it did not verify playback in every browser.

- **Pythagoras — FAIL:** the geometry is correct, but area labels use “units” instead of square units, an animated label overlaps the side label, and the accessible title has a typo.
- **Circle — PASS:** centre, radius, diameter and circumference are correctly depicted and described.
- **Series circuit — FAIL:** the right-hand wire has a gap and component connections are unclear.
- **Photosynthesis — PASS:** the inputs, light energy and products are represented correctly at the level of the concept; the word equation is simplified.
- **States of matter — FAIL:** liquid particles are drawn widely separated, contradicting the close spacing described in the concept.

These are reviews of the saved examples, not an automated scientific validator. Local browser Approve/Reject decisions remain separate from these recorded verdicts.
