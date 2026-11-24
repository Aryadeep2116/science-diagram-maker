import unittest
from unittest.mock import Mock, patch

import app as web
import config
import gemini_client as gemini
from tests.test_checks import GOOD_SVG


def response(status, body=None, headers=None):
    result = Mock()
    result.status_code = status
    result.headers = headers or {}
    result.json.return_value = body or {}
    return result


class TestGeminiErrorsAndRetries(unittest.TestCase):
    def setUp(self):
        self.key = patch.object(config, 'GEMINI_API_KEY', 'test-key-not-real')
        self.key.start()
        self.addCleanup(self.key.stop)

    def test_success_after_rate_limit_counts_retry(self):
        ok = response(200, {'candidates': [{'content': {'parts': [{'text': GOOD_SVG}]}}],
                            'usageMetadata': {'promptTokenCount': 12, 'candidatesTokenCount': 34}})
        with patch('gemini_client._post_once', side_effect=[response(429), ok]) as post, \
             patch('gemini_client.time.sleep') as sleep:
            result = gemini.call_gemini('prompt')
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(2)
        self.assertEqual((result['api_retries'], result['input_tokens'], result['output_tokens']), (1, 12, 34))

    def test_long_quota_reset_is_not_retried_early(self):
        limited = response(429, {'error': {'details': [
            {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '45.1s'}]}})
        with patch('gemini_client._post_once', return_value=limited) as post, \
             patch('gemini_client.time.sleep') as sleep:
            with self.assertRaises(gemini.GeminiRateLimitError) as error:
                gemini.call_gemini('prompt')
        self.assertIn('46 seconds', str(error.exception))
        post.assert_called_once()
        sleep.assert_not_called()

    def test_short_retry_after_is_honoured_and_retries_stop(self):
        with patch('gemini_client._post_once', return_value=response(429, headers={'Retry-After': '3'})) as post, \
             patch('gemini_client.time.sleep') as sleep:
            with self.assertRaises(gemini.GeminiRateLimitError):
                gemini.call_gemini('prompt')
        self.assertEqual(post.call_count, 4)
        self.assertEqual(sleep.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [3, 3, 3])

    def test_overload_is_not_reported_as_quota(self):
        with patch('gemini_client._post_once', return_value=response(503)), patch('gemini_client.time.sleep'):
            with self.assertRaises(gemini.GeminiOverloadedError) as error:
                gemini.call_gemini('prompt')
        self.assertIn('503', str(error.exception))
        self.assertNotIn('quota', str(error.exception))

    def test_bad_request_is_not_mislabeled_as_bad_key(self):
        with patch('gemini_client._post_once', return_value=response(400, {'error': {'message': 'invalid request'}})):
            with self.assertRaises(gemini.GeminiError) as error:
                gemini.call_gemini('prompt')
        self.assertNotIsInstance(error.exception, gemini.GeminiKeyError)
        self.assertIn('HTTP 400', str(error.exception))

    def test_invalid_key_and_access_denied_are_distinct(self):
        invalid = response(400, {'error': {'details': [{'reason': 'API_KEY_INVALID'}], 'message': 'secret-content'}})
        with patch('gemini_client._post_once', return_value=invalid):
            with self.assertRaises(gemini.GeminiKeyError) as error:
                gemini.call_gemini('prompt')
        self.assertNotIn('secret-content', str(error.exception))
        with patch('gemini_client._post_once', return_value=response(403)):
            with self.assertRaises(gemini.GeminiError) as error:
                gemini.call_gemini('prompt')
        self.assertNotIsInstance(error.exception, gemini.GeminiKeyError)
        self.assertIn('HTTP 403', str(error.exception))


class TestGenerateEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = web.app.test_client()
        web.last_finished = 0
        self.addCleanup(setattr, web, 'last_finished', 0)

    @patch('pipeline.call_gemini')
    def test_generation_endpoint_runs_pipeline_and_returns_new_diagram(self, call):
        call.return_value = {'text': GOOD_SVG, 'input_tokens': 5, 'output_tokens': 10, 'api_retries': 0}
        result = self.client.post('/api/generate/1')
        self.assertEqual(result.status_code, 200)
        self.assertIn('<svg', result.get_json()['svg'])
        call.assert_called_once()

    def test_missing_key_is_a_clear_error(self):
        with patch.object(config, 'GEMINI_API_KEY', None):
            result = self.client.post('/api/generate/1')
        self.assertEqual(result.status_code, 500)
        self.assertIn('GEMINI_API_KEY', result.get_json()['error'])

    def test_503_has_its_own_status(self):
        with patch('app.generate_one', side_effect=gemini.GeminiOverloadedError('temporarily unavailable')):
            result = self.client.post('/api/generate/1')
        self.assertEqual(result.status_code, 503)
        self.assertIn('temporarily unavailable', result.get_json()['error'])

    def test_cooldown_rejection_does_not_extend_cooldown(self):
        web.last_finished = 100
        with patch('app.time.time', return_value=102):
            result = self.client.post('/api/generate/1')
        self.assertEqual(result.status_code, 429)
        self.assertEqual(web.last_finished, 100)

    def test_unknown_concept(self):
        result = self.client.post('/api/generate/999')
        self.assertEqual(result.status_code, 404)
