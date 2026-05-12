#!/usr/bin/env python3
"""
Test script for N-Xyme Audio Workflow Engine
"""
import sys
sys.path.insert(0, '/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx-audio-workflow')

from workflow_engine import AudioWorkflowEngine
from production_templates import ProductionTemplates
from ai_context import AudioContextSystem

def test_workflow_engine():
    """Test the main workflow engine"""
    print("=" * 60)
    print("Testing Audio Workflow Engine")
    print("=" * 60)
    
    engine = AudioWorkflowEngine()
    
    # Test 1: Parse natural language
    print("\n--- Test 1: Parse 'Start a new track at 140bpm in A minor' ---")
    workflow = engine.parse_natural_language("Start a new track at 140bpm in A minor")
    print(f"Action: {workflow['action']}")
    print(f"Params: {workflow['params']}")
    print(f"OSC Commands: {len(workflow['osc_commands'])} commands")
    for cmd in workflow['osc_commands']:
        print(f"  - {cmd}")
    
    # Test 2: Add reverb
    print("\n--- Test 2: Parse 'Add some reverb to vocals' ---")
    workflow2 = engine.parse_natural_language("Add some reverb to vocals")
    print(f"Action: {workflow2['action']}")
    print(f"OSC Commands: {len(workflow2['osc_commands'])} commands")
    
    # Test 3: Create drum pattern
    print("\n--- Test 3: Parse 'Create a drum pattern' ---")
    workflow3 = engine.parse_natural_language("Create a drum pattern")
    print(f"Action: {workflow3['action']}")
    print(f"OSC Commands: {len(workflow3['osc_commands'])} commands")
    

def test_templates():
    """Test production templates"""
    print("\n" + "=" * 60)
    print("Testing Production Templates")
    print("=" * 60)
    
    templates = ProductionTemplates()
    
    # List available templates
    print("\n--- Available Templates ---")
    for name in templates.list_templates():
        print(f"  - {name}")
    
    # Test recording session template
    print("\n--- Recording Session Template ---")
    rec_session = templates.start_recording_session()
    print(f"Description: {rec_session['description']}")
    print(f"Steps: {len(rec_session['steps'])} steps")
    print(f"Estimated time: {rec_session['estimated_time']}")
    
    # Test beat template
    print("\n--- Beat Template (140 BPM, Trap) ---")
    beat = templates.create_beat_template(bpm=140, style="trap")
    print(f"Description: {beat['description']}")
    print(f"Time Signature: {beat['params']['time_signature']}")
    

def test_context_system():
    """Test AI context system"""
    print("\n" + "=" * 60)
    print("Testing AI Context System")
    print("=" * 60)
    
    context = AudioContextSystem()
    
    # Show initial state
    print("\n--- Initial Project State ---")
    full_context = context.get_full_context()
    print(f"Project: {full_context['project']['name']}")
    print(f"Tempo: {full_context['project']['tempo']} BPM")
    print(f"Key: {full_context['project']['key']}")
    print(f"Tracks: {len(full_context['project']['tracks'])}")
    
    # Update state
    print("\n--- Updating State ---")
    context.update_project_state(name="My First Track", tempo=128, key="G major")
    context.add_track("Drum Machine", "Instrument")
    context.add_track("Vocals", "Audio")
    
    # Show updated state
    print(f"Updated Tempo: {context.state['project']['tempo']} BPM")
    print(f"Updated Tracks: {len(context.state['project']['tracks'])}")
    
    # Get suggestions
    print("\n--- AI Suggestions ---")
    suggestions = context.suggest_next_actions()
    for s in suggestions:
        print(f"  [{s['priority']}] {s['action']}: {s['reason']}")
    
    # Get AI context string
    print("\n--- AI Context String ---")
    ai_context = context.get_context_for_ai()
    print(ai_context)
    

if __name__ == "__main__":
    test_workflow_engine()
    test_templates()
    test_context_system()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
