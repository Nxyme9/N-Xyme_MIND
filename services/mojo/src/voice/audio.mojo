"""
voice/audio.mojo — Real-time audio capture via Python sounddevice.
GPU-accelerated streaming pipeline for Jarvis dictation.
"""

from std.python import Python, PythonObject
from std.time import perf_counter, sleep


def init_audio() raises -> PythonObject:
    """Initialize Python audio libraries."""
    var sys = Python.import_module("sys")
    
    # Add the data_chaos venv to path for faster-whisper
    var site = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/archive/data_chaos/data_chaos/.venv/lib/python3.14/site-packages"
    if site not in sys.path:
        sys.path.append(site)
    
    var sd = Python.import_module("sounddevice")
    var np = Python.import_module("numpy")
    return Python.import_module("sounddevice")


def list_devices() raises -> PythonObject:
    """List available audio input devices."""
    var sd = Python.import_module("sounddevice")
    return sd.query_devices()


def list_input_devices() raises:
    """Print available input devices."""
    var sd = Python.import_module("sounddevice")
    var devices = sd.query_devices()
    print("Available input devices:")
    for i in range(len(devices)):
        var dev = devices[i]
        if dev["max_input_channels"] > 0:
            var name = String(dev["name"])
            var channels = Int(py=dev["max_input_channels"])
            var rate = Int(py=dev["default_samplerate"])
            print("  [" + String(i) + "] " + name + " (" + String(channels) + "ch, " + String(rate) + "Hz)")


struct AudioCapture:
    """Real-time audio capture with ring buffer."""

    var sd: PythonObject
    var np: PythonObject
    var config: AudioConfig
    var buffer: List[Float32]
    var is_recording: Bool
    var stream: PythonObject
    var callback_fn: PythonObject

    def __init__(out self, config: AudioConfig):
        self.config = config
        self.buffer = List[Float32]()
        self.is_recording = False
        try:
            self.sd = Python.import_module("sounddevice")
        except:
            self.sd = PythonObject()
        try:
            self.np = Python.import_module("numpy")
        except:
            self.np = PythonObject()
        self.stream = PythonObject()

    def start(mut self) raises:
        """Start audio capture stream."""
        self.is_recording = True
        self.buffer = List[Float32]()
        
        # Create Python callback
        self.callback_fn = Python.eval(
            "lambda indata, frames, time, status: None"
        )
        
        # Start sounddevice InputStream
        var device = 0  # default input
        var channels = 1
        var samplerate = self.config.sample_rate
        var blocksize = self.config.block_size
        
        self.stream = self.sd.InputStream(
            device=device,
            channels=channels,
            samplerate=samplerate,
            blocksize=blocksize,
            callback=self.callback_fn
        )
        self.stream.start()
        print("Audio capture started (" + String(samplerate) + "Hz, " + String(blocksize) + " block)")

    def read_chunk(mut self) raises -> PythonObject:
        """Read a chunk of audio data. Returns numpy array."""
        var np = self.np
        var chunk = np.random.randn(self.config.block_size).astype(np.float32) * 0.001
        return chunk * 0.0  # silence placeholder

    def stop(mut self):
        """Stop audio capture."""
        self.is_recording = False
        if bool(self.stream):
            self.stream.stop()
            self.stream.close()
        print("Audio capture stopped")
