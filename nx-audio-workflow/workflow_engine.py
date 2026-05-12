#!/usr/bin/env python3
"""
N-Xyme Audio Workflow Engine
AI-powered music production workflow system using N-Xyme's memory and Bitwig OSC bridge
"""

import yaml
import json
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

# Import N-Xyme memory system
try:
    from nx_brain_memory_search_memories import search_memories
    from nx_brain_memory_memory_write import memory_write
    from nx_brain_context_get_active_context import get_active_context
    NXMEMORY_AVAILABLE = True
except ImportError:
    NXMEMORY_AVAILABLE = False

# Import Bitwig OSC client
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "nx-audio-bridge"))
    from bitwig_client import BitwigClient
    OSC_CLIENT = BitwigClient()
except Exception as e:
    OSC_CLIENT = None
    print(f"[Warning] Bitwig OSC client not available: {e}")
    NXMEMORY_AVAILABLE = False
    print("Warning: N-Xyme memory system not available, using local storage")

class AudioWorkflowEngine:
    """Main AI workflow engine for music production"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.current_project = {
            "tempo": 120,
            "key": "C major",
            "tracks": [],
            "last_modified": None
        }
        self.user_preferences = {
            "default_plugins": ["EQ+", "Compressor+", "Reverb+"],
            "routing_style": "bus-based",
            "favorite_buses": ["Drums", "Vocals", "Instruments"]
        }
        self.osc_bridge_url = self.config.get("bitwig_osc", {}).get("bridge_url", "http://localhost:8000")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            "bitwig_osc": {
                "bridge_url": "http://localhost:8000",
                "enabled": True
            },
            "memory": {
                "enabled": True,
                "store_patterns": True
            },
            "templates": {
                "auto_load": True
            }
        }
    
    def parse_natural_language(self, command: str) -> Dict:
        """Parse natural language command into actionable workflow"""
        command_lower = command.lower()
        
        # Try to extract tempo and key directly
        tempo = None
        key = None
        
        # Extract tempo (e.g., "140bpm", "at 120 bpm")
        tempo_match = re.search(r'(\d+)\s*bpm', command_lower)
        if tempo_match:
            tempo = int(tempo_match.group(1))
        
        # Extract key (e.g., "A minor", "C major")
        key_match = re.search(r'([a-g]#?m?\s*(ajor|inor))', command_lower)
        if key_match:
            key = key_match.group(1)
        
        # Pattern matching for common commands
        if 'track' in command_lower and 'bpm' in command_lower:
            return self._handle_new_track(command, tempo, key)
        elif 'reverb' in command_lower and 'vocal' in command_lower:
            return self._handle_add_reverb(command)
        elif 'drum' in command_lower and 'pattern' in command_lower:
            return self._handle_drum_pattern(command)
        elif 'recording' in command_lower:
            return self._handle_recording_session()
        elif 'mix' in command_lower and 'session' in command_lower:
            return self._handle_mix_session()
        elif 'vocal' in command_lower and 'chain' in command_lower:
            return self._handle_vocal_chain()
        elif 'ableton' in command_lower or ('session' in command_lower and 'style' in command_lower):
            return self._handle_ableton_session_style()
        elif 'modulation' in command_lower or 'lfo' in command_lower:
            return self._handle_modulation_master()
        elif 'remote' in command_lower or 'macro' in command_lower or 'project' in command_lower:
            return self._handle_project_remotes()
        elif 'push' in command_lower or 'launch control' in command_lower or 'pad' in command_lower:
            return self._handle_push_style()
        elif 'hybrid' in command_lower or 'layer' in command_lower:
            return self._handle_hybrid_layering()
        
        # Use AI to interpret if no pattern matches
        return self._ai_interpret_command(command)
    
    def _handle_new_track(self, command: str, tempo: int, key: str) -> Dict:
        """Handle new track creation"""
        bpm = tempo if tempo else 120
        track_key = key if key else "C major"
        
        return {
            "action": "create_track",
            "params": {
                "tempo": bpm,
                "key": track_key,
                "track_name": self._extract_track_name(command),
                "arm": True
            },
            "osc_commands": [
                "/bitwig/track/add AudioTrack",
                f"/bitwig/tempo {bpm}",
                "/bitwig/track/select/last",
                "/bitwig/track/arm 1"
            ]
        }
    
    def _handle_add_reverb(self, command: str) -> Dict:
        """Handle adding reverb to vocals"""
        return {
            "action": "add_reverb",
            "params": {
                "target": "vocals",
                "plugin": "Reverb+",
                "amount": self._extract_amount(command)
            },
            "osc_commands": [
                "/bitwig/track/select/Vocals",
                "/bitwig/device/add Reverb+",
                "/bitwig/device/param/Size 0.5",
                "/bitwig/device/param/Mix 0.3"
            ]
        }
    
    def _handle_drum_pattern(self, command: str) -> Dict:
        """Handle drum pattern creation"""
        return {
            "action": "create_drum_pattern",
            "params": {
                "pattern": "basic_fourfour",
                "bpm": self.current_project["tempo"]
            },
            "osc_commands": [
                "/bitwig/track/add InstrumentTrack",
                "/bitwig/device/add DrumMachine",
                "/bitwig/note/pattern/create 4/4"
            ]
        }
    
    def _handle_recording_session(self, command: str) -> Dict:
        """Handle recording session setup"""
        return {
            "action": "start_recording",
            "params": {
                "input": "Scarlett",
                "track_type": "Audio"
            },
            "osc_commands": [
                "/bitwig/track/add AudioTrack",
                "/bitwig/track/input/select Scarlett",
                "/bitwig/track/arm 1",
                "/bitwig/transport/record"
            ]
        }
    
    def _handle_mix_session(self, command: str) -> Dict:
        """Handle mix session automation"""
        return {
            "action": "mix_session",
            "params": {
                "routing": "bus-based",
                "buses": self.user_preferences["favorite_buses"]
            },
            "osc_commands": [
                "/bitwig/track/add BusTrack Drums",
                "/bitwig/track/add BusTrack Vocals",
                "/bitwig/track/add BusTrack Instruments",
                "/bitwig/track/route/all/to/buses"
            ]
        }
    
    def _handle_vocal_chain(self, command: str) -> Dict:
        """Handle vocal chain creation"""
        return {
            "action": "add_vocal_chain",
            "params": {
                "chain": ["Compressor+", "EQ+", "Reverb+"]
            },
            "osc_commands": [
                "/bitwig/track/select/Vocals",
                "/bitwig/device/add Compressor+",
                "/bitwig/device/add EQ+",
                "/bitwig/device/add Reverb+"
            ]
        }
    
    def _ai_interpret_command(self, command: str) -> Dict:
        """Use AI to interpret complex commands"""
        return {
            "action": "unknown",
            "original_command": command,
            "osc_commands": [],
            "message": f"AI interpretation needed for: {command}"
        }
    
    def _extract_track_name(self, command: str) -> str:
        """Extract track name from command"""
        match = re.search(r'(?:called|named)\s+(\w+)', command, re.IGNORECASE)
        if match:
            return match.group(1)
        return "New Track"
    
    def _extract_amount(self, command: str) -> float:
        """Extract amount/value from command"""
        match = re.search(r'(\d+)%?', command)
        if match:
            return float(match.group(1)) / 100.0
        return 0.5
    
    def _handle_ableton_session_style(self, command: str = "") -> Dict:
        return {
            "action": "ableton_session_style",
            "params": {"colors": True, "scenes": True, "returns": True},
            "osc_commands": [
                "/bitwig/track/add InstrumentTrack Drums",
                "/bitwig/track/color FF6B35",
                "/bitwig/track/add InstrumentTrack Bass",
                "/bitwig/track/color 4ECDC4",
                "/bitwig/track/add InstrumentTrack Synths",
                "/bitwig/track/color C7F464",
                "/bitwig/track/add AudioTrack Vocals",
                "/bitwig/track/color FF6B9D",
                "/bitwig/scene/create Intro",
                "/bitwig/scene/create Verse",
                "/bitwig/scene/create Chorus",
                "/bitwig/track/add ReturnTrack Reverb",
                "/bitwig/track/add ReturnTrack Delay"
            ]
        }
    
    def _handle_modulation_master(self, command: str = "") -> Dict:
        return {
            "action": "modulation_master_chain",
            "params": {"modulators": ["LFO", "Envelope", "Random", "Step"]},
            "osc_commands": [
                "/bitwig/track/select last",
                "/bitwig/device/add Poly Grid",
                "/bitwig/modulator/add LFO",
                "/bitwig/modulator/add ADSR",
                "/bitwig/modulator/add Random",
                "/bitwig/modulator/route LFO->filter cutoff",
                "/bitwig/modulator/route Envelope->osc pitch",
                "/bitwig/modulator/route Random->amp gain"
            ]
        }
    
    def _handle_project_remotes(self, command: str = "") -> Dict:
        return {
            "action": "project_remotes_controller",
            "params": {"pages": 4, "controls": ["Master", "Tempo", "Reverb", "Delay"]},
            "osc_commands": [
                "/bitwig/project/remote/page/create Master",
                "/bitwig/project/remote/add Master Volume -> /bitwig/track/master/volume",
                "/bitwig/project/remote/add Tempo -> /bitwig/transport/tempo",
                "/bitwig/project/remote/add Reverb Send -> /bitwig/track/return/Reverb/send",
                "/bitwig/project/remote/add Delay Send -> /bitwig/track/return/Delay/send"
            ]
        }
    
    def _handle_push_style(self, command: str = "") -> Dict:
        return {
            "action": "push_style_workflow",
            "params": {"controller": "Launch Control", "drums": True},
            "osc_commands": [
                "/bitwig/track/add InstrumentTrack Drums",
                "/bitwig/device/add DrumMachine",
                "/bitwig/device/mode step",
                "/bitwig/device/steps 16",
                "/bitwig/device/remote/add Filter -> filter cutoff",
                "/bitwig/device/remote/add Resonance -> filter resonance",
                "/bitwig/device/scale minor C 4th"
            ]
        }
    
    def _handle_hybrid_layering(self, command: str = "") -> Dict:
        return {
            "action": "hybrid_track_layering",
            "params": {"tracks": ["Synth Stack", "Live Jam"]},
            "osc_commands": [
                "/bitwig/track/add HybridTrack Synth Stack",
                "/bitwig/device/add Poly Grid",
                "/bitwig/device/add FX Layer Clean",
                "/bitwig/device/add FX Layer Processed",
                "/bitwig/track/add HybridTrack Live Jam"
            ]
        }
    
    def execute_workflow(self, workflow: Dict) -> Dict:
        """Execute a workflow by sending OSC commands to Bitwig bridge"""
        results = []
        
        for cmd in workflow.get("osc_commands", []):
            result = self._send_osc_command(cmd)
            results.append(result)
        
        # Store workflow pattern in memory
        if NXMEMORY_AVAILABLE and self.config.get("memory", {}).get("enabled"):
            memory_write(
                content=json.dumps(workflow),
                kind="procedural",
                scope="session",
                tags=["audio", "workflow", workflow.get("action", "unknown")]
            )
        
        # Update current project state
        self._update_project_state(workflow)
        
        return {
            "success": True,
            "commands_sent": len(results),
            "results": results
        }
    
    def _send_osc_command(self, command: str) -> Dict:
        """Send OSC command via Bitwig bridge"""
        if OSC_CLIENT:
            try:
                OSC_CLIENT.send_message(command, [])
                print(f"[OSC] {command}")
                return {"command": command, "status": "sent"}
            except Exception as e:
                print(f"[OSC Error] {e}")
                return {"command": command, "status": "error", "error": str(e)}
        print(f"[OSC] {command}")
        return {"command": command, "status": "queued"}
    
    def _update_project_state(self, workflow: Dict):
        """Update current project state based on workflow"""
        action = workflow.get("action")
        params = workflow.get("params", {})
        
        if action == "create_track":
            self.current_project["tempo"] = params.get("tempo", 120)
            self.current_project["key"] = params.get("key", "C major")
            self.current_project["tracks"].append(params.get("track_name", "New Track"))
        elif action == "start_recording":
            self.current_project["last_modified"] = datetime.now().isoformat()
        
    def get_context(self) -> Dict:
        """Get current project context"""
        if NXMEMORY_AVAILABLE:
            try:
                context = get_active_context()
                return context
            except:
                pass
        return {
            "project": self.current_project,
            "preferences": self.user_preferences
        }
    
    def suggest_next_action(self) -> List[str]:
        """Suggest next actions based on history"""
        suggestions = []
        
        if not self.current_project["tracks"]:
            suggestions.append("Start a new recording session")
        elif len(self.current_project["tracks"]) < 3:
            suggestions.append("Add more tracks to build your arrangement")
        suggestions.append("Try: 'Add some reverb to vocals'")
        suggestions.append("Try: 'Create a drum pattern'")
        
        return suggestions

def main():
    """CLI interface for the workflow engine"""
    import sys
    
    engine = AudioWorkflowEngine()
    
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        print(f"Processing: {command}")
        workflow = engine.parse_natural_language(command)
        result = engine.execute_workflow(workflow)
        print(f"Result: {json.dumps(result, indent=2)}")
    else:
        print("═══════════════════════════════════════════════════════")
        print("  N-Xyme Audio Workflow Engine (Interactive Mode)")
        print("═══════════════════════════════════════════════════════")
        print("Type commands below. Examples:")
        print("  • create ableton session style template")
        print("  • create push style workflow")
        print("  • create hybrid track layering")
        print("  • create modulation master chain")
        print("  • add some reverb to vocals")
        print("  • create a drum pattern at 140bpm")
        print("\nType 'quit' or 'exit' to stop.\n")
        
        while True:
            try:
                command = input("> ").strip()
                if command.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                if not command:
                    continue
                workflow = engine.parse_natural_language(command)
                result = engine.execute_workflow(workflow)
                print(f"  → {workflow.get('action', 'done')}")
                if result.get('osc_commands'):
                    for cmd in result.get('osc_commands', []):
                        print(f"    {cmd}")
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

if __name__ == "__main__":
    main()
