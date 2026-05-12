#!/bin/bash
# Key Rotator CLI Wrapper
# Usage: ./key-rotator.sh [status|test|rotate|get-key|get-model]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROTATOR_SCRIPT="$SCRIPT_DIR/scripts/key_rotator_v3.py"

case "${1:-status}" in
    status)
        python3 "$ROTATOR_SCRIPT" status
        ;;
    test)
        python3 "$ROTATOR_SCRIPT" test
        ;;
    rotate)
        python3 "$ROTATOR_SCRIPT" rotate
        ;;
    rotate-model)
        python3 "$ROTATOR_SCRIPT" rotate-model
        ;;
    force-rotate)
        python3 "$ROTATOR_SCRIPT" force-rotate
        ;;
    get-key)
        python3 "$ROTATOR_SCRIPT" get-key
        ;;
    get-model)
        python3 "$ROTATOR_SCRIPT" get-model
        ;;
    update-env)
        python3 "$ROTATOR_SCRIPT" update-env
        ;;
    *)
        echo "Usage: $0 [status|test|rotate|rotate-model|force-rotate|get-key|get-model|update-env]"
        exit 1
        ;;
esac
