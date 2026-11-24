# prompts.py
# Builds the text we send to the model. Two versions:
#   1) the first-attempt prompt
#   2) the retry prompt, which also tells the model exactly what went wrong

import config


def build_prompt(concept):
    """Make the first-attempt prompt for one concept."""
    prompt = f"""You are an expert science teacher and SVG artist.
Create ONE animated SVG diagram for UK GCSE students about this concept.

Subject: {concept['subject']}
Concept: {concept['name']}
Explanation: {concept['text']}

STRICT RULES:
1. Reply with SVG code ONLY. No markdown fences, no explanation text.
2. The root tag must be exactly: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {config.VIEWBOX_WIDTH} {config.VIEWBOX_HEIGHT}">
3. Include a <title> element as a child of <svg> naming the concept.
4. Include at least 5 clear <text> labels using the key terms from the explanation.
5. Keep EVERYTHING (shapes and text) inside the viewBox, with a margin of at least 20 units.
6. Use font-size of 14 or larger so text is readable.
7. Include meaningful looping animation that illustrates the idea
   (for example: moving current dots, vibrating particles, a pulsing shape).
   Use SMIL (<animate>, <animateTransform>, <animateMotion>) or CSS @keyframes.
8. Do NOT use <script>, <foreignObject>, event attributes (onclick etc.) or external links/images.
9. Keep the design clean and simple with good colour contrast on a light background.
10. Do NOT use transform attributes on shapes. Write every shape with absolute coordinates
    (for a tilted square, use a <polygon> with four explicit points).
11. Keep the title and subtitle in their own band at the top (y between 20 and 70) and
    draw NOTHING else in that band.
12. Never place two text labels on top of each other; leave at least 20 units between labels,
    and keep the bottom 80 units free for a formula caption only.
13. Never use HTML entities such as &nbsp; &sup2; &times;. Type the characters directly
    (², ×) or use numeric references. Only &amp; &lt; &gt; are allowed.
"""
    if concept.get("review_hint"):
        prompt += "\nSCIENTIFIC ACCURACY REQUIREMENTS:\n" + concept["review_hint"] + "\n"
    hint = concept.get("layout_hint")
    if hint:
        prompt += "\nFIXED LAYOUT (copy these coordinates exactly):\n" + hint + "\n"
    return prompt


def build_retry_prompt(concept, failures):
    """Make the retry prompt, naming exactly which checks failed and why."""
    base = build_prompt(concept)

    problem_lines = []
    for check_name, reason in failures:
        problem_lines.append(f"- {check_name}: {reason}")
    problems = "\n".join(problem_lines)

    return (
        base
        + "\nYOUR PREVIOUS ATTEMPT WAS REJECTED by automatic checks. Problems found:\n"
        + problems
        + "\n\nFix ALL of these problems without weakening the scientific content. "
          "Pay particular attention to: " + concept.get("review_hint", "clear, accurate labels and geometry")
        + "\nReturn the complete corrected SVG only."
    )