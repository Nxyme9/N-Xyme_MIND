# N-Xyme Audio Bitwig Extension

A custom Bitwig Studio extension with full control UI and neural audio model support.

## Features

- Transport controls (Play/Stop/Record)
- BPM control knob
- Neural model selection (5 models)
- Model mix slider
- Neural mode toggle
- 8 track selection buttons
- 5 FX buttons (Reverb, Delay, Compress, EQ, Distort)
- OSC communication with nx-audio-workflow
- ONNX model loading support via deeplearning4j

## Requirements

- Java 17+
- Maven
- Bitwig Studio 5.3+

## Build

```bash
cd nx-audio-plugin
./build.sh
```

## Install

1. Copy `target/N-XymeAudio.jar` to `~/Bitwig Studio/Extensions/`
2. Rename to `N-XymeAudio.bwextension`
3. Restart Bitwig Studio

## OSC Communication

The extension communicates with nx-audio-workflow on:
- Send: port 8000
- Receive: port 9000

Commands:
- `/transport/play`, `/transport/stop`, `/transport/record`
- `/transport/bpm` - BPM value
- `/model/select` - Model name
- `/model/mix` - Mix level (0-1)
- `/track/select` - Track number
- `/fx/trigger` - FX name

## Models

Place ONNX/Keras models in `models/` directory:
- default.onnx / default.h5
- vocals.onnx / vocals.h5
- drums.onnx / drums.h5
- bass.onnx / bass.h5
- synth.onnx / synth.h5

## Architecture

```
nx-audio-plugin/
├── pom.xml                          # Maven config with Bitwig API
├── build.sh                        # Build script
├── README.md                        # This file
└── src/main/java/com/nxyme/bitwig/
    ├── NXymeAudioExtensionDefinition.java  # Extension metadata
    ├── NXymeAudioExtension.java            # Main extension class
    └── ONNXModelLoader.java                # Neural model loader
```

## Integration with DrivenByMoss

This extension works alongside DrivenByMoss (already installed):
- DrivenByMoss provides comprehensive hardware controller support
- N-Xyme Audio adds custom UI and neural model integration
- Both use OSC on ports 8000/9000