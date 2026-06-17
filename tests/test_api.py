"""
Unit and integration tests for the Sentiment Analysis API.
Run with: pytest tests/ -v
"""
import pickle
import os
import sys
import types
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Provide a lightweight fake model so tests never need the real .pkl file
# ---------------------------------------------------------------------------
class FakeModel:
    def predict(self, texts):
        text = texts[0].lower()
        if any(w in text for w in ("great", "amazing", "love", "excellent", "good")):
            return ["positive"]
        if any(w in text for w in ("bad", "terrible", "hate", "awful", "poor")):
            return ["negative"]
        return ["neutral"]

    def predict_proba(self, texts):
        return [[0.05, 0.90, 0.05]]


@pytest.fixture(autouse=True)
def mock_model(tmp_path):
    """Write a fake pickle and patch MODEL_PATH before importing the app."""
    fake_pkl = tmp_path / "model.pkl"
    with open(fake_pkl, "wb") as f:
        pickle.dump(FakeModel(), f)

    with patch.dict(os.environ, {"MODEL_PATH": str(fake_pkl)}):
        # Force re-import so startup_event uses the patched path
        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        if "main" in sys.modules:
            del sys.modules["main"]

        sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "app")))
        import main as app_module
        app_module.load_model()
        yield app_module


@pytest.fixture
def client(mock_model):
    return TestClient(mock_model.app)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True


# ---------------------------------------------------------------------------
# /predict – happy paths
# ---------------------------------------------------------------------------
class TestPredict:
    def test_positive_review(self, client):
        resp = client.post("/predict", json={"review": "This product is amazing! I love it."})
        assert resp.status_code == 200
        data = resp.json()
        assert data["sentiment"] == "positive"
        assert 0.0 <= data["confidence"] <= 1.0

    def test_negative_review(self, client):
        resp = client.post("/predict", json={"review": "Terrible quality, I hate this product."})
        assert resp.status_code == 200
        assert resp.json()["sentiment"] == "negative"

    def test_neutral_review(self, client):
        resp = client.post("/predict", json={"review": "The package arrived on time."})
        assert resp.status_code == 200
        assert resp.json()["sentiment"] == "neutral"

    def test_confidence_range(self, client):
        resp = client.post("/predict", json={"review": "Great item!"})
        assert 0.0 <= resp.json()["confidence"] <= 1.0

    # Edge cases
    def test_long_review(self, client):
        long_text = "great " * 500
        resp = client.post("/predict", json={"review": long_text})
        assert resp.status_code == 200

    def test_special_characters(self, client):
        resp = client.post("/predict", json={"review": "Amazing!!! 😍 #BestProduct @brand"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /predict – validation errors
# ---------------------------------------------------------------------------
class TestPredictValidation:
    def test_missing_review_field(self, client):
        resp = client.post("/predict", json={})
        assert resp.status_code == 422

    def test_empty_body(self, client):
        resp = client.post("/predict", json=None)
        assert resp.status_code == 422

    def test_wrong_content_type(self, client):
        resp = client.post("/predict", content="plain text", headers={"Content-Type": "text/plain"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /metrics endpoint
# ---------------------------------------------------------------------------
class TestMetrics:
    def test_metrics_endpoint_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_content_type(self, client):
        resp = client.get("/metrics")
        assert "text/plain" in resp.headers["content-type"]

    def test_metrics_contains_expected_keys(self, client):
        # Trigger a prediction so counters are non-zero
        client.post("/predict", json={"review": "Excellent product!"})
        body = client.get("/metrics").text
        assert "api_requests_total" in body
        assert "api_request_latency_seconds" in body
        assert "predictions_by_sentiment_total" in body


# ---------------------------------------------------------------------------
# Integration: counter increments after request
# ---------------------------------------------------------------------------
class TestIntegration:
    def test_request_counter_increments(self, client):
        before = client.get("/metrics").text
        client.post("/predict", json={"review": "Great quality!"})
        after = client.get("/metrics").text
        # The 'positive' label line should have increased
        assert after != before

    def test_model_unloaded_returns_503(self, mock_model, client):
        original = mock_model.model
        mock_model.model = None
        try:
            resp = client.post("/predict", json={"review": "good"})
            assert resp.status_code == 503
        finally:
            mock_model.model = original
