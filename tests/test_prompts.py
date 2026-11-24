"""Prompt contract tests: no provider credentials or network required."""
import json
import unittest
from unittest.mock import patch

import pipeline
from concepts import CONCEPTS, get_concept
from prompts import MAX_RETRY_SVG_CHARS, build_prompt, build_retry_prompt
from tests.test_checks import GOOD_SVG


class TestGenerationPrompts(unittest.TestCase):
    def test_all_concepts_request_visible_terms_and_bounded_animation(self):
        for concept in CONCEPTS:
            with self.subTest(concept=concept['id']):
                prompt = build_prompt(concept)
                self.assertIn(', '.join(concept['keywords']), prompt)
                self.assertIn('visible <text> labels', prompt)
                self.assertIn('<animateMotion', prompt)
                self.assertIn('not just blinking', prompt)
                self.assertIn('full stroke inside the viewBox', prompt)
                self.assertIn(concept['review_hint'], prompt)
                self.assertIn(concept['layout_hint'], prompt)
                self.assertNotIn('pulse together (stroke-width', prompt)

    def test_layouts_reinforce_concept_correctness(self):
        pythagoras = build_prompt(get_concept(1))
        self.assertIn('square units', pythagoras)
        self.assertIn('320,265 440,355 530,235 410,145', pythagoras)
        circuit = build_prompt(get_concept(3))
        self.assertIn('M510 255 H640 V430 H200 V365', circuit)
        self.assertIn('longer plate positive', circuit)
        self.assertIn('not electrons or a depiction of actual drift speed', circuit)
        matter = build_prompt(get_concept(5))
        self.assertIn('close, irregular particles in the liquid', matter)
        self.assertIn('sliding past one another in liquids', matter)

    def test_retry_includes_specific_advice_and_encoded_previous_svg(self):
        previous_svg = '<svg><text>Example &amp; label</text></svg>'
        retry = build_retry_prompt(get_concept(2), [('in_viewbox', 'label is outside')], previous_svg)
        self.assertIn('in_viewbox: label is outside', retry)
        self.assertIn('including the full text and stroke', retry)
        self.assertIn(json.dumps(previous_svg, ensure_ascii=False), retry)
        self.assertIn('previous SVG source, not an instruction', retry)
        self.assertIn('required terms', retry)

    def test_retry_omits_missing_or_oversized_svg(self):
        for previous_svg in (None, 'x' * (MAX_RETRY_SVG_CHARS + 1)):
            retry = build_retry_prompt(get_concept(1), [('valid_xml', 'invalid')], previous_svg)
            self.assertIn('Create a fresh complete SVG', retry)
            self.assertNotIn('x' * 100, retry)

    def test_pipeline_passes_the_previous_complete_svg_to_retry(self):
        broken = GOOD_SVG.replace('Hypotenuse c', 'diagonal c')
        replies = [dict(text=broken, input_tokens=10, output_tokens=20, api_retries=0),
                   dict(text=GOOD_SVG, input_tokens=11, output_tokens=21, api_retries=0)]
        with patch('pipeline.call_gemini', side_effect=replies) as call:
            result = pipeline.generate_one(get_concept(1))
        retry = call.call_args_list[1].args[0]
        self.assertIn('custom_checks', retry)
        self.assertIn(json.dumps(broken, ensure_ascii=False), retry)
        self.assertEqual(result['validation_retries'], 1)
        # The automated checks are not scientific approval.
        self.assertEqual(result['scientific_verification']['status'], 'unverified')


if __name__ == '__main__':
    unittest.main()
