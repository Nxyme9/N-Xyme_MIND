#!/bin/bash
echo "{\"type\": \"memory_search\", \"query\": \"error: $*\", \"id\": \"momus\"}" | timeout 5 $DAEMON 2>/dev/null
