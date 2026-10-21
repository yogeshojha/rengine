"""Tests for the named OrcaRouter provider.

These tests are intentionally database-free: they exercise the provider
package (catalog parsing/filtering, credential handling, chat client) with
fake HTTP sessions so they can run without PostgreSQL, Celery or network
access. A live catalog check is included but skipped unless
``ORCAROUTER_API_KEY`` is present in the environment.
"""

import os
import unittest
from unittest import mock

from orcarouter import config
from orcarouter.catalog import (
	CatalogResult,
	OrcaRouterCatalogError,
	fetch_chat_catalog,
	filter_models,
	model_ids,
	parse_catalog_payload,
	pick_default_orcarouter_model,
	reconcile_selection,
	seed_catalog,
)
from orcarouter.client import OrcaRouterError, chat_completion, mask_key, redact, resolve_api_key


class FakeResponse:
	def __init__(self, status_code=200, payload=None, body=None, reason=''):
		self.status_code = status_code
		self._payload = payload
		self._body = body
		self.reason = reason

	def json(self):
		if self._payload is None:
			raise ValueError('no json')
		return self._payload

	def iter_content(self, chunk_size=8192):
		body = self._body
		if body is None:
			body = b''
		if isinstance(body, str):
			body = body.encode('utf-8')
		for index in range(0, len(body), chunk_size):
			yield body[index:index + chunk_size]


class FakeSession:
	def __init__(self, response=None, exc=None, payload=None):
		self.response = response
		self.exc = exc
		self.payload = payload
		self.calls = []

	def get(self, url, **kwargs):
		self.calls.append((url, kwargs))
		if self.exc:
			raise self.exc
		return self.response

	def post(self, url, **kwargs):
		self.calls.append((url, kwargs))
		if self.exc:
			raise self.exc
		return self.response


CATALOG_PAYLOAD = {
	'data': [
		{
			'id': 'anthropic/claude-opus-4.8',
			'owned_by': 'anthropic',
			'supported_endpoint_types': ['anthropic', 'openai'],
			'architecture': {'input_modalities': ['text', 'image']},
			'context_length': 200000,
			'max_completion_tokens': 64000,
			'pricing': {'prompt': '0.000005', 'completion': '0.000025'},
		},
		{
			'id': 'deepseek/deepseek-v4-pro',
			'owned_by': 'deepseek',
			'supported_endpoint_types': ['openai'],
			'architecture': {'input_modalities': ['text']},
			'context_length': 1048576,
		},
		{
			'id': 'acme/text-embed-3',
			'owned_by': 'acme',
			'supported_endpoint_types': ['embeddings'],
		},
		{
			'id': 'acme/draw-2',
			'owned_by': 'acme',
			'supported_endpoint_types': ['image-generation'],
		},
		{
			'id': 'acme/motion-1',
			'owned_by': 'acme',
			'supported_endpoint_types': ['openai-video'],
		},
		{
			'id': 'acme/rank-1',
			'owned_by': 'acme',
			'supported_endpoint_types': ['jina-rerank'],
		},
		{
			'id': 'orcarouter/fusion',
			'owned_by': 'orcarouter',
			'supported_endpoint_types': ['openai', 'openai-response', 'anthropic', 'gemini'],
			'architecture': {'input_modalities': ['text']},
			'context_length': 1000000,
		},
	]
}


