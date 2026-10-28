from __future__ import annotations

import re
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
ANSWERS = ROOT / "answers.md"


class FakeOAuthInvalidGrant(Exception):
    pass


class FakeCacheUnavailable(Exception):
    pass


def extract_block(function_name: str) -> str:
    text = ANSWERS.read_text(encoding="utf-8")
    blocks = re.findall(r"```python\s*\n(.*?)```", text, flags=re.DOTALL)
    matches = [block for block in blocks if f"def {function_name}(" in block]
    assert len(matches) == 1, f"expected one block for {function_name}"
    return matches[0]


class FakeTokenStore:
    def __init__(self, *, commit_result=True, mark_result=True):
        self.commit_result = commit_result
        self.mark_result = mark_result
        self.commits = []

    def acquire_refresh_lease(self, tenant_id):
        assert tenant_id == "tenant-1"
        return nullcontext()

    def load_encrypted(self, tenant_id):
        assert tenant_id == "tenant-1"
        return SimpleNamespace(
            id=tenant_id,
            connection_state="CONNECTED",
            token_version=7,
        )

    def commit_atomic(self, tenant_id, **values):
        self.commits.append((tenant_id, values))
        return self.commit_result

    def mark_reauth_required(self, tenant_id, *, expected_version):
        assert (tenant_id, expected_version) == ("tenant-1", 7)
        return self.mark_result


class FakeCache:
    def __init__(self, *, put_error=None):
        self.put_error = put_error
        self.put_calls = []
        self.delete_calls = []

    def put(self, tenant_id, access_token, *, ttl_seconds):
        self.put_calls.append((tenant_id, access_token, ttl_seconds))
        if self.put_error is not None:
            raise self.put_error

    def delete_best_effort(self, tenant_id):
        self.delete_calls.append(tenant_id)


def build_refresh_runtime(*, token_store, cache, xero_refresh=None):
    def default_refresh(_refresh_token):
        return {"ok": True}

    namespace = {
        "OAuthInvalidGrant": FakeOAuthInvalidGrant,
        "CacheUnavailable": FakeCacheUnavailable,
        "token_store": token_store,
        "access_token_cache": cache,
        "xero_refresh": xero_refresh or default_refresh,
        "decrypt_tokens": lambda current: SimpleNamespace(
            refresh_token="old-refresh-token"
        ),
        "validate_token_response": lambda response: SimpleNamespace(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            access_token_expires_at="2026-10-27T01:00:00Z",
            refresh_token_expires_at="2026-12-26T00:30:00Z",
            access_token_ttl_seconds=1800,
        ),
        "encrypt_for_tenant": lambda tenant_id, value: f"encrypted:{tenant_id}:{value}",
        "key_manager": SimpleNamespace(active_version=lambda: 3),
    }
    exec(extract_block("refresh_tokens_safely"), namespace)  # noqa: S102
    return namespace["refresh_tokens_safely"]


def test_lost_optimistic_lock_does_not_publish_cache():
    token_store = FakeTokenStore(commit_result=False)
    cache = FakeCache()
    refresh_tokens_safely = build_refresh_runtime(
        token_store=token_store,
        cache=cache,
    )

    result = refresh_tokens_safely(SimpleNamespace(id="tenant-1"))

    assert result == "RETRY_WITH_LATEST"
    assert cache.put_calls == []


def test_stale_invalid_grant_does_not_force_reauthorisation():
    token_store = FakeTokenStore(mark_result=False)
    cache = FakeCache()

    def raise_invalid_grant(_refresh_token):
        raise FakeOAuthInvalidGrant()

    refresh_tokens_safely = build_refresh_runtime(
        token_store=token_store,
        cache=cache,
        xero_refresh=raise_invalid_grant,
    )

    result = refresh_tokens_safely(SimpleNamespace(id="tenant-1"))

    assert result == "RETRY_WITH_LATEST"


def test_cache_failure_after_commit_does_not_trigger_second_token_rotation():
    token_store = FakeTokenStore(commit_result=True)
    cache = FakeCache(put_error=FakeCacheUnavailable())
    refresh_tokens_safely = build_refresh_runtime(
        token_store=token_store,
        cache=cache,
    )

    result = refresh_tokens_safely(SimpleNamespace(id="tenant-1"))

    assert result == "REFRESHED"
    assert cache.delete_calls == ["tenant-1"]


class FakeLogger:
    def __init__(self):
        self.events = []

    def structured(self, name, **fields):
        self.events.append((name, fields))


