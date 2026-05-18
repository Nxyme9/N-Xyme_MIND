#!/bin/bash
QUERY="$*"
echo "{\"type\": \"code_search\", \"query\": \"$QUERY\", \"id\": \"hephaestus\"}" | timeout 15 $DAEMON 2>/dev/null | python3 -m json.tool 2>/dev/null
