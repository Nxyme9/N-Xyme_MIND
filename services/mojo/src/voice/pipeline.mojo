"""
voice/pipeline.mojo — Streaming audio pipeline orchestrator.
Audio → VAD → Whisper (libwhisper.so GPU) → Output.
All core logic in Mojo, Python only for audio capture and model calls.
"""

from std.python import Python, PythonObject
from std.time import perf_counter, sleep
from audio import AudioCapture, list_devices
from vad import VAD
from whisper import WhisperBackend
from utils import AudioConfig, Buffer


struct Pipeline:
    """Orchestrates the real-time dictation pipeline."""

    var audio: AudioCapture
    var vad: VAD
    var whisper: WhisperBackend
    var config: AudioConfig
    var buffer: Buffer
    var running: Bool
    var np: PythonObject
    var sd: PythonObject

    def __init__(out self, config: AudioConfig):
        print("=== Jarvis Audio Pipeline ===")
        self.config = config
        self.buffer = Buffer(48000 * 5)  # 5 second buffer
        self.running = False
        try:
            self.np = Python.import_module("numpy")
        except:
            self.np = PythonObject()
        try:
            self.sd = Python.import_module("sounddevice")
        except:
            self.sd = PythonObject()
        
        # Initialize pipeline components
        self.audio = AudioCapture(config)
        self.vad = VAD(config)
        self.whisper = WhisperBackend(config)

    def start(mut self):
        """Start the dictation pipeline."""
        self.running = True
        print("Pipeline started. Waiting for speech...")
        
        var np = self.np
        var sd = self.sd
        
        # Audio capture loop
        var device = 0
        var samplerate = self.config.sample_rate
        var blocksize = self.config.block_size
        var audio_chunk = np.zeros(blocksize, dtype=np.float32)
        
        while self.running:
            try:
                # Read audio chunk (simulated for now - real device read)
                # In production this uses sounddevice.InputStream callback
                audio_chunk = np.random.randn(blocksize).astype(np.float32) * 0.001
                
                # Run VAD
                var has_speech = self.vad.process_chunk(audio_chunk)
                
                if has_speech:
                    # Get speech segment
                    var segment = self.vad.get_speech_segment()
                    var seg_np = np.array(segment, dtype=np.float32)
                    
                    if len(segment) > self.config.sample_rate * 0.1:  # >100ms
                        # Transcribe via libwhisper.so GPU
                        var text = self.whisper.transcribe(seg_np)
                        
                        if len(text) > 0:
                            print(">> " + text)
                            # Route to Jarvis session
                            self._route_to_jarvis(text)
                
                sleep(0.001)  # Prevent busy-wait
                
            except e:
                print("Pipeline error: " + String(e))
                sleep(0.1)
        
        print("Pipeline stopped.")

    def _route_to_jarvis(mut self, text: String):
        """Route transcribed text to the Jarvis session."""
        # Write to stdout for the tray app to pick up
        print("[TRANSCRIBED] " + text)
        
        # Call the dictation bridge script
        var subprocess = Python.import_module("subprocess")
        var shlex = Python.import_module("shlex")
        
        var script = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin/dictate-to-jarvis.sh"
        var cmd = script + " " + shlex.quote(text)
        
        try:
            subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except e:
            print("Bridge failed: " + String(e))

    def stop(mut self):
        """Stop the pipeline."""
        self.running = False
        self.vad.reset()
        print("Pipeline stopped.")