class TestCatalogParsing(unittest.TestCase):
	def test_accepts_openai_envelope(self):
		models = parse_catalog_payload(CATALOG_PAYLOAD)
		ids = model_ids(models)
		self.assertIn('anthropic/claude-opus-4.8', ids)
		self.assertIn('orcarouter/fusion', ids)

	def test_accepts_bare_list(self):
		models = parse_catalog_payload(CATALOG_PAYLOAD['data'])
		self.assertTrue(models)

	def test_preserves_catalog_metadata(self):
		models = parse_catalog_payload(CATALOG_PAYLOAD)
		opus = next(m for m in models if m['id'] == 'anthropic/claude-opus-4.8')
		self.assertEqual(opus['owned_by'], 'anthropic')
		self.assertEqual(opus['context_length'], 200000)
		self.assertEqual(opus['max_completion_tokens'], 64000)
		self.assertIn('image', opus['input_modalities'])
		self.assertEqual(opus['pricing']['prompt'], '0.000005')

	def test_rejects_unexpected_shapes(self):
		for payload in ('nope', 42, {'data': 'nope'}, {'models': []}):
			with self.assertRaises(OrcaRouterCatalogError):
				parse_catalog_payload(payload)

	def test_deduplicates_ids(self):
		payload = {'data': [
			{'id': 'orcarouter/fusion', 'supported_endpoint_types': ['openai']},
			{'id': 'orcarouter/fusion', 'supported_endpoint_types': ['openai']},
		]}
		self.assertEqual(model_ids(parse_catalog_payload(payload)), ['orcarouter/fusion'])

	def test_drops_records_without_id(self):
		payload = {'data': [{'owned_by': 'x'}, {'id': '   '}, {'id': 'ok/model',
			'supported_endpoint_types': ['openai']}]}
		self.assertEqual(model_ids(parse_catalog_payload(payload)), ['ok/model'])

	def test_bounds_number_of_models(self):
		payload = {'data': [
			{'id': f'acme/model-{i}', 'supported_endpoint_types': ['openai']}
			for i in range(config.CATALOG_MAX_MODELS + 25)
		]}
		models = parse_catalog_payload(payload)
		self.assertEqual(len(models), config.CATALOG_MAX_MODELS)


class TestCapabilityFiltering(unittest.TestCase):
	def setUp(self):
		self.models = parse_catalog_payload(CATALOG_PAYLOAD)

	def test_chat_excludes_non_chat_capabilities(self):
		ids = model_ids(self.models)
		self.assertNotIn('acme/text-embed-3', ids)
		self.assertNotIn('acme/draw-2', ids)
		self.assertNotIn('acme/motion-1', ids)
		self.assertNotIn('acme/rank-1', ids)

	def test_embedding_capability(self):
		self.assertEqual(
			model_ids(parse_catalog_payload(CATALOG_PAYLOAD, config.CAPABILITY_EMBEDDING)),
			['acme/text-embed-3'])

	def test_image_capability(self):
		self.assertEqual(
			model_ids(parse_catalog_payload(CATALOG_PAYLOAD, config.CAPABILITY_IMAGE)),
			['acme/draw-2'])

	def test_video_capability(self):
		self.assertEqual(
			model_ids(parse_catalog_payload(CATALOG_PAYLOAD, config.CAPABILITY_VIDEO)),
			['acme/motion-1'])

	def test_rerank_capability(self):
		self.assertEqual(
			model_ids(parse_catalog_payload(CATALOG_PAYLOAD, config.CAPABILITY_RERANK)),
			['acme/rank-1'])

	def test_unknown_capability_returns_nothing(self):
		self.assertEqual(filter_models(self.models, 'audio'), [])

	def test_chat_requires_declared_chat_endpoint(self):
		models = [
			{'id': 'no-metadata'},
			{'id': 'only-embedding', 'supported_endpoint_types': ['embeddings']},
			{'id': 'chat-ok', 'supported_endpoint_types': ['openai']},
		]
		self.assertEqual(model_ids(filter_models(models)), ['chat-ok'])

	def test_multimodal_fails_closed_when_undeclared(self):
		models = [
			{'id': 'declared-image', 'supported_endpoint_types': ['openai'],
				'input_modalities': ['text', 'image']},
			{'id': 'undeclared', 'supported_endpoint_types': ['openai'],
				'input_modalities': ['text']},
			{'id': 'no-modalities', 'supported_endpoint_types': ['openai']},
		]
		self.assertEqual(
			model_ids(filter_models(models, config.CAPABILITY_CHAT, ['text', 'image'])),
			['declared-image'])


