# tests/test_checks.py
# Proves each check passes on a good SVG and fails on a deliberately bad one.
# Run from the project root with:  python -m unittest -v

import unittest
from concepts import get_concept
import checks

PYTHAGORAS = get_concept(1)     # keyword: hypotenuse
CIRCLE = get_concept(2)         # keywords: centre, radius, diameter, circumference

# A good SVG: title, 3+ labels, inside the viewBox, animated, safe.
GOOD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
  <title>Pythagoras' theorem</title>
  <polygon points="100,500 500,500 500,200" fill="#cde" stroke="#036"/>
  <text x="300" y="530" font-size="16">a</text>
  <text x="520" y="350" font-size="16">b</text>
  <text x="270" y="330" font-size="16">Hypotenuse c</text>
  <circle cx="100" cy="500" r="8" fill="red">
    <animate attributeName="r" values="8;14;8" dur="2s" repeatCount="indefinite"/>
  </circle>
</svg>"""


class TestChecks(unittest.TestCase):

    def test_good_svg_passes_static_checks_but_bounds_need_rendering_review(self):
        results = checks.run_all_checks(GOOD_SVG, PYTHAGORAS)
        self.assertIsNone(results["in_viewbox"]["passed"])
        for name, outcome in results.items():
            if name != "in_viewbox":
                self.assertTrue(outcome["passed"], f"{name} failed: {outcome['reason']}")

    def test_broken_xml_fails(self):
        passed, _ = checks.valid_xml("<svg><title>oops</svg>")     # tags do not match
        self.assertFalse(passed)

    def test_empty_reply_fails(self):
        passed, _ = checks.valid_xml("")
        self.assertFalse(passed)

    def test_broken_xml_skips_other_checks(self):
        results = checks.run_all_checks("<svg><title>oops</svg>", PYTHAGORAS)
        self.assertFalse(results["in_viewbox"]["passed"])
        self.assertEqual(checks.failed_checks(results)[0][0], "valid_xml")   # only the real failure is listed

    def test_circle_outside_viewbox_fails(self):
        bad = GOOD_SVG.replace('cx="100"', 'cx="2000"')
        passed, reason = checks.in_viewbox(bad)
        self.assertFalse(passed)
        self.assertIn("circle", reason)

    def test_text_below_viewbox_fails(self):
        bad = GOOD_SVG.replace('y="530"', 'y="700"')
        passed, _ = checks.in_viewbox(bad)
        self.assertFalse(passed)

    def test_transformed_element_outside_fails(self):
        skipped = GOOD_SVG.replace('<circle cx="100"', '<circle transform="translate(5,5)" cx="2000"')
        passed, _ = checks.in_viewbox(skipped)
        self.assertFalse(passed)

    def test_missing_title_fails(self):
        bad = GOOD_SVG.replace("<title>Pythagoras' theorem</title>", "")
        passed, reason = checks.title_and_labels(bad)
        self.assertFalse(passed)
        self.assertIn("title", reason)

    def test_too_few_labels_fails(self):
        bad = GOOD_SVG.replace('<text x="300" y="530" font-size="16">a</text>', "")
        passed, _ = checks.title_and_labels(bad)       # only 2 labels left
        self.assertFalse(passed)

    def test_no_animation_fails(self):
        bad = GOOD_SVG.replace('<animate attributeName="r" values="8;14;8" dur="2s" repeatCount="indefinite"/>', "")
        passed, _ = checks.has_animation(bad)
        self.assertFalse(passed)

    def test_css_animation_passes(self):
        css_svg = GOOD_SVG.replace(
            "<title>", "<style>@keyframes spin {from {opacity:0} to {opacity:1}} circle {animation: spin 2s infinite;}</style><title>")
        passed, _ = checks.has_animation(css_svg.replace("<animate", "<desc").replace("</animate>", "</desc>"))
        self.assertTrue(passed)

    def test_script_tag_fails_safety(self):
        bad = GOOD_SVG.replace("<title>", "<script>alert(1)</script><title>")
        passed, reason = checks.safe_svg(bad)
        self.assertFalse(passed)
        self.assertIn("script", reason)

    def test_event_attribute_fails_safety(self):
        bad = GOOD_SVG.replace('<circle ', '<circle onclick="x()" ')
        passed, _ = checks.safe_svg(bad)
        self.assertFalse(passed)

    def test_external_link_fails_safety(self):
        bad = GOOD_SVG.replace("</svg>", '<image href="https://evil.example/x.png"/></svg>')
        passed, _ = checks.safe_svg(bad)
        self.assertFalse(passed)

    def test_missing_keywords_fail(self):
        # The Pythagoras diagram is valid but is NOT a diagram about circles.
        passed, reason = checks.concept_keywords(GOOD_SVG, CIRCLE)
        self.assertFalse(passed)
        self.assertIn("radius", reason)


if __name__ == "__main__":
    unittest.main()

    