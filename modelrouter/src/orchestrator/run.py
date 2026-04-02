#!/usr/bin/env python3
"""
Quick CLI for Federated Orchestration System
Run individual components or full orchestration
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    if len(sys.argv) < 2:
        print("""
🎛️  FEDERATED ORCHESTRATION SYSTEM

Commands:
  python run.py tunnel status          - Show tunnel status
  python run.py tunnel rotate [country] - Rotate tunnels
  python run.py instance status        - Show instance status  
  python run.py instance create        - Create new instance
  python run.py agg status             - Show aggregator status
  python run.py db analytics           - Show database analytics
  python run.py full init              - Initialize full system
  python run.py full status            - Show full system status
        """)
        return
        
    command = sys.argv[1]
    subcommand = sys.argv[2] if len(sys.argv) > 2 else None
    
    if command == "tunnel":
        from multi_tunnel import get_tunnel_manager
        manager = get_tunnel_manager()
        
        if subcommand == "status":
            print(manager.get_status())
            
        elif subcommand == "rotate":
            country = sys.argv[3] if len(sys.argv) > 3 else None
            if country:
                manager.connect_tunnel(f"tunnel_{country}")
            else:
                manager.rotate_all()
                
    elif command == "instance":
        from instance_manager import get_instance_manager
        manager = get_instance_manager()
        
        if subcommand == "status":
            print(manager.get_all_status())
            
        elif subcommand == "create":
            inst = manager.create_instance(
                name=f"inst-{len(manager.instances)+1}"
            )
            print(f"Created: {inst.instance_id}")
            
    elif command == "agg":
        from token_aggregator import get_aggregator
        agg = get_aggregator()
        
        if subcommand == "status":
            print(agg.get_status())
            
    elif command == "db":
        from database import get_db
        db = get_db()
        
        if subcommand == "analytics":
            print(db.get_analytics())
            
    elif command == "full":
        from master_controller import MasterController, OrchestrationMode
        
        controller = MasterController()
        
        if subcommand == "init":
            controller.initialize(OrchestrationMode.FEDERATED)
            
        elif subcommand == "status":
            print(controller.get_status())


if __name__ == "__main__":
    main()
