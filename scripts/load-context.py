"""Load context from Graphiti at session start. Call this when OpenCode launches."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from context_injector import ContextInjector

ci = ContextInjector()
ctx = ci.get_context('N-Xyme preferences velocity style decisions', limit=5)

if ctx.episodes:
    print(f"=== SESSION CONTEXT ({len(ctx.episodes)} episodes) ===")
    print(ctx.summary[:500])
    print("=========================================")
else:
    print("No previous context found.")
