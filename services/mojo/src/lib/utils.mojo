"""
lib/utils.mojo — Shared types and utilities for Jarvis audio pipeline.
"""

from std.python import Python, PythonObject


struct AudioConfig:
    """Audio pipeline configuration."""
    var sample_rate: Int
    var block_size: Int
    var channels: Int
    var silence_frames: Int
    var min_speech_ms: Int

    def __init__(out self, 
                sample_rate: Int = 16000,
                block_size: Int = 512,
                channels: Int = 1,
                silence_frames: Int = 30,
                min_speech_ms: Int = 250):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.channels = channels
        self.silence_frames = silence_frames
        self.min_speech_ms = min_speech_ms


# VAD state as comptime Int constants (enum is removed in Mojo 1.0)
comptime VAD_IDLE: Int = 0
comptime VAD_SPEECH_START: Int = 1
comptime VAD_SPEECH_IN_PROGRESS: Int = 2
comptime VAD_SPEECH_END: Int = 3


struct Buffer:
    """Simple float32 ring buffer for audio."""
    var data: List[Float32]
    var max_size: Int
    var np: PythonObject

    def __init__(out self, max_size: Int = 48000):  # 3 seconds at 16kHz
        self.data = List[Float32]()
        self.max_size = max_size
        try:
            self.np = Python.import_module("numpy")
        except:
            self.np = PythonObject()

    def append(mut self, chunk: PythonObject) raises:
        """Append numpy array to buffer."""
        var py_builtins = Python.import_module("builtins")
        var chunk_len = Int(py=py_builtins.len(chunk))
        for i in range(chunk_len):
            self.data.append(Float32(py=chunk[i]))
        # Trim if over max
        if len(self.data) > self.max_size:
            var trimmed = List[Float32]()
            var start = len(self.data) - self.max_size
            for i in range(start, len(self.data)):
                trimmed.append(self.data[i])
            self.data = trimmed^

    def clear(mut self):
        """Clear buffer."""
        self.data = List[Float32]()

    def to_numpy(mut self) raises -> PythonObject:
        """Convert buffer to numpy array."""
        var py_list = Python.list()
        for i in range(len(self.data)):
            py_list.append(Float64(self.data[i]))
        var arr = self.np.array(py_list, dtype=self.np.float32)
        return arr

    def len(self) -> Int:
        return len(self.data)

    def is_empty(self) -> Bool:
        return len(self.data) == 0