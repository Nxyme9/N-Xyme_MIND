#!/bin/bash
# GGUF Engine Dashboard - BLEEDING EDGE CLI
# Real-time monitoring for llama.cpp on 3080 Ti + 7800X3D

PORT=${1:-9000}
REFRESH=${2:-2}

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\0136m'
MAGENTA='\033[0;35m'
WHITE='\033[0;37m'
BOLD='\033[1m'
NC='\033[0m'
DIM='\033[2m'

# Check server health
check_server() {
    curl -s http://localhost:$PORT/v1/models >/dev/null 2>&1
}

# Get GPU stats
get_gpu() {
    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.free,temperature.gpu,power.draw \
            --format=csv,noheader,nounits 2>/dev/null | IFS=',' read -r GPU_UTIL MEM_UTIL VRAM_USED VRAM_FREE TEMP POWER
        echo "$GPU_UTIL|$MEM_UTIL|$VRAM_USED|$VRAM_FREE|$TEMP|$POWER"
    else
        echo "N/A|N/A|N/A|N/A|N/A|N/A"
    fi
}

# Get CPU/RAM stats
get_sys() {
    CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    RAM_USED=$(free -m | awk 'NR==2{print $3}')
    RAM_TOTAL=$(free -m | awk 'NR==2{print $2}')
    RAM_PCT=$((RAM_USED * 100 / RAM_TOTAL))
    echo "$CPU_LOAD|$RAM_USED|$RAM_TOTAL|$RAM_PCT"
}

# Test inference speed
benchmark() {
    START=$(date +%s%3N)
    RESP=$(curl -s http://localhost:$PORT/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{"messages":[{"role":"user","content":"Count from 1 to 5:"}],"max_tokens":20}' 2>/dev/null)
    END=$(date +%s%3N)
    
    if [ -n "$RESP" ]; then
        TOKENS=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['choices'][0]['message']['content'].split()))" 2>/dev/null || echo "0")
        MS=$((END - START))
        if [ "$MS" -gt 0 ]; then
            TOK_PER_S=$((TOKENS * 1000 / MS))
        else
            TOK_PER_S=0
        fi
        echo "$TOKENS|$MS|$TOK_PER_S"
    else
        echo "ERR|0|0"
    fi
}

# Health check
check_server
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Server not running on port $PORT${NC}"
    exit 1
fi

# Header
clear
echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║   🦙 N-XYME GGUF ENGINE - BLEEDING EDGE v2.0                   ║${NC}"
echo -e "${BOLD}${BLUE}║   RTX 3080 Ti + AMD Ryzen 7 7800X3D + 32GB RAM              ║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Main loop
while true; do
    check_server
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Server died on port $PORT${NC}"
        break
    fi
    
    # Get stats
    IFS='|' read -r GPU_UTIL MEM_UTIL VRAM_USED VRAM_FREE TEMP POWER <<< "$(get_gpu)"
    IFS='|' read -r CPU_LOAD RAM_USED RAM_TOTAL RAM_PCT <<< "$(get_sys)"
    IFS='|' read -r TOKENS MS TOK_PER_S <<< "$(benchmark)"
    
    # Format GPU util with color
    if [ "$GPU_UTIL" -gt 80 ]; then
        GPU_COLOR=$RED
    elif [ "$GPU_UTIL" -gt 50 ]; then
        GPU_COLOR=$YELLOW
    else
        GPU_COLOR=$GREEN
    fi
    
    # Format tokens/sec
    if [ "$TOK_PER_S" -gt 300 ]; then
        SPEED_COLOR=$GREEN
    elif [ "$TOK_PER_S" -gt 100 ]; then
        SPEED_COLOR=$YELLOW
    else
        SPEED_COLOR=$RED
    fi
    
    echo -e "${BOLD}┌──────────────────┬───────────────────┬──────────────────┐${NC}"
    printf "${BOLD}│ ${CYAN}GPU${NC} %-10s │ ${CYAN}MEM${NC} %-11s │ ${CYAN}TEMP${NC} %-6s │\n" \
        "${GPU_COLOR}${GPU_UTIL}%${NC}" "${MEM_UTIL}%" "${TEMP}°C"
    printf "${BOLD}│ ${CYAN}VRAM${NC} %-7s │ ${CYAN}POWER${NC} %-7s │ ${CYAN}SPEED${NC} %-6s │\n" \
        "${VRAM_USED}/${VRAM_FREE}MB" "${POWER}W" "${SPEED_COLOR}${TOK_PER_S} tok/s${NC}"
    echo -e "${BOLD}├──────────────────┼───────────────────┼──────────────────┤${NC}"
    printf "${BOLD}│ ${CYAN}CPU${NC} %-10s │ ${CYAN}RAM${NC} %-11s │ ${CYAN}TOKENS${NC} %-6s │\n" \
        "${CPU_LOAD}" "${RAM_USED}/${RAM_TOTAL}MB (${RAM_PCT}%)" "${TOKENS} in ${MS}ms"
    echo -e "${BOLD}├──────────────────┴───────────────────┴──────────────────┤${NC}"
    printf "${BOLD}│ ${GREEN}Model:${NC} rosetta-v5-q8_0.gguf | ${GREEN}Port:${NC} $PORT | Ctrl+C to exit${NC}\n"
    echo -e "${BOLD}└──────────────────────────────────────────────────────┘${NC}"
    
    sleep $REFRESH
done