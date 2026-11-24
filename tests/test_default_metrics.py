"""The replacements keep their SVGs while preserving original run metadata."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app, load_results
from concepts import get_concept
from pipeline import generate_one
from scripts.build_default_results import build_results
from tests.test_checks import GOOD_SVG
from verification import svg_digest

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    1: (0.000973, 1101, 2157, 0, 0, 12.5),
    2: (0.000741, 323, 1773, 0, 0, 5.6),
    3: (0.001627, 990, 3820, 1, 1, 14.8),
    4: (0.00186, 302, 4574, 0, 0, 10.8),
    5: (0.001802, 316, 4427, 0, 2, 30.9),
}
SVG_HASHES = {
    1: '52524ce6f4c007ccf0e21b84f04c17d4346c15cee74652e79af5a9081022747c',
    2: '0a89625aeffac89e8c3fcf60ddecc933be7e76955ec1c5aca8a11dd0877a533d',
    3: '49454023454f2c586720c489de5f39b127cb6bb3a4e17821c44b9705b3934b69',
    4: '559004bb67900cd3fa01500e26db2390606436ee3c9a1bd341033dac46dbffd4',
    5: '7eafb058b8a5f2af2cc0be6f08a3d0c054a503677e8f3d2107c40978b2855fbd',
}


class TestDefaultMetrics(unittest.TestCase):
    def test_original_metrics_are_restored_but_images_remain_new(self):
        metrics = json.loads((ROOT / 'data/original_generation_metrics.json').read_text())
        for result in load_results():
            with self.subTest(concept=result['id']):
                self.assertEqual((result['cost_usd'], result['input_tokens'], result['output_tokens'],
                                  result['validation_retries'], result['api_retries'], result['latency_seconds']),
                                 EXPECTED[result['id']])
                old = metrics[str(result['id'])]
                self.assertEqual(result['model'], old['model'])
                self.assertEqual(result['generated_at'], old['generated_at'])
                self.assertEqual(result['metrics_source'], 'previous_gemini_run')
                self.assertEqual(result['illustration_source'], 'built-in')
                self.assertEqual(result['metrics_svg_sha256'], old['svg_sha256'])
                self.assertNotEqual(result['metrics_svg_sha256'], svg_digest(result['svg']))
                self.assertEqual(svg_digest(result['svg']), SVG_HASHES[result['id']])
                self.assertIn('earlier Gemini-generated SVG', result['note'])
                self.assertEqual(result['final_status'], 'pass')

    def test_rebuilding_defaults_preserves_metrics_and_images(self):
        generated = build_results()
        saved = load_results()
        self.assertEqual(generated, saved)

    def test_live_generation_uses_own_metrics(self):
        reply = {'text': GOOD_SVG, 'input_tokens': 14, 'output_tokens': 27, 'api_retries': 2}
        with patch('pipeline.call_gemini', return_value=reply):
            result = generate_one(get_concept(1))
        self.assertEqual((result['input_tokens'], result['output_tokens'], result['api_retries']), (14, 27, 2))
        self.assertNotIn('metrics_source', result)
        self.assertNotIn('metrics_svg_sha256', result)

    def test_results_api_exposes_metric_provenance(self):
        with app.test_client() as client:
            results = client.get('/api/results').get_json()
        self.assertEqual(len(results), 5)
        self.assertTrue(all(r['metrics_source'] == 'previous_gemini_run' for r in results))


if __name__ == '__main__':
    unittest.main()
