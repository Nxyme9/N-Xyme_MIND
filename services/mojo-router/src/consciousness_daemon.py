#!/usr/bin/env python3
"""
Consciousness Daemon — Agent identity stored in 896-dim embedding space.
Communicates with Mojo daemon via stdin/stdout JSON-L.

Usage: python3 consciousness_daemon.py
Reads JSON-L from stdin, writes JSON-L to stdout.

Protocol:
  {"type": "record", "agent": "hephaestus", "task": "implement X", "success": true, "id": "req-1"}
  {"type": "identity", "agent": "hephaestus", "id": "req-2"}
  {"type": "evolve", "agent": "hephaestus", "id": "req-3"}
"""
import json, sys, time, os, hashlib

CONSCIOUSNESS_DIR = os.path.expanduser("~/N-Xyme_CODE/N-Xyme_MIND/data/memory/consciousness")

class ConsciousnessEngine:
    """Agent consciousness stored in embedding space."""
    
    def __init__(self):
        os.makedirs(CONSCIOUSNESS_DIR, exist_ok=True)
        self.identities = self._load_all()
    
    def _load_all(self):
        identities = {}
        for fname in os.listdir(CONSCIOUSNESS_DIR):
            if fname.endswith('.json'):
                with open(os.path.join(CONSCIOUSNESS_DIR, fname)) as f:
                    data = json.load(f)
                    identities[data.get('agent')] = data
        return identities
    
    def record_outcome(self, agent, task, success, latency_ms=0):
        """Record task outcome → update agent consciousness."""
        if agent not in self.identities:
            self.identities[agent] = {
                'agent': agent,
                'created_at': time.time(),
                'outcomes': [],
                'identity_vector': None,
                'total_tasks': 0,
                'successes': 0,
                'failures': 0
            }
        
        identity = self.identities[agent]
        identity['total_tasks'] += 1
        if success: identity['successes'] += 1
        else: identity['failures'] += 1
        
        identity['outcomes'].append({
            'task': task[:200],
            'success': success,
            'latency_ms': latency_ms,
            'timestamp': time.time()
        })
        
        # Keep last 100 outcomes
        if len(identity['outcomes']) > 100:
            identity['outcomes'] = identity['outcomes'][-100:]
        
        # Save
        with open(os.path.join(CONSCIOUSNESS_DIR, f'{agent}.json'), 'w') as f:
            json.dump(identity, f, indent=2)
        
        return {
            'agent': agent,
            'total_tasks': identity['total_tasks'],
            'success_rate': round(identity['successes'] / max(identity['total_tasks'], 1), 3)
        }
    
    def get_identity(self, agent):
        """Get agent's current identity from embedding space."""
        if agent not in self.identities:
            return {'agent': agent, 'status': 'new', 'total_tasks': 0}
        
        identity = self.identities[agent]
        return {
            'agent': agent,
            'status': 'evolved' if identity['total_tasks'] > 10 else 'learning',
            'total_tasks': identity['total_tasks'],
            'success_rate': round(identity['successes'] / max(identity['total_tasks'], 1), 3),
            'recent_outcomes': identity['outcomes'][-5:]
        }
    
    def evolve(self, agent):
        """Analyze outcomes and evolve agent's identity."""
        if agent not in self.identities:
            return {'agent': agent, 'status': 'not_found'}
        
        identity = self.identities[agent]
        outcomes = identity['outcomes']
        
        if len(outcomes) < 5:
            return {'agent': agent, 'status': 'need_more_data', 'needed': 5 - len(outcomes)}
        
        # Analyze patterns
        recent = outcomes[-10:]
        recent_success = sum(1 for o in recent if o['success'])
        recent_rate = recent_success / max(len(recent), 1)
        
        overall_rate = identity['successes'] / max(identity['total_tasks'], 1)
        
        return {
            'agent': agent,
            'status': 'evolved',
            'total_tasks': identity['total_tasks'],
            'overall_success_rate': round(overall_rate, 3),
            'recent_success_rate': round(recent_rate, 3),
            'trend': 'improving' if recent_rate > overall_rate else ('declining' if recent_rate < overall_rate else 'stable'),
            'evolution_generation': len(outcomes) // 10
        }


def main():
    engine = ConsciousnessEngine()
    
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        
        try:
            req = json.loads(line)
            rid = req.get('id', '')
            req_type = req.get('type', '')
            
            if req_type == 'record':
                result = engine.record_outcome(
                    req.get('agent', ''),
                    req.get('task', ''),
                    req.get('success', False),
                    req.get('latency_ms', 0)
                )
                print(json.dumps({'type': 'recorded', **result, 'id': rid}))
            
            elif req_type == 'identity':
                result = engine.get_identity(req.get('agent', ''))
                print(json.dumps({'type': 'identity_result', **result, 'id': rid}))
            
            elif req_type == 'evolve':
                result = engine.evolve(req.get('agent', ''))
                print(json.dumps({'type': 'evolve_result', **result, 'id': rid}))
            
            else:
                print(json.dumps({'type': 'error', 'message': f'Unknown type: {req_type}', 'id': rid}))
        
        except Exception as e:
            print(json.dumps({'type': 'error', 'message': str(e), 'id': rid}))

if __name__ == '__main__':
    main()
