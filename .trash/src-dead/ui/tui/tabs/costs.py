"""Costs tab - cost and usage dashboard."""

# Import from parent module
get_routing_data = None


def init(routing_fn):
    global get_routing_data
    get_routing_data = routing_fn


def get_content(live_data: dict) -> str:
    content = "═══ COST DASHBOARD ═══\n\n"

    # Get live data
    d = live_data
    outcomes = d.get("outcomes", 0)

    # Simulated cost data (would come from actual API tracking)
    content += "▸ MONTHLY BUDGET\n"
    content += "  Budget: $100.00/month\n"
    content += "  Used:   $0.00\n"
    content += "  Left:   $100.00\n\n"

    # Token usage (estimated)
    content += "▸ TOKEN USAGE (ESTIMATED)\n"
    estimated_tokens = outcomes * 500  # rough estimate
    content += f"  Total tokens: {estimated_tokens:,}\n"
    content += "  By agent:\n"
    content += "    Sisyphus: ~50,000 (orchestration)\n"
    content += "    Hephaestus: ~30,000 (implementation)\n"
    content += "    Oracle: ~20,000 (review)\n\n"

    # API calls
    content += "▸ API CALLS\n"
    content += f"  Total: {outcomes * 3:,} (estimated)\n"
    content += "  Success rate: 95%+\n"

    content += "\n▸ COST OPTIMIZATIONS\n"
    content += "  • Using local Ollama when available\n"
    content += "  • Caching agent responses\n"
    content += "  • Batching similar requests\n"

    return content
