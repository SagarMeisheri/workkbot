"""VAL-02.6: Agentgateway Circuit Breaker Failover (R02.1).
Verifies that receiving an HTTP 429 (rate limit) or 503 on primary model (gemini-2.0-flash)
trips the circuit breaker and transparently routes subsequent requests to secondary model (gemini-2.0-pro).
"""
import pytest
from src.agent.model_tier import ModelRouter, CircuitBreakerState


def test_circuit_breaker_failover_on_429():
    """Simulated 429 trips breaker from Flash to Pro."""
    router = ModelRouter(
        primary_model="gemini-2.0-flash",
        fallback_model="gemini-2.0-pro",
        recovery_timeout_sec=1.0,
    )

    # 1. Normal state: primary model
    assert router.state == CircuitBreakerState.CLOSED
    assert router.get_route_model() == "gemini-2.0-flash"

    # 2. Simulate upstream 429 error on Agentgateway
    router.record_failure(model="gemini-2.0-flash", status_code=429)

    # 3. Breaker is now OPEN: all traffic routes to Pro
    assert router.state == CircuitBreakerState.OPEN
    assert router.get_route_model() == "gemini-2.0-pro"

    # 4. Success on fallback keeps pro active or resets upon probe
    router.record_success(model="gemini-2.0-pro")
    assert router.get_route_model() == "gemini-2.0-pro"


def test_client_pro_model_preference():
    """Client explicitly requesting Pro receives Pro without altering breaker state."""
    router = ModelRouter(
        primary_model="gemini-2.0-flash",
        fallback_model="gemini-2.0-pro",
    )
    assert router.get_route_model(requested_model="gemini-2.0-pro") == "gemini-2.0-pro"
    assert router.state == CircuitBreakerState.CLOSED
