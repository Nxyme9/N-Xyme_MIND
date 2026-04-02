@echo off
echo === N-Xyme Catalyst System Test ===
echo.

echo Testing Graphiti Memory...
curl -s http://localhost:8001/health
echo.

echo Testing Ollama AI...
curl -s http://localhost:11434/api/tags | python -c "import json,sys; d=json.load(sys.stdin); print(f'  Models: {len(d[\"models\"])}')"
echo.

echo Testing Jarvis API...
curl -s http://localhost:8088/health
echo.

echo Testing Jarvis Status...
curl -s -H "Authorization: Bearer h1_2qaF6NEK1XjNCNho1ToJvdmL5eRMJNEluKGOMBxg" http://localhost:8088/status | python -c "import json,sys; d=json.load(sys.stdin); print(f'  Mode: {d[\"mode\"]}, Model: {d[\"model\"]}, CPU: {d[\"cpu_percent\"]}%%')"
echo.

echo Testing Command API...
curl -s -X POST -H "Authorization: Bearer h1_2qaF6NEK1XjNCNho1ToJvdmL5eRMJNEluKGOMBxg" -H "Content-Type: application/json" -d "{\"message\":\"Hello from test\"}" http://localhost:8088/command
echo.

echo === ALL TESTS COMPLETE ===