class TestSeedFallback(unittest.TestCase):
	def test_seed_is_copied_not_shared(self):
		first = seed_catalog()
		first[0]['id'] = 'mutated'
		self.assertNotEqual(seed_catalog()[0]['id'], 'mutated')

	def test_seed_keeps_verified_metadata(self):
		seed = {m['id']: m for m in seed_catalog()}
		gpt = seed['openai/gpt-5.5']
		self.assertEqual(gpt['context_length'], 400000)
		self.assertEqual(gpt['max_completion_tokens'], 128000)
		self.assertIn('image', gpt['input_modalities'])
		self.assertEqual(gpt['reasoning_efforts'], ['low', 'medium', 'high', 'xhigh'])

	def test_auth_error_falls_back_to_seed(self):
		session = FakeSession(FakeResponse(status_code=401))
		result = fetch_chat_catalog('sk-orca-test', session=session)
		self.assertEqual(result.source, 'seed')
		self.assertTrue(result.degraded)
		self.assertIn('API key', result.error)
		self.assertTrue(result.models)

	def test_forbidden_falls_back_to_seed(self):
		session = FakeSession(FakeResponse(status_code=403))
		result = fetch_chat_catalog('sk-orca-test', session=session)
		self.assertEqual(result.source, 'seed')

	def test_server_error_falls_back_to_seed(self):
		session = FakeSession(FakeResponse(status_code=500))
		result = fetch_chat_catalog('sk-orca-test', session=session)
		self.assertEqual(result.source, 'seed')
		self.assertIn('500', result.error)

	def test_network_error_falls_back_to_seed(self):
		session = FakeSession(exc=ConnectionError('boom'))
		result = fetch_chat_catalog('sk-orca-test', session=session)
		self.assertEqual(result.source, 'seed')
		self.assertTrue(result.degraded)

	def test_garbage_payload_falls_back_to_seed(self):
		session = FakeSession(FakeResponse(status_code=200, body=b'not-json'))
		result = fetch_chat_catalog('sk-orca-test', session=session)
		self.assertEqual(result.source, 'seed')

	def test_empty_live_catalog_falls_back_to_seed(self):
		body = b'{"data": []}'
		session = FakeSession(FakeResponse(status_code=200, body=body))
		result = fetch_chat_catalog('sk-orca-test', session=session)
		self.assertEqual(result.source, 'seed')
		self.assertIn('no compatible models', result.error)

	def test_oversized_payload_is_rejected(self):
		body = b'{"data": [' + b' ' * (config.CATALOG_MAX_BYTES + 10) + b']}'
		session = FakeSession(FakeResponse(status_code=200, body=body))
		result = fetch_chat_catalog('sk-orca-test', session=session)
		self.assertEqual(result.source, 'seed')
		self.assertIn('too large', result.error)


class TestLiveCatalog(unittest.TestCase):
	def test_live_catalog_request(self):
		session = FakeSession(FakeResponse(
			status_code=200, body=b'{"data": [{"id": "orcarouter/fusion",'
			b' "supported_endpoint_types": ["openai"]}]}'))
		result = fetch_chat_catalog('sk-orca-test', session=session)
		self.assertEqual(result.source, 'live')
		self.assertEqual(model_ids(result.models), ['orcarouter/fusion'])
		url, kwargs = session.calls[0]
		self.assertEqual(url, f'{config.ORCAROUTER_API_BASE_URL}/models')
		self.assertEqual(kwargs['params']['capability'], 'chat')
		self.assertEqual(kwargs['headers']['Authorization'], 'Bearer sk-orca-test')

	def test_catalog_request_is_bounded(self):
		session = FakeSession(FakeResponse(status_code=200, body=b'{"data": []}'))
		fetch_chat_catalog('sk-orca-test', session=session)
		_, kwargs = session.calls[0]
		self.assertEqual(kwargs['timeout'], config.CATALOG_TIMEOUT)
		self.assertTrue(kwargs['stream'])

	def test_request_without_key_sends_no_authorization(self):
		session = FakeSession(FakeResponse(status_code=200, body=b'{"data": []}'))
		fetch_chat_catalog('', session=session)
		_, kwargs = session.calls[0]
		self.assertNotIn('Authorization', kwargs['headers'])

	@unittest.skipUnless(os.environ.get('ORCAROUTER_API_KEY'), 'ORCAROUTER_API_KEY not set')
	def test_real_catalog_lists_chat_models(self):
		result = fetch_chat_catalog(resolve_api_key())
		self.assertEqual(result.source, 'live', result.error)
		self.assertTrue(result.models)
		for model in result.models:
			self.assertTrue(
				set(model['supported_endpoint_types']) & config.CHAT_ENDPOINT_TYPES,
				f"{model['id']} is not chat capable")


