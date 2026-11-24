import json
import unittest
from unittest.mock import patch

from app import app, load_results
from concepts import get_concept
from pipeline import generate_one
from tests.test_checks import GOOD_SVG, PYTHAGORAS
from verification import assess_result, svg_digest


class TestVerification(unittest.TestCase):
    def test_saved_series_circuit_is_failed_with_reason(self):
        result = next(r for r in load_results() if r['id'] == 3)
        self.assertEqual(result['final_status'], 'fail')
        self.assertEqual(result['scientific_verification']['status'], 'fail')
        self.assertIn('gap', result['scientific_verification']['reason'])
        self.assertTrue(all(c['passed'] is not False for c in result['checks'].values()))
        self.assertIsNone(result['checks']['in_viewbox']['passed'])

    def test_passed_automatic_checks_need_scientific_review(self):
        result = assess_result({'svg': GOOD_SVG, 'final_status': 'pass'}, PYTHAGORAS)
        self.assertEqual(result['final_status'], 'needs_review')
        self.assertEqual(result['scientific_verification']['status'], 'unverified')

    def test_review_only_applies_to_exact_svg(self):
        verification = {'status': 'pass', 'reason': 'Reviewed', 'svg_sha256': svg_digest(GOOD_SVG)}
        reviewed = assess_result({'svg': GOOD_SVG, 'scientific_verification': verification}, PYTHAGORAS)
        self.assertEqual(reviewed['final_status'], 'needs_review')  # bounds still need rendering review
        self.assertEqual(reviewed['scientific_verification']['status'], 'pass')
        changed = assess_result({'svg': GOOD_SVG + ' ', 'scientific_verification': verification}, PYTHAGORAS)
        self.assertEqual(changed['final_status'], 'needs_review')

    def test_automatic_failure_cannot_be_overridden_by_review(self):
        svg = GOOD_SVG.replace('<title>Pythagoras\' theorem</title>', '')
        result = assess_result({'svg': svg, 'scientific_verification': {
            'status': 'pass', 'reason': 'Reviewed', 'svg_sha256': svg_digest(svg)}}, PYTHAGORAS)
        self.assertEqual(result['final_status'], 'fail')

    @patch('pipeline.call_gemini')
    def test_generation_does_not_claim_scientific_pass(self, call):
        call.return_value = {'text': GOOD_SVG, 'input_tokens': 10, 'output_tokens': 20, 'api_retries': 0}
        result = generate_one(PYTHAGORAS)
        self.assertEqual(result['final_status'], 'needs_review')
        self.assertEqual(result['validation_retries'], 0)

    def test_api_reports_series_fail(self):
        with app.test_client() as client:
            response = client.get('/api/results')
        result = next(r for r in response.get_json() if r['id'] == 3)
        self.assertEqual(result['final_status'], 'fail')
        self.assertEqual(result['scientific_verification']['status'], 'fail')


class TestSavedScientificReviews(unittest.TestCase):
    def test_all_saved_diagrams_have_verdicts_for_the_current_svg(self):
        results = {result['id']: result for result in load_results()}
        self.assertEqual({i: results[i]['scientific_verification']['status'] for i in range(1, 6)},
                         {1: 'fail', 2: 'pass', 3: 'fail', 4: 'pass', 5: 'fail'})
        for result in results.values():
            review = result['scientific_verification']
            self.assertEqual(review['svg_sha256'], svg_digest(result['svg']))
            self.assertTrue(review['reason'])
            self.assertEqual(result['final_status'], 'needs_review' if review['status'] == 'pass' else 'fail')

    def test_saved_verdict_is_invalidated_when_svg_changes(self):
        result = next(r for r in load_results() if r['id'] == 2)
        result['svg'] += ' '
        result = assess_result(result, get_concept(2))
        self.assertEqual(result['scientific_verification']['status'], 'unverified')
        self.assertEqual(result['final_status'], 'needs_review')


if __name__ == '__main__':
    unittest.main()
