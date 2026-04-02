# N-XYME Security Agent

FastAPI service for command validation and security analysis.

## Endpoints

- `GET /health` - Health check
- `POST /analyze` - Analyze command security
- `POST /feedback` - Submit user feedback

## Run

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 5002
```

## Docker

```bash
docker build -t security-agent .
docker run -p 5002:5002 security-agent
```

## Environment Variables

- `OLLAMA_BASE_URL` - Ollama endpoint (default: http://localhost:11434)
- `OLLAMA_SECURITY_MODEL` - Model for analysis (default: phi3:mini)
- `OLLAMA_TIMEOUT` - Request timeout (default: 10s)
