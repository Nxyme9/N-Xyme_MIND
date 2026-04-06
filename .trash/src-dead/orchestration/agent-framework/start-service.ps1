# Start Agent Framework Service
$env:PYTHONPATH = "."
python -m uvicorn src.service:app --host 0.0.0.0 --port 8002
