#!/usr/bin/env python3
"""CLI Monitoring Dashboard

Provides real-time visibility into system behavior with:
- Agent performance metrics
- Routing decision tracking
- Error rate monitoring
- System health indicators
- Message queue status
- Task decomposition stats
"""

import json
import time
import sqlite3
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("monitoring-dashboard")


class MonitoringDashboard:
    """CLI-based monitoring dashboard for the N-Xyme_MIND system."""
    
    def __init__(self):
        self.db_path = Path(".sisyphus/routing.db")
        self.msg_db_path = Path(".sisyphus/messages.db")
        self.outcomes_path = Path(".sisyphus/outcomes.jsonl")
        self.triggers_path = Path(".sisyphus/routing-triggers.json")
    
    def clear_screen(self):
        """Clear terminal screen."""
        shutil.get_terminal_size()
        print("\033[H\033[J", end="")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        health = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'components': {},
            'overall_status': 'healthy'
        }
        
        # Check database
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(str(self.db_path))
                outcomes_count = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
                agents_count = conn.execute("SELECT COUNT(*) FROM agent_weights").fetchone()[0]
                triggers_count = conn.execute("SELECT COUNT(*) FROM triggers").fetchone()[0]
                conn.close()
                
                health['components']['database'] = {
                    'status': 'healthy',
                    'outcomes': outcomes_count,
                    'agents': agents_count,
                    'triggers': triggers_count
                }
            except Exception as e:
                health['components']['database'] = {'status': 'error', 'error': str(e)}
                health['overall_status'] = 'degraded'
        else:
            health['components']['database'] = {'status': 'missing'}
            health['overall_status'] = 'critical'
        
        # Check message queue
        if self.msg_db_path.exists():
            try:
                conn = sqlite3.connect(str(self.msg_db_path))
                messages_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
                pending_count = conn.execute("SELECT COUNT(*) FROM messages WHERE status='pending'").fetchone()[0]
                conn.close()
                
                health['components']['message_queue'] = {
                    'status': 'healthy',
                    'total_messages': messages_count,
                    'pending_messages': pending_count
                }
            except Exception as e:
                health['components']['message_queue'] = {'status': 'error', 'error': str(e)}
                health['overall_status'] = 'degraded'
        else:
            health['components']['message_queue'] = {'status': 'missing'}
        
        # Check outcomes file
        if self.outcomes_path.exists():
            try:
                with open(self.outcomes_path) as f:
                    outcomes = [json.loads(line) for line in f if line.strip()]
                
                recent = outcomes[-100:] if len(outcomes) > 100 else outcomes
                success_rate = sum(1 for o in recent if o.get('success')) / len(recent) if recent else 0
                
                health['components']['outcomes'] = {
                    'status': 'healthy',
                    'total_outcomes': len(outcomes),
                    'recent_success_rate': f"{success_rate:.0%}"
                }
            except Exception as e:
                health['components']['outcomes'] = {'status': 'error', 'error': str(e)}
                health['overall_status'] = 'degraded'
        else:
            health['components']['outcomes'] = {'status': 'missing'}
        
        return health
    
    def get_agent_performance(self) -> List[Dict[str, Any]]:
        """Get agent performance metrics."""
        if not self.db_path.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            rows = conn.execute("""
                SELECT agent, success_rate, avg_latency_ms, total_tasks, success_count, failure_count
                FROM agent_weights
                ORDER BY total_tasks DESC
            """).fetchall()
            conn.close()
            
            agents = []
            for row in rows:
                agents.append({
                    'agent': row[0],
                    'success_rate': row[1],
                    'avg_latency_ms': row[2],
                    'total_tasks': row[3],
                    'success_count': row[4],
                    'failure_count': row[5]
                })
            
            return agents
        except Exception as e:
            logger.error(f"Error getting agent performance: {e}")
            return []
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent system activity."""
        if not self.outcomes_path.exists():
            return []
        
        try:
            with open(self.outcomes_path) as f:
                outcomes = [json.loads(line) for line in f if line.strip()]
            
            recent = outcomes[-limit:] if len(outcomes) > limit else outcomes
            return recent
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []
    
    def get_message_queue_stats(self) -> Dict[str, Any]:
        """Get message queue statistics."""
        if not self.msg_db_path.exists():
            return {'status': 'missing'}
        
        try:
            conn = sqlite3.connect(str(self.msg_db_path))
            stats = {}
            
            stats['total'] = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            
            status_counts = conn.execute("""
                SELECT status, COUNT(*) as count FROM messages GROUP BY status
            """).fetchall()
            stats['by_status'] = {row[0]: row[1] for row in status_counts}
            
            type_counts = conn.execute("""
                SELECT type, COUNT(*) as count FROM messages GROUP BY type
            """).fetchall()
            stats['by_type'] = {row[0]: row[1] for row in type_counts}
            
            conn.close()
            return stats
        except Exception as e:
            logger.error(f"Error getting message queue stats: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def display_dashboard(self):
        """Display the full monitoring dashboard."""
        self.clear_screen()
        
        # Header
        print("=" * 80)
        print("  N-Xyme_MIND MONITORING DASHBOARD")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # System Health
        health = self.get_system_health()
        print(f"\n📊 SYSTEM HEALTH: {health['overall_status'].upper()}")
        print("-" * 40)
        
        for component, data in health['components'].items():
            status = data.get('status', 'unknown')
            status_icon = "✅" if status == 'healthy' else "⚠️" if status == 'degraded' else "❌"
            print(f"  {status_icon} {component}: {status}")
            for key, value in data.items():
                if key != 'status' and key != 'error':
                    print(f"     - {key}: {value}")
        
        # Agent Performance
        agents = self.get_agent_performance()
        if agents:
            print(f"\n🤖 AGENT PERFORMANCE")
            print("-" * 40)
            print(f"  {'Agent':20s} {'Success':>8s} {'Tasks':>6s} {'Latency':>10s}")
            print(f"  {'-'*20} {'-'*8} {'-'*6} {'-'*10}")
            
            for agent in agents:
                print(f"  {agent['agent']:20s} {agent['success_rate']:7.0%} {agent['total_tasks']:6d} {agent['avg_latency_ms']:9.1f}ms")
        
        # Message Queue
        mq_stats = self.get_message_queue_stats()
        if mq_stats.get('status') != 'missing':
            print(f"\n📨 MESSAGE QUEUE")
            print("-" * 40)
            print(f"  Total messages: {mq_stats.get('total', 0)}")
            print(f"  By status: {mq_stats.get('by_status', {})}")
            print(f"  By type: {mq_stats.get('by_type', {})}")
        
        # Recent Activity
        recent = self.get_recent_activity(5)
        if recent:
            print(f"\n📋 RECENT ACTIVITY (last 5)")
            print("-" * 40)
            for outcome in recent:
                status = "✅" if outcome.get('success') else "❌"
                task_id = outcome.get('task_id', '?')[-12:]
                desc = outcome.get('task_description', '?')[:40]
                agent = outcome.get('agent', '?')
                print(f"  {status} {task_id}: {desc} → {agent}")
        
        print(f"\n{'=' * 80}")
        print("  Dashboard refreshes every 5 seconds. Press Ctrl+C to exit.")
        print(f"{'=' * 80}")


def main():
    """Main dashboard loop."""
    dashboard = MonitoringDashboard()
    
    try:
        while True:
            dashboard.display_dashboard()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")


if __name__ == "__main__":
    main()
