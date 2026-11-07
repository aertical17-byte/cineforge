"""Unified AI provider layer.

Design rules (docs/AI_ENGINE.md):
- Frontend NEVER talks to providers. All provider calls happen in the worker.
- A provider adapter must (a) never fake success, (b) raise ProviderNotConfigured when its key is missing
  so the API can emit an explicit, honest configuration status, (c) validate against public API docs.
- The mock adapter exists ONLY when AI_MOCK_MODE=1 (CI/tests) and is clearly labelled in every response.
"""
