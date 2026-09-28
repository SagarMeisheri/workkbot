"""Model Tier and Resilient Agentgateway LLM Routing (Spec 02, R02.1).

Routes ADK requests to loopback Agentgateway (127.0.0.1:8080/v1) with automated circuit-breaker
failover from Vertex AI gemini-2.0-flash (primary) to gemini-2.0-pro (fallback) upon 429/503.
"""
import time
import logging
from enum import Enum
from typing import Dict, Any, AsyncIterator, Optional, List
import httpx

from src.config import settings

logger = logging.getLogger("workkbot.model_tier")


class ModelTier(str, Enum):
    FLASH = "gemini-3.8-flash"
    PRO = "gemini-3.7-flash"


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, fallback active
    HALF_OPEN = "half_open"  # Testing primary recovery


class ModelRouter:
    """Manages model selection and circuit breaker failover for Agentgateway."""

    def __init__(
        self,
        primary_model: str = settings.DEFAULT_MODEL,
        fallback_model: str = settings.FALLBACK_MODEL,
        gateway_url: str = settings.AGENTGATEWAY_URL,
        recovery_timeout_sec: float = 30.0,
    ):
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.gateway_url = gateway_url.rstrip("/")
        self.recovery_timeout_sec = recovery_timeout_sec

        self._state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self._last_failure_time: float = 0.0
        self._consecutive_failures: int = 0
        self._active_model: str = primary_model

    @property
    def state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.OPEN:
            if time.time() - self._last_failure_time > self.recovery_timeout_sec:
                self._state = CircuitBreakerState.HALF_OPEN
        return self._state

    def get_route_model(self, requested_model: Optional[str] = None) -> str:
        """Determines the active model considering client preference and circuit breaker."""
        if requested_model and requested_model == self.fallback_model:
            return self.fallback_model

        current_state = self.state
        if current_state == CircuitBreakerState.OPEN:
            logger.warning(
                "Circuit breaker is OPEN. Failing over from %s to fallback %s",
                self.primary_model,
                self.fallback_model,
            )
            return self.fallback_model

        return self.primary_model

    def record_failure(self, model: str, status_code: int) -> None:
        """Records a 429 or 5xx failure, tripping the circuit breaker."""
        if status_code in (429, 500, 502, 503, 504):
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            self._state = CircuitBreakerState.OPEN
            self._active_model = self.fallback_model
            logger.error(
                "Circuit breaker tripped to OPEN on status %d for model %s. Fallback %s activated.",
                status_code,
                model,
                self.fallback_model,
            )

    def record_success(self, model: str) -> None:
        """Records a successful response, resetting circuit breaker if half-open."""
        if self._state == CircuitBreakerState.HALF_OPEN and model == self.primary_model:
            self._state = CircuitBreakerState.CLOSED
            self._consecutive_failures = 0
            self._active_model = self.primary_model
            logger.info("Circuit breaker reset to CLOSED for primary %s", self.primary_model)


model_router = ModelRouter()
