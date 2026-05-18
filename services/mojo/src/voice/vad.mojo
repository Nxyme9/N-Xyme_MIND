"""
voice/vad.mojo — Voice Activity Detection using Silero VAD.
GPU-accelerated, real-time, streaming VAD for Jarvis.
"""

from std.python import Python, PythonObject
from std.time import perf_counter
from utils import AudioConfig, VAD_IDLE, VAD_SPEECH_START, VAD_SPEECH_IN_PROGRESS, VAD_SPEECH_END


struct VAD:
    """Silero VAD — detects speech in audio stream."""

    var torch: PythonObject
    var model: PythonObject
    var utils: PythonObject
    var get_speech_timestamps: PythonObject
    var config: AudioConfig
    var state: Int
    var speech_buffer: List[Float32]
    var silence_counter: Int
    var speech_detected: Bool

    def __init__(out self, config: AudioConfig):
        self.config = config
        self.state = VAD_IDLE
        self.speech_buffer = List[Float32]()
        self.silence_counter = 0
        self.speech_detected = False
        self._load_model()

    def _load_model(mut self):
        """Load Silero VAD model."""
        print("Loading Silero VAD model...")
        self.torch = Python.import_module("torch")
        var torch = self.torch
        
        # Load Silero VAD
        var silero = Python.import_module("silero_vad")
        
        # Try loading onnx model
        try:
            var model, utils_val = silero.load_silero_vad(onnx=True)
            self.model = model
            self.utils = utils_val
            print("VAD model loaded (ONNX)")
        except:
            print("ONNX VAD failed, trying PyTorch...")
            var model, utils_val = silero.load_silero_vad(onnx=False)
            self.model = model
            self.utils = utils_val
            print("VAD model loaded (PyTorch)")

    def process_chunk(mut self, audio_chunk: PythonObject) -> Bool:
        """Process audio chunk, return True if speech detected."""
        var torch = self.torch
        
        # Convert to tensor
        var audio_tensor = torch.from_numpy(audio_chunk)
        
        # Run VAD
        var speech_prob = self.model(audio_tensor, 16000).item()
        
        # Threshold
        var threshold: Float64 = 0.5
        var is_speech = speech_prob > threshold
        
        if is_speech:
            self.speech_detected = True
            self.silence_counter = 0
            # Append to speech buffer
            for i in range(len(audio_chunk)):
                self.speech_buffer.append(Float32(audio_chunk[i]))
        else:
            self.silence_counter += 1
        
        # Check if speech segment ended
        if self.speech_detected and self.silence_counter > self.config.silence_frames:
            self.state = VAD_SPEECH_END
            return True
        
        return False

    def get_speech_segment(mut self) -> List[Float32]:
        """Get the accumulated speech segment and reset."""
        var segment = self.speech_buffer
        self.speech_buffer = List[Float32]()
        self.speech_detected = False
        self.silence_counter = 0
        self.state = VAD_IDLE
        return segment

    def reset(mut self):
        """Reset VAD state."""
        self.speech_buffer = List[Float32]()
        self.speech_detected = False
        self.silence_counter = 0
        self.state = VAD_IDLE