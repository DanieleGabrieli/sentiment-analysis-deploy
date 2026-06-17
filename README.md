# Sentiment Analysis — Deploy & Monitoring

Sistema completo di deploy e monitoraggio per un modello di Sentiment Analysis su recensioni di prodotti e-commerce.

## Architettura

```
┌─────────────┐      POST /predict      ┌──────────────────┐
│   Client    │ ──────────────────────► │  FastAPI (8000)  │
└─────────────┘                         │  + Pickle model  │
                                        └────────┬─────────┘
                                                 │ GET /metrics
                                        ┌────────▼─────────┐
                                        │  Prometheus       │
                                        │  (9090)          │
                                        └────────┬─────────┘
                                                 │
                                        ┌────────▼─────────┐
                                        │  Grafana (3000)  │
                                        └──────────────────┘
```

## Struttura del progetto

```
sentiment-analysis-deploy/
├── app/
│   ├── main.py              # FastAPI application
│   └── requirements.txt
├── tests/
│   ├── conftest.py
│   └── test_api.py          # Unit + integration tests
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/prometheus.yml
│       │   └── dashboards/dashboards.yml
│       └── dashboards/sentiment_dashboard.json
├── scripts/
│   └── download_model.sh
├── Dockerfile
├── docker-compose.yml
├── Jenkinsfile
└── README.md
```

---

## Avvio rapido

### Prerequisiti
- Docker ≥ 24 e Docker Compose ≥ 2
- Python 3.11+ (solo per sviluppo locale)

### 1 — Avvio con Docker Compose

```bash
# Clona il repository
git clone <repo-url>
cd sentiment-analysis-deploy

# Avvia tutti i servizi (API + Prometheus + Grafana)
docker compose up --build -d

# Verifica lo stato
docker compose ps
```

| Servizio    | URL                        | Credenziali         |
|-------------|----------------------------|---------------------|
| API         | http://localhost:8000      | —                   |
| Swagger UI  | http://localhost:8000/docs | —                   |
| Prometheus  | http://localhost:9090      | —                   |
| Grafana     | http://localhost:3000      | admin / admin123    |

### 2 — Test dell'API

```bash
# Health check
curl http://localhost:8000/health

# Predizione sentimento
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"review": "This product is amazing! I love it."}'
# → {"sentiment": "positive", "confidence": 0.95}

# Metriche Prometheus
curl http://localhost:8000/metrics
```

### 3 — Sviluppo locale (senza Docker)

```bash
# Crea ambiente virtuale
python3 -m venv venv && source venv/bin/activate

# Installa dipendenze
pip install -r app/requirements.txt pytest httpx

# Scarica il modello
bash scripts/download_model.sh

# Avvia l'API
MODEL_PATH=sentimentanalysismodel.pkl uvicorn app.main:app --reload

# Esegui i test
pytest tests/ -v
```

---

## API Reference

### `POST /predict`

Analizza il sentimento di una recensione.

**Request body:**
```json
{ "review": "This product is amazing! I love it." }
```

**Response:**
```json
{ "sentiment": "positive", "confidence": 0.95 }
```

I valori possibili di `sentiment` sono: `positive`, `negative`, `neutral`.

### `GET /metrics`

Espone le metriche in formato Prometheus. Endpoint consumato automaticamente da Prometheus ogni 10 secondi.

### `GET /health`

Health check per liveness/readiness probe.

---

## Metriche monitorate

| Metrica | Tipo | Descrizione |
|---------|------|-------------|
| `api_requests_total` | Counter | Richieste totali per metodo, endpoint e status |
| `api_request_latency_seconds` | Histogram | Latenza in secondi per endpoint |
| `prediction_errors_total` | Counter | Errori di predizione |
| `predictions_by_sentiment_total` | Counter | Predizioni per classe (positive/negative/neutral) |
| `system_cpu_usage_percent` | Gauge | Utilizzo CPU del processo |
| `system_memory_usage_percent` | Gauge | Utilizzo RAM del processo |

---

## Dashboard Grafana

La dashboard **Sentiment Analysis API** viene caricata automaticamente al primo avvio di Grafana e mostra:

- Tasso di richieste (req/s)
- Latenza P95
- Distribuzione dei sentimenti (pie chart)
- Contatore errori con soglie colorate
- Gauge CPU e Memoria

---

## Pipeline CI/CD (Jenkins)

Il `Jenkinsfile` implementa le seguenti fasi:

```
Checkout → Install deps → Unit tests → Build image → Push registry → Deploy → Smoke test
```

### Configurazione Jenkins

1. Crea un nuovo **Pipeline** job in Jenkins.
2. Imposta *Pipeline definition* su **Pipeline script from SCM** e punta al repository.
3. Configura le seguenti **Credentials** (Jenkins > Manage > Credentials):

| ID | Tipo | Contenuto |
|----|------|-----------|
| `docker-registry-url` | Secret text | URL del registro Docker (es. `registry.example.com`) |
| `docker-registry-creds` | Username/Password | Credenziali del registro |

4. (Opzionale) Installa il plugin **Email Extension** o **Slack Notification** per le notifiche.

### Trigger automatico

Configura un webhook GitHub/GitLab che punta a `http://<jenkins-url>/github-webhook/` per attivare la pipeline ad ogni push sul branch `main`.

---

## Notifiche

La pipeline include sezioni commentate per email e Slack nelle fasi `post { success }` e `post { failure }`. Decommentale dopo aver installato i plugin:

```groovy
// Email Extension Plugin
emailext subject: "...", body: "...", to: "team@example.com"

// Slack Notification Plugin  
slackSend channel: "#deployments", message: "..."
```

---

## Arresto e pulizia

```bash
# Ferma tutti i servizi
docker compose down

# Rimuovi anche i volumi (dati Prometheus + Grafana)
docker compose down -v
```
