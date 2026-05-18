#!/usr/bin/env python3
"""Event Daemon - persistent process, Unix socket, Mojo-routed event push."""
import json, os, time, threading, socket, sys

ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
SOCKET_PATH = "/tmp/nx-event-daemon.sock"

class EventDaemon:
    def __init__(self):
        self.sessions = {}
        self.running = True
        self.embed_bridge = os.path.join(ROOT, "services/mojo-router/src/embed_bridge.py")
        self._lock = threading.Lock()

    def start(self):
        if os.path.exists(SOCKET_PATH): os.unlink(SOCKET_PATH)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH); server.listen(5); server.settimeout(1.0)
        print(f"[event-daemon] Listening on {SOCKET_PATH}")
        while self.running:
            try:
                conn, _ = server.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout: continue
            except Exception as e:
                if self.running: print(f"[event-daemon] Error: {e}")
        server.close()

    def _handle(self, conn):
        try:
            data = conn.recv(65536).decode()
            for line in data.strip().split('\n'):
                if line.strip(): self._process(json.loads(line))
        except: pass
        finally: conn.close()

    def _process(self, event):
        event_type = event.get("type", "")
        session_id = event.get("session_id", "default")
        
        # Handle get_events requests
        if event_type == "get_events":
            events = self.get_events(session_id)
            import sys
            print(json.dumps({"type":"events_result","session_id":session_id,"events":events,"count":len(events)}))
            sys.stdout.flush()
            return
            
        routed = self._route(event)
        with self._lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = []
            self.sessions[session_id].append({"event": event, "routed": routed, "at": time.time()})
            if len(self.sessions[session_id]) > 100:
                self.sessions[session_id] = self.sessions[session_id][-100:]

    def _route(self, event):
        try:
            import subprocess
            text = f"{event.get('source','')} {event.get('agent','')} {event.get('status','')}"
            q = json.dumps({"type": "score", "text": text, "id": "daemon"})
            r = subprocess.run(["python3", self.embed_bridge], input=q,
                capture_output=True, text=True, timeout=5)
            if r.stdout: return json.loads(r.stdout.strip())
        except: pass
        return {"tool": "unknown", "confidence": 0}

    def get_events(self, session_id):
        with self._lock:
            return self.sessions.pop(session_id, [])

    def stop(self): self.running = False

if __name__ == "__main__":
    d = EventDaemon()
    try: d.start()
    except KeyboardInterrupt:
        d.stop()
        if os.path.exists(SOCKET_PATH): os.unlink(SOCKET_PATH)
        print("\n[event-daemon] Stopped")
