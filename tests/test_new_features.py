import json
import unittest
from unittest.mock import patch

import app as web
import config
import gemini_client as gemini
import pipeline
from concepts import get_concept
from prompts import build_prompt, build_retry_prompt
from render_bounds import rendered_bounds
from tests.test_checks import GOOD_SVG
from tests.test_generate import response


class TestRenderer(unittest.TestCase):
    def test_rendered_text_outside_viewbox_fails(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text x="90" y="50" font-size="20">LONG LABEL</text></svg>'
        passed, reason = rendered_bounds(svg)
        self.assertFalse(passed, reason)
        self.assertIn('outside', reason)

    def test_rendered_text_inside_passes_static_snapshot(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text x="10" y="50" font-size="10">OK</text></svg>'
        self.assertTrue(rendered_bounds(svg)[0])

    def test_moving_svg_keeps_animated_bounds_unverified(self):
        from checks import run_all_checks
        result = run_all_checks(GOOD_SVG, get_concept(1))
        self.assertTrue(result['in_viewbox']['passed'])
        self.assertIsNone(result['animated_bounds']['passed'])

    def test_relative_css_geometry_is_not_certified_by_padded_renderer(self):
        from checks import run_all_checks
        svg = GOOD_SVG.replace('</svg>', '<style>circle { cx: 90%; }</style></svg>')
        self.assertIsNone(run_all_checks(svg, get_concept(1))['in_viewbox']['passed'])

    def test_opacity_only_animation_can_pass_bounds(self):
        from checks import run_all_checks
        svg = GOOD_SVG.replace('attributeName="r" values="8;14;8"',
                               'attributeName="opacity" values="1;0.35;1"')
        self.assertTrue(run_all_checks(svg, get_concept(1))['animated_bounds']['passed'])

    def test_unsupported_animation_never_gets_opacity_proof(self):
        from checks import run_all_checks
        svg = GOOD_SVG.replace('attributeName="r" values="8;14;8"',
                               'attributeName="opacity" values="1;0.35;1"')
        for altered in (svg.replace('<circle cx=', '<circle opacity="0" cx='),
                        svg.replace('dur="2s"', 'additive="sum" dur="2s"'),
                        svg.replace('<title>', '<style>circle { opacity: 0 }</style><title>'),
                        svg.replace('values="1;0.35;1"', 'values="1;2;1"'),
                        svg.replace('dur="2s"', 'href="#other" dur="2s"')):
            self.assertIsNone(run_all_checks(altered, get_concept(1))['animated_bounds']['passed'])

    def test_opacity_proof_requires_successful_static_bounds(self):
        from checks import run_all_checks
        svg = GOOD_SVG.replace('attributeName="r" values="8;14;8"',
                               'attributeName="opacity" values="1;0.35;1"').replace('cx="100"', 'cx="2000"')
        checks = run_all_checks(svg, get_concept(1))
        self.assertFalse(checks['in_viewbox']['passed'])
        self.assertIsNone(checks['animated_bounds']['passed'])

    def test_external_resources_not_loaded_by_renderer(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><image href="file:///etc/passwd" width="10" height="10"/></svg>'
        self.assertIsNone(rendered_bounds(svg)[0])


class TestFallback(unittest.TestCase):
    def setUp(self):
        self.key = patch.object(config, 'GEMINI_API_KEY', 'fake-key')
        self.fallback = patch.object(config, 'GEMINI_FALLBACK_MODEL', 'backup-model')
        self.key.start(); self.fallback.start()
        self.addCleanup(self.key.stop); self.addCleanup(self.fallback.stop)

    def test_fallback_after_quota_and_reports_actual_model(self):
        ok = response(200, {'candidates': [{'content': {'parts': [{'text': GOOD_SVG}]}}],
                            'usageMetadata': {'promptTokenCount': 12, 'candidatesTokenCount': 34}})
        with patch('gemini_client._post_once', side_effect=[response(429, headers={'Retry-After': '50'}), ok]) as post:
            result = gemini.call_gemini('prompt')
        self.assertEqual(result['model'], 'backup-model')
        self.assertEqual(result['fallback_from'], config.GEMINI_MODEL)
        self.assertEqual(post.call_args_list[1].args, ('prompt', 'backup-model'))

    def test_503_uses_configured_fallback_after_retries(self):
        ok = response(200, {'candidates': [{'content': {'parts': [{'text': GOOD_SVG}]}}]})
        with patch('gemini_client._post_once', side_effect=[response(503)] * 4 + [ok]) as post, \
             patch('gemini_client.time.sleep'):
            result = gemini.call_gemini('prompt')
        self.assertEqual(post.call_count, 5)
        self.assertEqual(result['model'], 'backup-model')
        self.assertEqual(result['api_retries'], 3)

    def test_fallback_not_used_for_invalid_key(self):
        with patch('gemini_client._post_once', return_value=response(401)) as post:
            with self.assertRaises(gemini.GeminiKeyError):
                gemini.call_gemini('prompt')
        self.assertEqual(post.call_count, 1)

    def test_fallback_cost_not_guessed(self):
        reply = {'text': GOOD_SVG, 'input_tokens': 10, 'output_tokens': 20, 'api_retries': 0,
                 'model': 'backup-model', 'fallback_from': config.GEMINI_MODEL}
        with patch('pipeline.call_gemini', return_value=reply), \
             patch.object(config, 'FALLBACK_INPUT_PRICE', None), patch.object(config, 'FALLBACK_OUTPUT_PRICE', None):
            result = pipeline.generate_one(get_concept(1))
        self.assertEqual(result['model'], 'backup-model')
        self.assertIsNone(result['cost_usd'])
        self.assertIn('fallback', result['note'])


class TestConfigurationAndPrompt(unittest.TestCase):
    def test_status_never_returns_key(self):
        with patch.object(config, 'GEMINI_API_KEY', 'do-not-expose-me'):
            with web.app.test_client() as client:
                result = client.get('/api/status')
        self.assertTrue(result.get_json()['key_configured'])
        self.assertNotIn('do-not-expose-me', result.get_data(as_text=True))
        self.assertEqual(result.get_json()['provider_status'], 'not_checked')

    def test_recheck_does_not_trust_browser_verdict(self):
        with web.app.test_client() as client:
            response = client.post('/api/check/1', json={'svg': GOOD_SVG,
                'scientific_verification': {'status': 'pass'}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['scientific_verification']['status'], 'unverified')
        self.assertEqual(response.get_json()['final_status'], 'needs_review')

    def test_concept_specific_prompt_and_retry(self):
        circuit = get_concept(3)
        prompt = build_prompt(circuit)
        self.assertIn('single closed loop', prompt)
        retry = build_retry_prompt(circuit, [('in_viewbox', 'text extends outside')])
        self.assertIn('text extends outside', retry)
        self.assertIn('electrically connected', retry)
