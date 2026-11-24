"""Exercise the conservative verifier, including cases it must not certify."""
import unittest
import xml.etree.ElementTree as ET

from checks import run_all_checks
from concepts import get_concept
from motion_bounds import bounded_motion, linear_path_bounds


class TestLinearPathBounds(unittest.TestCase):
    def test_absolute_relative_and_implicit_segments(self):
        self.assertEqual(linear_path_bounds('M10 20 l5 -10 4 2 H30 v20 h-3'), (10, 10, 30, 32))
        self.assertEqual(linear_path_bounds('M1e1 20 L30 40'), (10, 20, 30, 40))

    def test_unsupported_and_invalid_paths_are_not_certified(self):
        for path in ('', 'M0 0', 'M0 0 C20 30 40 50 60 70', 'M0 0 A5 5 0 0 0 40 50',
                     'M0 0 L10', 'M0 0 L10 1e999', 'M0 0 L10 10 junk', 'M0 0 Z'):
            with self.subTest(path=path):
                self.assertIsNone(linear_path_bounds(path))


class TestBoundedMotion(unittest.TestCase):
    def setUp(self):
        self.svg = ('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <title>Pythagoras</title><text x="10" y="20" font-size="8">hypotenuse</text>
          <text x="10" y="35">a</text><text x="10" y="50">b</text>
          <circle cx="0" cy="0" r="5" fill="blue" stroke="white" stroke-width="1.5">
          <animateMotion path="M20 20 L80 80" dur="4s" calcMode="linear" repeatCount="indefinite"/>
          </circle></svg>''')

    def certified(self, svg):
        return bounded_motion(ET.fromstring(svg))

    def test_safe_bounded_motion_passes_without_approving_science(self):
        self.assertTrue(self.certified(self.svg))
        checks = run_all_checks(self.svg, get_concept(1))
        self.assertTrue(checks['animated_bounds']['passed'])

    def test_outside_and_border_crossing_remain_unverified(self):
        for end in ('L101 80', 'L96 80', 'L80 -10'):
            svg = self.svg.replace('L80 80', end)
            self.assertFalse(self.certified(svg))
            checks = run_all_checks(svg, get_concept(1))
            self.assertIsNone(checks['animated_bounds']['passed'])

    def test_rotation_bounds_include_the_full_sweep_and_stroke(self):
        svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g>
          <line x1="50" y1="50" x2="80" y2="50" stroke="blue" stroke-width="2"/>
          <circle cx="80" cy="50" r="4" fill="red" stroke="white" stroke-width="1"/>
          <animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur="3s" repeatCount="indefinite"/>
          </g></svg>'''
        self.assertTrue(self.certified(svg))
        self.assertFalse(self.certified(svg.replace('x2="80"', 'x2="100"')))
        self.assertFalse(self.certified(svg.replace('to="360 50 50"', 'to="360 60 50"')))

    def test_complex_or_unsafe_features_remain_unverified(self):
        for altered in (
            self.svg.replace('M20 20 L80 80', 'M20 20 C30 40 50 60 80 80'),
            self.svg.replace('calcMode="linear"', 'calcMode="spline"'),
            self.svg.replace('dur="4s"', 'dur="4s" additive="sum"'),
            self.svg.replace('cx="0"', 'cx="10"'),
            self.svg.replace('<circle cx=', '<circle transform="translate(20 0)" cx='),
            self.svg.replace('<circle cx=', '<circle style="stroke-width:50" cx='),
            self.svg.replace('<circle cx=', '<circle vector-effect="non-scaling-stroke" cx='),
            self.svg.replace('<title>', '<style>circle { stroke-width: 40 }</style><title>'),
            self.svg.replace('<title>', '<script>alert(1)</script><title>'),
            self.svg.replace('<animateMotion ', '<animateMotion href="#other" '),
            self.svg.replace('</circle>', '<animate attributeName="r" values="5;100" dur="2s"/></circle>'),
            self.svg.replace('<circle cx=', '<g><circle cx=').replace('</circle></svg>', '</circle></g></svg>'),
        ):
            with self.subTest(svg=altered):
                self.assertFalse(self.certified(altered))
                self.assertIsNone(run_all_checks(altered, get_concept(1))['animated_bounds']['passed'])

    def test_failed_or_unverified_static_bounds_cannot_be_overridden(self):
        svg = self.svg.replace('x="10" y="20"', 'x="200" y="20"')
        checks = run_all_checks(svg, get_concept(1))
        self.assertFalse(checks['in_viewbox']['passed'])
        self.assertIsNone(checks['animated_bounds']['passed'])


if __name__ == '__main__':
    unittest.main()
