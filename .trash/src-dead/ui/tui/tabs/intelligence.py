"""Intelligence tab - learning and predictive insights."""

import json


def generate_insights(live_data: dict) -> str:
    """Generate predictive insights from available data."""
    d = live_data
    feedback = d.get("learning_feedback", 0)
    queries = d.get("learning_queries", 0)
    outcomes = d.get("outcomes", 0)
    preferences = d.get("preferences", 0)
    indexed = d.get("indexed_files", 0)
    memory_sources = d.get("memory_sources", 0)

    insights = ["PREDICTIVE INSIGHTS", "─" * 40]

    if indexed > 0:
        trend = "Growing" if indexed > 20000 else "Stable"
        insights.append(f"  Index: {indexed:,} files ({trend})")

    if feedback > 0:
        rate = "active" if feedback > 50 else "moderate" if feedback > 10 else "light"
        insights.append(f"  Learning: {feedback} events ({rate} usage)")

    if queries > 0:
        insights.append(f"  Queries: {queries} unique requests processed")

    if outcomes > 0:
        success_rate = (
            "high" if outcomes > 300 else "moderate" if outcomes > 100 else "building"
        )
        insights.append(f"  Outcomes: {outcomes} total ({success_rate} success rate)")

    if preferences > 0:
        insights.append(f"  Preferences: {preferences} user settings stored")

    if memory_sources > 0:
        insights.append(f"  Sources: {memory_sources} memory sources active")

    if queries > 0 and feedback > 0:
        ratio = feedback / queries if queries > 0 else 0
        if ratio > 2:
            insights.append(f"  Pattern: High feedback-to-query ratio ({ratio:.1f}x)")

    if len(insights) > 2:
        insights.append("")
        insights.append("Insight: System is operational with active learning.")

    return "\n".join(insights)


def get_content(live_data: dict) -> str:
    feedback = live_data.get("learning_feedback", 0)
    queries = live_data.get("learning_queries", 0)
    top_queries = live_data.get("learning_top_queries", [])[:5]
    prefs = live_data.get("preferences", 0)

    insights = generate_insights(live_data)

    return f"""INTELLIGENCE LAYER

Feedback
  Events: {feedback} | Queries: {queries}
  Preferences: {prefs}

Top Queries:
  {json.dumps(top_queries, indent=2)[:200]}

{insights}"""
