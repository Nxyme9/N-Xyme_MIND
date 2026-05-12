#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DEVICE=1
MODEL="distil-large-v3"
COMPUTE_TYPE=float16
LANGUAGE=en
FAST_MODE=""

export CUDA_VISIBLE_DEVICES=0
NO_UI=""
VERBOSE=""
REALTIME=""
VAD_MODE="firered"  # firered, fast, energy

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--device)
            DEVICE="$2"
            shift 2
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -l|--language)
            LANGUAGE="$2"
            shift 2
            ;;
        -n|--no-ui)
            NO_UI="--no-ui"
            shift
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --realtime)
            REALTIME="--realtime"
            shift
            ;;
        --fast)
            FAST_MODE="--fast"
            shift
            ;;
        --vad)
            VAD_MODE="$2"
            shift 2
            ;;
        -h|--help)
            echo "N-Xyme Dictate Launcher"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -d, --device N    Audio device (default: 1 = webcam C920)"
            echo "  -m, --model M      Whisper model (default: deepdml model)"
            echo "  -l, --language L  Language (default: en)"
            echo "  -n, --no-ui        Run without GUI (CLI-only)"
            echo "  -v, --verbose     Enable verbose logging"
            echo "  --realtime        Enable real-time streaming transcription (FASTER)"
            echo "  --vad MODE        VAD mode: firered, fast, energy (default: firered)"
            echo "  -h, --help        Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Starting N-Xyme Dictate..."
echo "  Device: $DEVICE (webcam)"
echo "  Model: $MODEL"
echo "  GPU: $(python3 -c 'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")')"
echo ""

for cmd in wl-copy wtype; do
    if ! command -v $cmd &> /dev/null; then
        echo "Warning: $cmd not found - text injection may not work"
    fi
done

export PYTHONPATH="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx-dictate:$PYTHONPATH"
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
exec python3 -m nx_dictate.__main__ \
    --device "$DEVICE" \
    --model "$MODEL" \
    --language "$LANGUAGE" \
    $NO_UI \
    $VERBOSE \
    $REALTIME \
    $FAST_MODE