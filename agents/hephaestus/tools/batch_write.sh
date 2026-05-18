#!/bin/bash
SPEC="$*"
echo "{\"type\": \"batch_write\", \"query\": \"$SPEC\", \"id\": \"hephaestus\"}" | timeout 10 $DAEMON 2>/dev/null
