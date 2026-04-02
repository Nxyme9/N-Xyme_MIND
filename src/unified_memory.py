import sqlite3
import json
import httpx
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

OPENCODE_DB = "./data/opencode/opencode.db"
GRAPHITI_URL = "http://localhost:8001/json-rpc"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "unified-memory"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/json-rpc':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)
            method = data.get('method')
            params = data.get('params', {})
            
            if method == 'memory_search':
                query = params.get('query', '')
                limit = params.get('limit', 10)
                
                results = []
                
                conn = sqlite3.connect(OPENCODE_DB)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.data, m.time_created 
                    FROM part p 
                    JOIN message m ON p.message_id = m.id 
                    WHERE p.data LIKE ? 
                    ORDER BY m.time_created DESC 
                    LIMIT ?
                """, (f'%{query}%', limit))
                
                for row in cursor.fetchall():
                    data_str, timestamp = row
                    try:
                        content = json.loads(data_str)
                        if content.get('type') == 'text':
                            results.append({
                                'source': 'opencode',
                                'text': content.get('text', ''),
                                'timestamp': timestamp
                            })
                    except:
                        pass
                
                conn.close()
                
                try:
                    graphiti_resp = httpx.post(GRAPHITI_URL, json={
                        "jsonrpc": "2.0",
                        "method": "graphiti_search_nodes",
                        "params": {"query": query, "limit": limit},
                        "id": 1
                    }, timeout=5.0)
                    graphiti_results = graphiti_resp.json().get('result', {}).get('episodes', [])
                    for ep in graphiti_results:
                        results.append({
                            'source': 'graphiti',
                            'text': ep.get('text', ''),
                            'timestamp': ep.get('created', '')
                        })
                except:
                    pass
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"result": results}).encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unknown method"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run():
    server = HTTPServer(('0.0.0.0', 8002), Handler)
    print("Unified memory server running on port 8002")
    server.serve_forever()

if __name__ == '__main__':
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    print("Server started in background")
