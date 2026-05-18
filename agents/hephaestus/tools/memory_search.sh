#!/bin/bash
echo "{\"type\": \"memory_search\", \"query\": \"$*\", \"id\": \"hephaestus\"}" | timeout 5 $DAEMON 2>/dev/null
