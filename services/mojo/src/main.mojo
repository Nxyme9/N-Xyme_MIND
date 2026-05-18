"""
main.mojo — Jarvis Dictation Pipeline Entry Point.
Launches: Audio → VAD → Whisper (libwhisper.so GPU) → Jarvis Session.

Usage:
    mojo main.mojo                  # Run pipeline (text output to stdout)
    mojo main.mojo --list-devices   # Show audio devices
    mojo main.mojo --test-whisper   # Test whisper with a file
"""

from std.python import Python
from std.sys import argv
from pipeline import Pipeline
from utils import AudioConfig
from audio import list_devices, list_input_devices
from whisper import WhisperBackend


def main() raises:
    # Init Python early
    var sys = Python.import_module("sys")
    
    # Setup paths
    var site = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/archive/data_chaos/data_chaos/.venv/lib/python3.14/site-packages"
    var np_path = "/home/nxyme/.local/lib/python3.14/site-packages"
    if site not in sys.path:
        sys.path.append(site)
    if np_path not in sys.path:
        sys.path.append(np_path)
    
    print("")
    print("  ╔══════════════════════════════════╗")
    print("  ║   JARVIS DICTATION PIPELINE      ║")
    print("  ║   libwhisper.so · GPU CUDA       ║")
    print("  ╚══════════════════════════════════╝")
    print("")
    
    # Parse args
    var args = argv()
    var cmd = ""
    if len(args) > 1:
        cmd = args[1]
    
    if cmd == "--list-devices":
        list_input_devices()
        return
    
    elif cmd == "--test-whisper":
        # Test whisper with a file
        var config = AudioConfig()
        var whisper = WhisperBackend(config)
        
        var np = Python.import_module("numpy")
        var test_audio = np.zeros(16000 * 3, dtype=np.float32)  # 3s silence
        var result = whisper.transcribe(test_audio)
        
        print("Test transcription: '" + result + "'")
        print("Whisper pipeline OK")
        return
    
    else:
        # Run full pipeline
        var config = AudioConfig(
            sample_rate=16000,
            block_size=512,
            channels=1,
            silence_frames=30,
            min_speech_ms=250
        )
        
        var pipeline = Pipeline(config)
        pipeline.start()