class FakeMetrics:
    def __init__(self):
        self.increments = []
        self.gauges = []

    def increment(self, name, *, labels):
        self.increments.append((name, labels))

    def gauge(self, name, value, *, labels):
        self.gauges.append((name, value, labels))


class FakeAlerts:
    def raise_incident(self, **_values):
        return None


def build_observation_function():
    namespace = {
        "ALLOWED_LOG_FIELDS": {
            "tenant_id",
            "endpoint",
            "status",
            "error_code",
            "correlation_id",
        },
        "FORBIDDEN_FIELDS": set(),
        "logger": FakeLogger(),
        "metrics": FakeMetrics(),
        "alerts": FakeAlerts(),
        "normalise_endpoint": lambda value: "/api.xro/2.0/Invoices",
        "normalise_error_code": lambda value: value or "none",
    }
    exec(extract_block("write_api_observation"), namespace)  # noqa: S102
    return namespace["write_api_observation"], namespace


def observation_event(**overrides):
    values = {
        "fields": {
            "tenant_id": "tenant-1",
            "endpoint": "https://api.xero.com/api.xro/2.0/Invoices?token=secret",
        },
        "environment": "test",
        "endpoint": "https://api.xero.com/api.xro/2.0/Invoices?token=secret",
        "status": None,
        "error_code": None,
        "cursor_age_seconds": 12,
        "correlation_id": "corr-1",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_null_status_is_classified_without_crashing():
    write_api_observation, runtime = build_observation_function()

    write_api_observation(observation_event())

    labels = runtime["metrics"].increments[0][1]
    assert labels["status_class"] == "network_error"


def test_cursor_age_metric_does_not_use_tenant_id_label():
    write_api_observation, runtime = build_observation_function()

    write_api_observation(observation_event(status=200))

    _, _, labels = runtime["metrics"].gauges[0]
    assert "tenant_id" not in labels


def test_endpoint_is_sanitised_before_logging():
    write_api_observation, runtime = build_observation_function()

    write_api_observation(observation_event(status=200))

    _, fields = runtime["logger"].events[0]
    assert fields["endpoint"] == "/api.xro/2.0/Invoices"
    assert "secret" not in fields["endpoint"]


class FakeSecretStore:
    def __init__(self):
        self.active_ref = "old-secret-ref"
        self.staged = []
        self.activations = []
        self.retired = []
        self.discarded = []

    def acquire_rotation_lock(self, app_id):
        assert app_id == "app-1"
        return nullcontext()

    def get_active_reference(self, app_id):
        assert app_id == "app-1"
        return self.active_ref

    def stage(self, app_id, secret_ref):
        self.staged.append(secret_ref)

    def activate(self, app_id, secret_ref):
        self.activations.append(secret_ref)
        self.active_ref = secret_ref

    def retire(self, app_id, secret_ref):
        self.retired.append(secret_ref)

    def discard_staged(self, app_id, secret_ref):
        self.discarded.append(secret_ref)


def build_rotate_function(*, health_error=None):
    secret_store = FakeSecretStore()
    incidents = []

    def verify_authentication_healthy(_app_id):
        if health_error is not None:
            raise health_error

    namespace = {
        "secret_store": secret_store,
        "verify_token_refresh_with_secret": lambda *_args: None,
        "verify_authentication_healthy": verify_authentication_healthy,
        "alert_if_authentication_errors_spike": verify_authentication_healthy,
        "alerts": SimpleNamespace(
            raise_incident=lambda **values: incidents.append(values)
        ),
    }
    exec(extract_block("rotate_client_secret"), namespace)  # noqa: S102
    return namespace["rotate_client_secret"], secret_store, incidents


def test_overlap_rotation_requires_explicit_confirmation():
    rotate_client_secret, secret_store, _ = build_rotate_function()

    with pytest.raises(ValueError, match="overlap"):
        rotate_client_secret("app-1", "new-secret-ref", overlap_supported=False)

    assert secret_store.staged == []


def test_failed_health_check_rolls_back_to_previous_secret():
    health_error = type("AuthenticationHealthError", (Exception,), {})
    rotate_client_secret, secret_store, incidents = build_rotate_function(
        health_error=health_error()
    )

    with pytest.raises(health_error):
        rotate_client_secret("app-1", "new-secret-ref", overlap_supported=True)

    assert secret_store.active_ref == "old-secret-ref"
    assert secret_store.retired == []
    assert secret_store.discarded == ["new-secret-ref"]
    assert len(incidents) == 1
