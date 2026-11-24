"""Regression checks for the scientific motion in the built-in SVG examples."""
import math
import unittest
import xml.etree.ElementTree as ET

from svgelements import Path
from app import load_results

NS = {'svg': 'http://www.w3.org/2000/svg'}


def items(root, kind):
    return root.findall(f".//*[@data-motion='{kind}']")


class TestDefaultMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = {r['id']: r for r in load_results()}
        cls.roots = {i: ET.fromstring(r['svg']) for i, r in cls.results.items()}

    def test_motion_does_not_claim_unverified_bounds_as_pass(self):
        for result in self.results.values():
            self.assertTrue(result['checks']['in_viewbox']['passed'])
            self.assertIsNone(result['checks']['animated_bounds']['passed'])
            self.assertEqual(result['final_status'], 'needs_review')
            self.assertEqual(result['scientific_verification']['status'], 'pass')

    def test_each_example_has_real_looping_motion(self):
        for concept_id, root in self.roots.items():
            with self.subTest(concept=concept_id):
                animations = root.findall('.//svg:animateMotion', NS) + root.findall('.//svg:animateTransform', NS)
                self.assertTrue(animations)
                self.assertTrue(all(a.get('repeatCount') == 'indefinite' for a in animations))

    def test_circuit_markers_follow_the_same_closed_loop(self):
        markers = items(self.roots[3], 'conventional-current')
        self.assertEqual(len(markers), 4)
        motions = [m.find('svg:animateMotion', NS) for m in markers]
        self.assertEqual(len({a.get('path') for a in motions}), 1)
        self.assertEqual({a.get('begin') for a in motions}, {'0s', '-2s', '-4s', '-6s'})
        path = Path(motions[0].get('path'))
        self.assertEqual(tuple(path[1].start), (200, 335))
        self.assertEqual(tuple(path[-1].end), (200, 335))
        self.assertEqual(path.bbox(), (200, 255, 640, 430))

    def test_leaf_inputs_and_outputs_move_in_correct_directions(self):
        root = self.roots[4]
        for kind, axis, sign in [('carbon-dioxide-in', 'x', 1), ('water-in', 'x', 1),
                                 ('oxygen-out', 'x', 1), ('glucose-out', 'x', 1),
                                 ('light-in', 'y', 1)]:
            motion = items(root, kind)[0].find('svg:animateMotion', NS)
            path = Path(motion.get('path'))
            delta = getattr(path[-1].end, axis) - getattr(path[1].start, axis)
            self.assertGreater(delta * sign, 0, kind)

    def test_particle_motion_stays_inside_its_container(self):
        root = self.roots[5]
        for kind, rect, count, duration in [
            ('solid-vibration', (70, 198, 244, 363), 16, '0.7s'),
            ('liquid-exchange', (313, 198, 487, 363), 16, '3.2s'),
            ('gas-motion', (556, 198, 730, 363), 6, '1.4s'),
        ]:
            particles = items(root, kind)
            self.assertEqual(len(particles), count)
            for particle in particles:
                animation = particle.find('svg:animateMotion', NS)
                self.assertEqual(animation.get('dur'), duration)
                left, top, right, bottom = Path(animation.get('path')).bbox()
                r = float(particle.get('r')) + float(particle.get('stroke-width')) / 2
                self.assertGreaterEqual(left-r, rect[0], kind)
                self.assertGreaterEqual(top-r, rect[1], kind)
                self.assertLessEqual(right+r, rect[2], kind)
                self.assertLessEqual(bottom+r, rect[3], kind)

    def test_rotating_radius_is_fixed_at_the_centre(self):
        group = items(self.roots[2], 'rotating-radius')[0]
        line = group.find('svg:line', NS)
        animation = group.find('svg:animateTransform', NS)
        self.assertEqual((line.get('x1'), line.get('y1')), ('260', '300'))
        self.assertEqual(animation.get('from'), '0 260 300')
        self.assertEqual(animation.get('to'), '360 260 300')
        self.assertAlmostEqual(math.hypot(float(line.get('x2')) - 260, float(line.get('y2')) - 300), 150)


if __name__ == '__main__':
    unittest.main()
