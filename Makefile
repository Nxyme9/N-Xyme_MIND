.PHONY: install start stop restart health logs test clean

# Default target
all: install start

# Install dependencies
install:
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "📦 Installing Node dependencies..."
	cd packages/graphiti-memory && npm install
	cd packages/security-agent && npm install
	cd packages/auto-capture && npm install
	@echo "✅ Dependencies installed"

# Start all services
start:
	@echo "🚀 Starting Neo4j..."
	/opt/neo4j/bin/neo4j start
	@echo "🚀 Starting Ollama..."
	systemctl start ollama || true
	@echo "🚀 Starting MCP servers..."
	pm2 resurrect
	@echo "🚀 Starting Fusion Bridge..."
	cd src && python fusion_bridge.py &
	@echo "🚀 Starting Security Agent..."
	cd packages/security-agent && python app/main.py &
	@echo "🚀 Starting Auto-capture..."
	cd packages/auto-capture && python src/server.py &
	@echo "✅ All services started"

# Stop all services
stop:
	@echo "🛑 Stopping MCP servers..."
	pm2 stop all
	@echo "🛑 Stopping Neo4j..."
	/opt/neo4j/bin/neo4j stop
	@echo "🛑 Stopping custom services..."
	pkill -f fusion_bridge.py || true
	pkill -f "security-agent" || true
	pkill -f "auto-capture" || true
	@echo "✅ All services stopped"

# Restart all services
restart: stop start

# Health check
health:
	@echo "🏥 Checking service health..."
	@echo ""
	@echo "=== PM2 Processes ==="
	@pm2 list
	@echo ""
	@echo "=== Neo4j ==="
	@curl -s http://localhost:7474 > /dev/null && echo "✅ Neo4j: Online" || echo "❌ Neo4j: Offline"
	@echo ""
	@echo "=== Ollama ==="
	@curl -s http://localhost:11434/api/tags > /dev/null && echo "✅ Ollama: Online" || echo "❌ Ollama: Offline"
	@echo ""
	@echo "=== Graphiti MCP ==="
	@curl -s http://localhost:8001/health > /dev/null && echo "✅ Graphiti: Online" || echo "❌ Graphiti: Offline"
	@echo ""
	@echo "=== Fusion Bridge ==="
	@curl -s http://localhost:9999/health > /dev/null && echo "✅ Fusion Bridge: Online" || echo "❌ Fusion Bridge: Offline"
	@echo ""
	@echo "=== Security Agent ==="
	@curl -s http://localhost:5002/health > /dev/null && echo "✅ Security Agent: Online" || echo "❌ Security Agent: Offline"
	@echo ""
	@echo "=== Auto-capture ==="
	@curl -s http://localhost:5003/health > /dev/null && echo "✅ Auto-capture: Online" || echo "❌ Auto-capture: Offline"

# View logs
logs:
	@pm2 logs --lines 50

# Run tests
test:
	@echo "🧪 Running tests..."
	pytest tests/ -v

# Clean temporary files
clean:
	@echo "🧹 Cleaning..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned"

# Save PM2 state
save:
	pm2 save

# Show status
status:
	@pm2 list
	@echo ""
	@echo "=== Ports ==="
	@ss -tlnp | grep -E "7474|7687|8001|9999|11434|5002|5003"