class TestSelectionReconciliation(unittest.TestCase):
	def setUp(self):
		self.models = parse_catalog_payload(CATALOG_PAYLOAD)

	def test_keeps_valid_selection(self):
		self.assertEqual(reconcile_selection('orcarouter/fusion', self.models),
			('orcarouter/fusion', False))

	def test_clears_stale_selection(self):
		self.assertEqual(reconcile_selection('retired/model', self.models), ('', True))

	def test_empty_selection_is_not_a_clear(self):
		self.assertEqual(reconcile_selection('', self.models), ('', False))

	def test_clears_selection_of_non_chat_model(self):
		self.assertEqual(reconcile_selection('acme/text-embed-3', self.models), ('', True))

	def test_default_prefers_orcacyber_zero_when_present(self):
		models = [{'id': 'orcacyber-zero'}, {'id': 'orcarouter/fusion'}]
		self.assertEqual(pick_default_orcarouter_model(models), 'orcacyber-zero')

	def test_default_falls_back_to_fusion(self):
		models = [{'id': 'openai/gpt-5.5'}, {'id': 'orcarouter/fusion'}]
		self.assertEqual(pick_default_orcarouter_model(models), 'orcarouter/fusion')

	def test_default_falls_back_to_first_model(self):
		self.assertEqual(pick_default_orcarouter_model([{'id': 'openai/gpt-5.5'}]), 'openai/gpt-5.5')

	def test_default_of_empty_catalog(self):
		self.assertEqual(pick_default_orcarouter_model([]), '')


class TestCatalogResult(unittest.TestCase):
	def test_degraded_flag(self):
		self.assertTrue(CatalogResult([], 'seed', 'chat', error='x').degraded)
		self.assertFalse(CatalogResult([], 'live', 'chat').degraded)

	def test_as_dict_is_json_safe(self):
		data = CatalogResult([{'id': 'a'}], 'live', 'chat').as_dict()
		self.assertEqual(data['count'], 1)
		self.assertEqual(data['source'], 'live')


class TestKeyHandling(unittest.TestCase):
	def test_mask_never_reveals_full_key(self):
		key = 'sk-orca-abcdefghijklmnopqrstuvwxyz'
		masked = mask_key(key)
		self.assertNotEqual(masked, key)
		self.assertTrue(masked.startswith('sk-orca-'))
		self.assertNotIn('mnopqrst', masked)

	def test_mask_of_empty_key(self):
		self.assertEqual(mask_key(''), '')

	def test_redaction_replaces_keys(self):
		text = 'invalid key sk-orca-abcdef123456 rejected'
		clean = redact(text)
		self.assertNotIn('abcdef123456', clean)
		self.assertIn('sk-orca-…', clean)

	def test_redaction_bounds_length(self):
		self.assertLessEqual(len(redact('x' * 5000)), config.MAX_ERROR_LENGTH)

	def test_stored_key_wins_over_environment(self):
		with mock.patch.dict(os.environ, {'ORCAROUTER_API_KEY': 'sk-orca-env'}):
			self.assertEqual(resolve_api_key('sk-orca-stored'), 'sk-orca-stored')
			self.assertEqual(resolve_api_key(''), 'sk-orca-env')

	def test_no_key_anywhere(self):
		# ``clear=False`` keeps unrelated variables and restores the operator's
		# deployment key when the patch exits.
		with mock.patch.dict(os.environ, {}, clear=False):
			os.environ.pop('ORCAROUTER_API_KEY', None)
			self.assertEqual(resolve_api_key(None), '')

	def test_origins_are_independent(self):
		self.assertEqual(config.ORCAROUTER_API_BASE_URL, 'https://api.orcarouter.ai/v1')
		self.assertEqual(config.ORCAROUTER_AUTH_BASE_URL, 'https://www.orcarouter.ai')

	def test_validate_origin_rejects_plain_http(self):
		with self.assertRaises(ValueError):
			config.validate_origin('http://api.orcarouter.ai/v1')
		self.assertEqual(config.validate_origin('https://api.orcarouter.ai/v1'),
			'https://api.orcarouter.ai/v1')


