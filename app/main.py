import time
import pickle
import os
import psutil
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
)
from fastapi.responses import Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sentiment Analysis API",
    description="REST API for product review sentiment analysis",
    version="1.0.0"
)

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)
PREDICTION_ERRORS = Counter(
    "prediction_errors_total",
    "Total number of prediction errors"
)
CPU_USAGE = Gauge("system_cpu_usage_percent", "Current CPU usage percentage")
MEMORY_USAGE = Gauge("system_memory_usage_percent", "Current memory usage percentage")
PREDICTIONS_BY_SENTIMENT = Counter(
    "predictions_by_sentiment_total",
    "Number of predictions per sentiment class",
    ["sentiment"]
)

# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
MODEL_PATH = os.getenv("MODEL_PATH", "sentimentanalysismodel.pkl")
model = None


def load_model():
    global model
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        logger.info("Model loaded successfully from %s", MODEL_PATH)
    except FileNotFoundError:
        logger.error("Model file not found at %s", MODEL_PATH)
        raise RuntimeError(f"Model file not found: {MODEL_PATH}")


@app.on_event("startup")
def startup_event():
    load_model()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class ReviewRequest(BaseModel):
    review: str

    model_config = {"json_schema_extra": {"example": {"review": "This product is amazing!"}}}


class PredictionResponse(BaseModel):
    sentiment: str
    confidence: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/predict", response_model=PredictionResponse)
def predict(request: ReviewRequest):
    """Predict the sentiment of a product review."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    start = time.time()
    try:
        text = [request.review]
        prediction = model.predict(text)
        sentiment = str(prediction[0]).lower()

        # Attempt to get confidence probability
        try:
            proba = model.predict_proba(text)
            confidence = float(max(proba[0]))
        except AttributeError:
            confidence = 1.0

        PREDICTIONS_BY_SENTIMENT.labels(sentiment=sentiment).inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="200").inc()
        return PredictionResponse(sentiment=sentiment, confidence=confidence)

    except Exception as exc:
        PREDICTION_ERRORS.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="500").inc()
        logger.exception("Prediction failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(exc)}")
    finally:
        elapsed = time.time() - start
        REQUEST_LATENCY.labels(endpoint="/predict").observe(elapsed)
        CPU_USAGE.set(psutil.cpu_percent())
        MEMORY_USAGE.set(psutil.virtual_memory().percent)


@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics."""
    CPU_USAGE.set(psutil.cpu_percent())
    MEMORY_USAGE.set(psutil.virtual_memory().percent)
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "model_loaded": model is not None}
