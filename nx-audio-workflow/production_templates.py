#!/usr/bin/env python3
"""
Production Templates for N-Xyme Audio Workflow
Pre-built workflow templates for common music production tasks
"""

from typing import Dict, List, Optional
import random

class ProductionTemplates:
    """Pre-built workflow templates for music production"""
    
    @staticmethod
    def start_recording_session() -> Dict:
        """Set up Scarlett interface + create track + arm"""
        return {
            "action": "start_recording_session",
            "description": "Initialize recording session with Scarlett audio interface",
            "steps": [
                {
                    "step": 1,
                    "action": "configure_audio_interface",
                    "params": {
                        "interface": "Scarlett",
                        "inputs": ["Input 1", "Input 2"],
                        "sample_rate": 44100,
                        "bit_depth": 24
                    },
                    "osc_commands": [
                        "/bitwig/audio/interface Scarlett",
                        "/bitwig/audio/samplerate 44100",
                        "/bitwig/audio/bitdepth 24"
                    ]
                },
                {
                    "step": 2,
                    "action": "create_audio_track",
                    "params": {
                        "name": "Audio 1",
                        "track_type": "Audio",
                        "input_source": "Scarlett Input 1"
                    },
                    "osc_commands": [
                        "/bitwig/track/add AudioTrack",
                        "/bitwig/track/name Audio 1",
                        "/bitwig/track/input/select Scarlett Input 1"
                    ]
                },
                {
                    "step": 3,
                    "action": "arm_track",
                    "params": {
                        "track": "Audio 1",
                        "monitor": "on",
                        "record_enable": True
                    },
                    "osc_commands": [
                        "/bitwig/track/select/Audio 1",
                        "/bitwig/track/arm 1",
                        "/bitwig/track/monitor on"
                    ]
                }
            ],
            "estimated_time": "30 seconds"
        }
    
    @staticmethod
    def mix_session() -> Dict:
        """Auto-route tracks to buses for mixing"""
        return {
            "action": "mix_session",
            "description": "Automatically route tracks to appropriate buses",
            "steps": [
                {
                    "step": 1,
                    "action": "create_buses",
                    "params": {
                        "buses": ["Drums", "Vocals", "Instruments", "Master"]
                    },
                    "osc_commands": [
                        "/bitwig/track/add BusTrack Drums",
                        "/bitwig/track/add BusTrack Vocals",
                        "/bitwig/track/add BusTrack Instruments"
                    ]
                },
                {
                    "step": 2,
                    "action": "route_drum_tracks",
                    "params": {
                        "pattern": "Drum*|Kick|Snare|HiHat|*Perc*",
                        "target_bus": "Drums"
                    },
                    "osc_commands": [
                        "/bitwig/track/select/pattern Drum*",
                        "/bitwig/track/route/to Drums"
                    ]
                },
                {
                    "step": 3,
                    "action": "route_vocal_tracks",
                    "params": {
                        "pattern": "Vocal*|Voice|*Vox*",
                        "target_bus": "Vocals"
                    },
                    "osc_commands": [
                        "/bitwig/track/select/pattern Vocal*",
                        "/bitwig/track/route/to Vocals"
                    ]
                },
                {
                    "step": 4,
                    "action": "route_instrument_tracks",
                    "params": {
                        "pattern": "Bass|Synth|Keys|Piano|Guitar",
                        "target_bus": "Instruments"
                    },
                    "osc_commands": [
                        "/bitwig/track/select/pattern Bass*|Synth*|Keys*",
                        "/bitwig/track/route/to Instruments"
                    ]
                }
            ],
            "estimated_time": "2 minutes"
        }
    
    @staticmethod
    def create_beat_template(bpm: int = 120, style: str = "basic") -> Dict:
        """Generate beat pattern with given BPM and style"""
        patterns = {
            "basic": {
                "name": "Basic 4/4 Beat",
                "time_sig": "4/4",
                "pattern": {
                    "kick": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
                    "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                    "hihat": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
                }
            },
            "boom_bap": {
                "name": "Boom Bap Hip-Hop",
                "time_sig": "4/4",
                "pattern": {
                    "kick": [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                    "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                    "hihat": [1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0]
                }
            },
            "trap": {
                "name": "Trap Beat",
                "time_sig": "4/4",
                "pattern": {
                    "kick": [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                    "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                    "hihat": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
                }
            }
        }
        
        selected = patterns.get(style, patterns["basic"])
        
        return {
            "action": "create_beat",
            "description": f"Create {selected['name']} at {bpm} BPM",
            "params": {
                "bpm": bpm,
                "style": style,
                "time_signature": selected["time_sig"]
            },
            "steps": [
                {
                    "step": 1,
                    "action": "set_tempo",
                    "osc_commands": [f"/bitwig/tempo {bpm}"]
                },
                {
                    "step": 2,
                    "action": "create_drum_machine",
                    "osc_commands": [
                        "/bitwig/track/add InstrumentTrack",
                        "/bitwig/device/add DrumMachine"
                    ]
                },
                {
                    "step": 3,
                    "action": "program_pattern",
                    "params": selected["pattern"],
                    "osc_commands": [
                        "/bitwig/note/pattern/create 4/4",
                        "/bitwig/note/program " + str(selected["pattern"])
                    ]
                }
            ],
            "estimated_time": "1 minute"
        }
    
    @staticmethod
    def add_vocals_chain() -> Dict:
        """Set up vocal chain (compressor + EQ + reverb)"""
        return {
            "action": "add_vocal_chain",
            "description": "Add professional vocal processing chain",
            "steps": [
                {
                    "step": 1,
                    "action": "select_vocal_track",
                    "params": {
                        "track_pattern": "Vocal*|Voice|*Vox*"
                    },
                    "osc_commands": [
                        "/bitwig/track/select/pattern Vocal*"
                    ]
                },
                {
                    "step": 2,
                    "action": "add_compressor",
                    "params": {
                        "plugin": "Compressor+",
                        "settings": {
                            "threshold": -18,
                            "ratio": "4:1",
                            "attack": 20,
                            "release": 100,
                            "makeup_gain": 6
                        }
                    },
                    "osc_commands": [
                        "/bitwig/device/add Compressor+",
                        "/bitwig/device/param/Threshold -18",
                        "/bitwig/device/param/Ratio 4:1",
                        "/bitwig/device/param/Attack 20",
                        "/bitwig/device/param/Release 100",
                        "/bitwig/device/param/Makeup 6"
                    ]
                },
                {
                    "step": 3,
                    "action": "add_eq",
                    "params": {
                        "plugin": "EQ+",
                        "settings": {
                            "high_pass": 80,
                            "low_shelf_boost": "3dB at 200Hz",
                            "presence": "+2dB at 3kHz",
                            "deess": "-3dB at 8kHz"
                        }
                    },
                    "osc_commands": [
                        "/bitwig/device/add EQ+",
                        "/bitwig/device/param/HPF 80",
                        "/bitwig/device/param/LowShelf +3dB 200Hz",
                        "/bitwig/device/param/Presence +2dB 3kHz"
                    ]
                },
                {
                    "step": 4,
                    "action": "add_reverb",
                    "params": {
                        "plugin": "Reverb+",
                        "settings": {
                            "type": "Plate",
                            "size": 0.4,
                            "decay": 1.5,
                            "mix": 0.15
                        }
                    },
                    "osc_commands": [
                        "/bitwig/device/add Reverb+",
                        "/bitwig/device/param/Type Plate",
                        "/bitwig/device/param/Size 0.4",
                        "/bitwig/device/param/Decay 1.5",
                        "/bitwig/device/param/Mix 0.15"
                    ]
                },
                {
                    "step": 5,
                    "action": "add_delay",
                    "params": {
                        "plugin": "Delay+",
                        "settings": {
                            "time": "1/8 note",
                            "feedback": 0.3,
                            "mix": 0.1
                        }
                    },
                    "osc_commands": [
                        "/bitwig/device/add Delay+",
                        "/bitwig/device/param/Time 1/8",
                        "/bitwig/device/param/Feedback 0.3",
                        "/bitwig/device/param/Mix 0.1"
                    ]
                }
            ],
            "estimated_time": "1 minute"
        }
    
    @staticmethod
    def get_all_templates() -> Dict[str, callable]:
        """Return all available templates"""
        return {
            "start_recording_session": ProductionTemplates.start_recording_session,
            "mix_session": ProductionTemplates.mix_session,
            "create_beat_template": ProductionTemplates.create_beat_template,
            "add_vocals_chain": ProductionTemplates.add_vocals_chain,
            # Hybrid Bitwig + Ableton templates
            "ableton_session_style": ProductionTemplates.ableton_session_style,
            "modulation_master_chain": ProductionTemplates.modulation_master_chain,
            "project_remotes_controller": ProductionTemplates.project_remotes_controller,
            "push_style_workflow": ProductionTemplates.push_style_workflow,
            "hybrid_track_layering": ProductionTemplates.hybrid_track_layering
}
    
    @staticmethod
    def list_templates() -> List[str]:
        """List all available template names"""
        return list(ProductionTemplates.get_all_templates().keys())
    
    @staticmethod
    def ableton_session_style() -> Dict:
        return {
            "action": "ableton_session_style",
            "description": "Ableton-style session with color-coded scenes and clip launcher setup",
            "steps": [
                {
                    "step": 1,
                    "action": "create_session_tracks",
                    "params": {"tracks": [
                        {"name": "Drums", "color": "#FF6B35", "type": "instrument"},
                        {"name": "Bass", "color": "#4ECDC4", "type": "instrument"},
                        {"name": "Synths", "color": "#C7F464", "type": "instrument"},
                        {"name": "Vocals", "color": "#FF6B9D", "type": "audio"},
                        {"name": "FX", "color": "#9B59B6", "type": "hybrid"}
                    ]},
                    "osc_commands": [
                        "/bitwig/track/add InstrumentTrack",
                        "/bitwig/track/name Drums",
                        "/bitwig/track/color FF6B35",
                        "/bitwig/track/add InstrumentTrack",
                        "/bitwig/track/name Bass",
                        "/bitwig/track/color 4ECDC4",
                        "/bitwig/track/add InstrumentTrack",
                        "/bitwig/track/name Synths",
                        "/bitwig/track/color C7F464",
                        "/bitwig/track/add AudioTrack",
                        "/bitwig/track/name Vocals",
                        "/bitwig/track/color FF6B9D",
                        "/bitwig/track/add HybridTrack",
                        "/bitwig/track/name FX",
                        "/bitwig/track/color 9B59B6"
                    ]
                },
                {
                    "step": 2,
                    "action": "create_scenes",
                    "params": {"scenes": ["Intro", "Verse", "Chorus", "Bridge", "Break", "Outro"]},
                    "osc_commands": [
                        "/bitwig/scene/create Intro",
                        "/bitwig/scene/create Verse",
                        "/bitwig/scene/create Chorus",
                        "/bitwig/scene/create Bridge",
                        "/bitwig/scene/create Break",
                        "/bitwig/scene/create Outro"
                    ]
                },
                {
                    "step": 3,
                    "action": "configure_clip_launcher",
                    "params": {"launch_mode": "trigger", "follow_actions": True, "quantize": "1bar"},
                    "osc_commands": [
                        "/bitwig/clip/launch/mode trigger",
                        "/bitwig/clip/quantize 1",
                        "/bitwig/follow/actions/enable"
                    ]
                },
                {
                    "step": 4,
                    "action": "create_return_tracks",
                    "params": {"returns": [
                        {"name": "Reverb", "color": "#3498DB"},
                        {"name": "Delay", "color": "#E74C3C"},
                        {"name": "Compression", "color": "#F39C12"}
                    ]},
                    "osc_commands": [
                        "/bitwig/track/add ReturnTrack Reverb",
                        "/bitwig/track/color 3498DB",
                        "/bitwig/track/add ReturnTrack Delay",
                        "/bitwig/track/color E74C3C",
                        "/bitwig/track/add ReturnTrack Compression",
                        "/bitwig/track/color F39C12"
                    ]
                }
            ],
            "estimated_time": "2 minutes"
        }
    
    @staticmethod
    def modulation_master_chain() -> Dict:
        return {
            "action": "modulation_master_chain",
            "description": "Bitwig modulation system - LFO/Envelope modulation chain",
            "steps": [
                {
                    "step": 1,
                    "action": "create_modulator_chain",
                    "params": {"modulators": ["LFO", "Envelope", "Random", "Step"]},
                    "osc_commands": [
                        "/bitwig/track/select last",
                        "/bitwig/device/add Poly Grid",
                        "/bitwig/modulator/add LFO",
                        "/bitwig/modulator/add ADSR",
                        "/bitwig/modulator/add Random",
                        "/bitwig/modulator/add Step Modulator"
                    ]
                },
                {
                    "step": 2,
                    "action": "route_modulation",
                    "params": {"targets": ["filter_cutoff", "osc_pitch", "amp_gain", "pan"]},
                    "osc_commands": [
                        "/bitwig/modulator/route LFO->filter cutoff",
                        "/bitwig/modulator/route Envelope->osc pitch",
                        "/bitwig/modulator/route Random->amp gain",
                        "/bitwig/modulator/route Step->pan"
                    ]
                },
                {
                    "step": 3,
                    "action": "add_modulator_to_mixer",
                    "params": {"global_modulation": True},
                    "osc_commands": [
                        "/bitwig/track/add ModulatorTrack Global",
                        "/bitwig/modulator/add LFO master_tempo_sync",
                        "/bitwig/modulator/route master->all tracks"
                    ]
                },
                {
                    "step": 4,
                    "action": "polyphonic_modulation",
                    "params": {"per_voice": True},
                    "osc_commands": [
                        "/bitwig/modulator/poly on",
                        "/bitwig/modulator/per-voice on"
                    ]
                }
            ],
            "estimated_time": "3 minutes"
        }
    
    @staticmethod
    def project_remotes_controller() -> Dict:
        return {
            "action": "project_remotes_controller",
            "description": "Bitwig Project Remotes - 64 global macro controls across project",
            "steps": [
                {
                    "step": 1,
                    "action": "create_remote_pages",
                    "params": {"pages": 4, "controls_per_page": 8},
                    "osc_commands": [
                        "/bitwig/project/remote/page/create Master",
                        "/bitwig/project/remote/page/create Drums",
                        "/bitwig/project/remote/page/create Bass",
                        "/bitwig/project/remote/page/create FX"
                    ]
                },
                {
                    "step": 2,
                    "action": "master_page_remotes",
                    "params": {"controls": [
                        {"name": "Master Volume", "target": "master volume", "range": [0, 1]},
                        {"name": "Tempo", "target": "transport tempo", "range": [60, 200]},
                        {"name": "Reverb Send", "target": "reverb return", "range": [0, 1]},
                        {"name": "Delay Send", "target": "delay return", "range": [0, 1]},
                        {"name": "Cue Mix", "target": "cue volume", "range": [0, 1]},
                        {"name": "Quantize", "target": "global quantize", "range": [0.25, 4]},
                        {"name": "Swing", "target": "swing amount", "range": [0, 1]},
                        {"name": "Master Filter", "target": "master filter", "range": [200, 20000]}
                    ]},
                    "osc_commands": [
                        "/bitwig/project/remote/add Master Volume -> /bitwig/track/master/volume",
                        "/bitwig/project/remote/add Tempo -> /bitwig/transport/tempo",
                        "/bitwig/project/remote/add Reverb Send -> /bitwig/track/return/Reverb/send",
                        "/bitwig/project/remote/add Delay Send -> /bitwig/track/return/Delay/send",
                        "/bitwig/project/remote/add Cue Mix -> /bitwig/track/cue/volume",
                        "/bitwig/project/remote/add Quantize -> /bitwig/transport/quantize",
                        "/bitwig/project/remote/add Swing -> /bitwig/transport/swing",
                        "/bitwig/project/remote/add Master Filter -> /bitwig/track/master/filter"
                    ]
                },
                {
                    "step": 3,
                    "action": "map_hardware_controller",
                    "params": {"controller": "Launch Control", "pages": 4},
                    "osc_commands": [
                        "/bitwig/controller/script DrivenByMoss LaunchControl",
                        "/bitwig/controller/map page1 Master",
                        "/bitwig/controller/map page2 Drums",
                        "/bitwig/controller/map page3 Bass",
                        "/bitwig/controller/map page4 FX"
                    ]
                }
            ],
            "estimated_time": "4 minutes"
        }
    
    @staticmethod
    def push_style_workflow() -> Dict:
        return {
            "action": "push_style_workflow",
            "description": "Novation Push-style workflow in Bitwig - pads, knobs, step seq",
            "steps": [
                {
                    "step": 1,
                    "action": "drum_rack_setup",
                    "params": {"pads": 16, "sounds": ["Kick", "Snare", "HiHat", "Clap", "Perc", "Tom", "Cymbal", "FX"]},
                    "osc_commands": [
                        "/bitwig/track/add InstrumentTrack Drums",
                        "/bitwig/device/add DrumMachine",
                        "/bitwig/device/slot 1 kick",
                        "/bitwig/device/slot 2 snare",
                        "/bitwig/device/slot 3 hihat",
                        "/bitwig/device/slot 4 clap"
                    ]
                },
                {
                    "step": 2,
                    "action": "step_sequencer_mode",
                    "params": {"steps": 16, "velocity": True, "gate": True},
                    "osc_commands": [
                        "/bitwig/device/mode step",
                        "/bitwig/device/steps 16",
                        "/bitwig/device/velocity on",
                        "/bitwig/device/gate on"
                    ]
                },
                {
                    "step": 3,
                    "action": "device_controls_page",
                    "params": {"knobs": ["Filter", "Resonance", "Decay", "Saturation", "Pitch", "Pan", "Send A", "Send B"]},
                    "osc_commands": [
                        "/bitwig/device/remote/add Filter -> filter cutoff",
                        "/bitwig/device/remote/add Resonance -> filter resonance",
                        "/bitwig/device/remote/add Decay -> amp decay",
                        "/bitwig/device/remote/add Saturation -> drive",
                        "/bitwig/device/remote/add Pitch -> osc pitch",
                        "/bitwig/device/remote/add Pan -> output pan",
                        "/bitwig/device/remote/add Send A -> send level A",
                        "/bitwig/device/remote/add Send B -> send level B"
                    ]
                },
                {
                    "step": 4,
                    "action": "scale_mode_setup",
                    "params": {"scale": "Minor", "root": "C", "layout": "4th"},
                    "osc_commands": [
                        "/bitwig/device/scale minor C 4th",
                        "/bitwig/device/fixed_velocity on"
                    ]
                }
            ],
            "estimated_time": "2 minutes"
        }
    
    @staticmethod
    def hybrid_track_layering() -> Dict:
        return {
            "action": "hybrid_track_layering",
            "description": "Bitwig hybrid tracks - audio and MIDI on same track with parallel processing",
            "steps": [
                {
                    "step": 1,
                    "action": "create_hybrid_tracks",
                    "params": {"tracks": ["Synth Stack", "Live Jam", "Layered Texture"]},
                    "osc_commands": [
                        "/bitwig/track/add HybridTrack Synth Stack",
                        "/bitwig/track/add HybridTrack Live Jam",
                        "/bitwig/track/add HybridTrack Layered Texture"
                    ]
                },
                {
                    "step": 2,
                    "action": "add_instrument_and_audio",
                    "params": {"instrument": "Poly Grid", "audio_routing": "parallel"},
                    "osc_commands": [
                        "/bitwig/track/select Synth Stack",
                        "/bitwig/device/add Poly Grid",
                        "/bitwig/track/add/audio clip"
                    ]
                },
                {
                    "step": 3,
                    "action": "parallel_processing_chain",
                    "params": {"chains": ["Clean", "Processed", "Parallel"]},
                    "osc_commands": [
                        "/bitwig/device/add FX Layer Clean",
                        "/bitwig/device/add FX Layer Processed",
                        "/bitwig/device/add FX Layer Parallel"
                    ]
                },
                {
                    "step": 4,
                    "action": "layer_mixing",
                    "params": {"layer_volumes": [0.8, 0.6, 0.4]},
                    "osc_commands": [
                        "/bitwig/device/layer 1 volume 0.8",
                        "/bitwig/device/layer 2 volume 0.6",
                        "/bitwig/device/layer 3 volume 0.4"
                    ]
                }
            ],
            "estimated_time": "3 minutes"
        }


if __name__ == "__main__":
    templates = ProductionTemplates()
    
    print("=== Available Templates ===")
    for name in templates.list_templates():
        print(f"  - {name}")
    
    print("\n=== Recording Session Template ===")
    import json
    print(json.dumps(templates.start_recording_session(), indent=2))
    
    print("\n=== Beat Template (140 BPM, Trap) ===")
    print(json.dumps(templates.create_beat_template(140, "trap"), indent=2))
    
    print("\n=== Hybrid: Ableton Session Style ===")
    print(json.dumps(templates.ableton_session_style(), indent=2))
    
    print("\n=== Hybrid: Modulation Master Chain ===")
    print(json.dumps(templates.modulation_master_chain(), indent=2))
    
    print("\n=== Hybrid: Project Remotes Controller ===")
    print(json.dumps(templates.project_remotes_controller(), indent=2))
