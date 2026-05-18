#!/bin/bash
echo "{\"type\": \"code_search\", \"query\": \"$*\", \"id\": \"explore\"}" | timeout 15 $DAEMON 2>/dev/null | python3 -m json.tool 2>/dev/null
