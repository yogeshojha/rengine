"""Live checks against the real OrcaRouter gateway.

These are the only tests that touch the network. They run through the very
provider code the application uses (``orcarouter.catalog`` and
``orcarouter.client``) and are skipped unless ``ORCAROUTER_API_KEY`` is set.

The workspace used for verification cannot call every catalog model: models
that require business verification (including the recommended OrcaCyber Zero)
answer 403. The chat test therefore walks the catalog in order and requires
at least one model from the live catalog to answer, which proves the wiring
without pretending a restricted model is available.

No key material is printed, logged or embedded in assertion messages.
"""

import os
import time
import unittest

from orcarouter import config
from orcarouter.catalog import (
	model_ids,
	fetch_chat_catalog,
	pick_default_orcarouter_model,
)
from orcarouter.client import OrcaRouterError, chat_completion, resolve_api_key

# The key is resolved from the environment inside each test and never stored
# in a module attribute, so it cannot leak through a test report.
SKIP_REASON = 'ORCAROUTER_API_KEY is not set'
# Bounded: a refusal is answered immediately, but a hung model must not make
# the check exceed its time budget, so attempts are capped and the whole walk
# stops at a wall-clock deadline.
MAX_CHAT_ATTEMPTS = 24
LIVE_CHAT_TIMEOUT = 30
LIVE_CHAT_BUDGET = 240


@unittest.skipUnless(os.environ.get('ORCAROUTER_API_KEY'), SKIP_REASON)
class TestLiveOrcaRouterProvider(unittest.TestCase):
	def test_live_catalog_is_used(self):
		result = fetch_chat_catalog(resolve_api_key())
		self.assertEqual(result.source, 'live', result.error)
		self.assertTrue(result.models, 'live catalog returned no chat models')
		ids = model_ids(result.models)
		self.assertEqual(len(ids), len(set(ids)))
		for model in result.models:
			self.assertTrue(
				set(model['supported_endpoint_types']) & config.CHAT_ENDPOINT_TYPES,
				'model without a chat-capable endpoint was offered')
			# Ids are used verbatim: the catalog may serve plain ids as well as
			# vendor/model namespaced ones, and neither may be rewritten.
			self.assertEqual(model['id'], model['id'].strip())
			self.assertNotIn(' ', model['id'])
		self.assertEqual(
			pick_default_orcarouter_model(result.models),
			config.ORCAROUTER_DEFAULT_MODEL
			if config.ORCAROUTER_DEFAULT_MODEL in ids
			else config.ORCAROUTER_FALLBACK_MODEL
			if config.ORCAROUTER_FALLBACK_MODEL in ids
			else ids[0])

	def test_chat_completion_through_provider(self):
		catalog = fetch_chat_catalog(resolve_api_key())
		self.assertEqual(catalog.source, 'live', catalog.error)
		preferred = os.environ.get('ORCAROUTER_LIVE_MODEL')
		ids = model_ids(catalog.models)
		ordered = ([preferred] if preferred in ids else []) + [
			model_id for model_id in ids if model_id != preferred]
		attempts = 0
		refused = []
		deadline = time.monotonic() + LIVE_CHAT_BUDGET
		for model_id in ordered[:MAX_CHAT_ATTEMPTS]:
			if time.monotonic() > deadline:
				break
			attempts += 1
			try:
				content = chat_completion(
					resolve_api_key(),
					model_id,
					[{'role': 'user', 'content': 'Reply with the single word OK.'}],
					timeout=LIVE_CHAT_TIMEOUT,
				)
			except OrcaRouterError as exc:
				message = str(exc)
				if 'rejected the API key' in message:
					# A 401 means the credential is unusable: trying more models
					# cannot help and would only hide the real problem.
					self.fail(f'provider rejected the configured key: {message}')
				refused.append(model_id)
				continue
			self.assertTrue(content.strip())
			self.assertNotIn(resolve_api_key(), content)
			return
		self.fail(
			f'no catalog model answered after {attempts} attempts; '
			f'refused models: {", ".join(refused) or "none"}')


if __name__ == '__main__':
	unittest.main()
