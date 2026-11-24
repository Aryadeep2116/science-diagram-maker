import unittest
from unittest.mock import patch

import checks
import pipeline
from concepts import get_concept
from gemini_client import GeminiError
from tests.test_checks import GOOD_SVG


class TestSvgEdgeCases(unittest.TestCase):
    def test_invalid_viewbox_dimensions(self):
        for dimensions in ('0 0 0 100', '0 0 -1 100', '0 0 nan 100', '0 0 100 inf'):
            with self.subTest(dimensions=dimensions):
                self.assertFalse(checks.in_viewbox(f'<svg viewBox="{dimensions}"/>')[0])

    def test_nested_transforms_and_bezier_bounds(self):
        inside = '<svg viewBox="0 0 100 100"><g transform="translate(50 0)"><circle cx="10" cy="50" r="4"/></g></svg>'
        outside = inside.replace('translate(50 0)', 'translate(100 0)')
        curve = '<svg viewBox="0 0 100 100"><path d="M 10 10 C 200 200 200 200 200 200"/></svg>'
        self.assertTrue(checks.in_viewbox(inside)[0])
        self.assertFalse(checks.in_viewbox(outside)[0])
        self.assertFalse(checks.in_viewbox(curve)[0])

    def test_visible_labels_exclude_hidden_and_defs(self):
        for hidden in ('<defs>{}</defs>', '<g display="none">{}</g>', '<g style="visibility:hidden">{}</g>', '<g class="hide">{}</g>'):
            labels = '<text>A</text><text>B</text><text>C</text>'
            svg = '<svg><title>T</title><style>.hide {{display:none}}</style>{}</svg>'.format(hidden.format(labels))
            self.assertFalse(checks.title_and_labels(svg)[0])

    def test_animation_must_be_timed_and_used(self):
        for content in ('<animate/>', '<animate attributeName="x" values="0;1" dur="0s"/>',
                        '<style>/* animation: x */ @keyframes x {{from {{opacity:0}} to {{opacity:1}}}}</style>',
                        '<defs><circle><animate attributeName="r" values="1;2" dur="1s"/></circle></defs>',
                        '<style>@keyframes x {from {opacity:0} to {opacity:1}} circle {animation:x 0s}</style><circle/>'):
            self.assertFalse(checks.has_animation('<svg>' + content + '</svg>')[0])

    def test_unsupported_geometry_is_unverified_not_passed(self):
        svg = '<svg viewBox="0 0 100 100"><circle cx="50%" cy="50" r="10"/></svg>'
        result = checks.run_all_checks(svg, get_concept(1))
        self.assertIsNone(result['in_viewbox']['passed'])

    def test_unverified_is_not_a_failed_check(self):
        result = checks.run_all_checks(GOOD_SVG, get_concept(1))
        self.assertTrue(result['in_viewbox']['passed'])
        self.assertIsNone(result['animated_bounds']['passed'])
        self.assertEqual(checks.failed_checks(result), [])


class TestValidationRetry(unittest.TestCase):
    def test_failed_check_retried_once_with_reason(self):
        replies = [dict(text='not an SVG', input_tokens=10, output_tokens=20, api_retries=0),
                   dict(text=GOOD_SVG, input_tokens=11, output_tokens=21, api_retries=0)]
        with patch('pipeline.call_gemini', side_effect=replies) as call:
            result = pipeline.generate_one(get_concept(1))
        self.assertEqual(call.call_count, 2)
        self.assertIn('valid_xml', call.call_args_list[1].args[0])
        self.assertEqual(result['validation_retries'], 1)
        self.assertEqual((result['input_tokens'], result['output_tokens']), (21, 41))
        self.assertEqual(result['final_status'], 'needs_review')

    def test_second_failure_stays_failed(self):
        reply = dict(text='not an SVG', input_tokens=10, output_tokens=20, api_retries=0)
        with patch('pipeline.call_gemini', return_value=reply) as call:
            result = pipeline.generate_one(get_concept(1))
        self.assertEqual(call.call_count, 2)
        self.assertEqual(result['final_status'], 'fail')

    def test_retry_call_failure_keeps_original_result_and_note(self):
        first = dict(text='not an SVG', input_tokens=10, output_tokens=20, api_retries=0)
        with patch('pipeline.call_gemini', side_effect=[first, GeminiError('service failed')]):
            result = pipeline.generate_one(get_concept(1))
        self.assertEqual(result['final_status'], 'fail')
        self.assertIn('service failed', result['note'])
