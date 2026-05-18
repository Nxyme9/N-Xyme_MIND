#!/bin/bash
echo "{\"type\": \"code_review\", \"query\": \"$1\", \"id\": \"hephaestus\"}" | timeout 10 $DAEMON 2>/dev/null | python3 -m json.tool 2>/dev/null