class TestChatClient(unittest.TestCase):
	def _ok(self, content='hello'):
		return FakeResponse(payload={'choices': [{'message': {'content': content}}]})

	def test_sends_bearer_header_and_model(self):
		session = FakeSession(self._ok())
		content = chat_completion('sk-orca-test', 'orcarouter/fusion',
			[{'role': 'user', 'content': 'hi'}], session=session)
		self.assertEqual(content, 'hello')
		url, kwargs = session.calls[0]
		self.assertEqual(url, f'{config.ORCAROUTER_API_BASE_URL}/chat/completions')
		self.assertEqual(kwargs['headers']['Authorization'], 'Bearer sk-orca-test')
		self.assertEqual(kwargs['json']['model'], 'orcarouter/fusion')

	def test_missing_key_is_reported_without_key_material(self):
		with mock.patch.dict(os.environ, {}, clear=False):
			os.environ.pop('ORCAROUTER_API_KEY', None)
			with self.assertRaises(OrcaRouterError) as ctx:
				chat_completion('', 'orcarouter/fusion', [{'role': 'user', 'content': 'hi'}])
		self.assertIn('API key', str(ctx.exception))

	def test_missing_model(self):
		with self.assertRaises(OrcaRouterError):
			chat_completion('sk-orca-test', '', [{'role': 'user', 'content': 'hi'}])

	def test_unauthorized_is_mapped(self):
		session = FakeSession(FakeResponse(status_code=401))
		with self.assertRaises(OrcaRouterError) as ctx:
			chat_completion('sk-orca-test', 'm', [{'role': 'user', 'content': 'hi'}],
				session=session)
		self.assertIn('API key', str(ctx.exception))
		self.assertNotIn('sk-orca-test', str(ctx.exception))

	def test_forbidden_is_mapped(self):
		session = FakeSession(FakeResponse(status_code=403))
		with self.assertRaises(OrcaRouterError) as ctx:
			chat_completion('sk-orca-test', 'm', [{'role': 'user', 'content': 'hi'}],
				session=session)
		self.assertIn('refused', str(ctx.exception))

	def test_rate_limit_is_mapped(self):
		session = FakeSession(FakeResponse(status_code=429))
		with self.assertRaises(OrcaRouterError) as ctx:
			chat_completion('sk-orca-test', 'm', [{'role': 'user', 'content': 'hi'}],
				session=session)
		self.assertIn('rate limit', str(ctx.exception))

	def test_server_error_includes_redacted_detail(self):
		session = FakeSession(FakeResponse(
			status_code=500,
			payload={'error': {'message': 'boom for sk-orca-secretsecret'}}))
		with self.assertRaises(OrcaRouterError) as ctx:
			chat_completion('sk-orca-test', 'm', [{'role': 'user', 'content': 'hi'}],
				session=session)
		self.assertIn('500', str(ctx.exception))
		self.assertNotIn('secretsecret', str(ctx.exception))

	def test_network_failure_is_mapped(self):
		session = FakeSession(exc=TimeoutError('slow'))
		with self.assertRaises(OrcaRouterError) as ctx:
			chat_completion('sk-orca-test', 'm', [{'role': 'user', 'content': 'hi'}],
				session=session)
		self.assertIn('Unable to reach', str(ctx.exception))

	def test_unexpected_payload_is_mapped(self):
		session = FakeSession(FakeResponse(status_code=200, payload={'nope': True}))
		with self.assertRaises(OrcaRouterError):
			chat_completion('sk-orca-test', 'm', [{'role': 'user', 'content': 'hi'}],
				session=session)

	def test_empty_content_is_mapped(self):
		session = FakeSession(self._ok('  '))
		with self.assertRaises(OrcaRouterError):
			chat_completion('sk-orca-test', 'm', [{'role': 'user', 'content': 'hi'}],
				session=session)

	def test_environment_key_is_used_when_no_stored_key(self):
		previous = os.environ.get('ORCAROUTER_API_KEY')
		os.environ['ORCAROUTER_API_KEY'] = 'sk-orca-envkey'
		try:
			session = FakeSession(self._ok())
			chat_completion('', 'orcarouter/fusion',
				[{'role': 'user', 'content': 'hi'}], session=session)
			_, kwargs = session.calls[0]
			self.assertEqual(kwargs['headers']['Authorization'], 'Bearer sk-orca-envkey')
		finally:
			# Restore the operator's environment instead of deleting it: a
			# deployment key must survive the test run for the live tests.
			if previous is None:
				os.environ.pop('ORCAROUTER_API_KEY', None)
			else:
				os.environ['ORCAROUTER_API_KEY'] = previous


if __name__ == '__main__':
	unittest.main()
