"""
voice/whisper.mojo — GPU Whisper via libwhisper.so (C, through pywhispercpp).
Hooks directly into the compiled libwhisper.so with CUDA acceleration.
"""

from std.python import Python, PythonObject
from std.time import perf_counter
from utils import AudioConfig


struct WhisperBackend:
    """Mojo Whisper backend — wraps libwhisper.so via pywhispercpp."""

    var model: PythonObject
    var config: AudioConfig
    var np: PythonObject

    def __init__(out self, config: AudioConfig):
        self.config = config
        try:
            self.np = Python.import_module("numpy")
        except:
            self.np = PythonObject()
        self._load()

    def _load(mut self):
        """Load whisper model via libwhisper.so through pywhispercpp."""
        print("Loading Whisper (libwhisper.so CUDA)...")
        var t0 = perf_counter()
        
        var pw = Python.import_module("pywhispercpp.model")
        
        # Use the local model path
        var model_path = "/home/nxyme/N-Xyme_CODE/LLMs/by-type/voice/ggml-large-v3-turbo.bin"
        
        # Load with GPU acceleration (n_threads=4 for CUDA)
        self.model = pw.Model(
            model_path,
            n_threads=4,
            use_gpu=True,
            gpu_device=0
        )
        
        var t1 = perf_counter()
        var elapsed = (t1 - t0) * 1000
        var elapsed_str = String(elapsed)
        print("Whisper loaded (" + elapsed_str + "ms) via libwhisper.so CUDA")

    def transcribe(mut self, audio: PythonObject) -> String:
        """Transcribe audio through libwhisper.so. GPU-accelerated."""
        var pw = Python.import_module("pywhispercpp.model")
        var t0 = perf_counter()
        
        # Ensure float32 mono
        var audio_array = audio.astype(self.np.float32)
        
        # Transcribe with optimized params for GPU
        var segments = self.model.transcribe(
            audio_array,
            n_threads=4,
            print_progress=False
        )
        
        # Collect text
        var result = ""
        for seg in segments:
            var text = String(seg.text)
            if text != "[BLANK_AUDIO]":
                result += text + " "
        
        var t1 = perf_counter()
        var elapsed = (t1 - t0) * 1000
        var elapsed_str = String(elapsed)
        var len_str = String(len(audio_array))
        print("Whisper: " + len_str + " samples in " + elapsed_str + "ms -> '" + result[:40] + "'")
        
        return result.strip()

    def transcribe_file(mut self, wav_path: String) -> String:
        """Transcribe a WAV file via libwhisper.so."""
        var t0 = perf_counter()
        
        var segments = self.model.transcribe(
            wav_path,
            n_threads=4,
            print_progress=False
        )
        
        var result = ""
        for seg in segments:
            var text = String(seg.text)
            if text != "[BLANK_AUDIO]":
                result += text + " "
        
        var t1 = perf_counter()
        var elapsed = (t1 - t0) * 1000
        var elapsed_str = String(elapsed)
        print("File in " + elapsed_str + "ms: '" + result[:60] + "'")
        
        return result.strip()