#!/usr/bin/env python3
"""Brain - Core brain wrapper for N-Xyme_MIND.

Provides unified API for local GGUF inference with:
- Model pool management (lazy load, auto-unload)
- VRAM management (1GB headroom)
- Text completion, chat completion, embeddings
- Tool calling support

Usage:
    from packages.local_llm.brain import Brain

    brain = Brain()
    result = brain.complete("Hello, how are you?")
    result = brain.chat([{"role": "user", "content": "Hello!"}])
    result = brain.embed("Your text here")
    print(brain.get_status())
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# RAG imports - lazy loaded to avoid import errors if memory_core unavailable
_RAGInjector = None
_ToolCaller = None

from frankenstein_engine.config import (
    DEFAULT_MODEL,
    EMBED_MODEL,
    ROSETTA_MODEL,
    get_model_path,
)
from frankenstein_engine.engine import DirectLlamaClient

logger = logging.getLogger("brain")


# ============================================================================
# Model Configuration
# ============================================================================

# Model aliases for easy selection
MODEL_ALIASES = {
    "7b": DEFAULT_MODEL,
    "default": DEFAULT_MODEL,
    "qwen": DEFAULT_MODEL,
    "0.5b": ROSETTA_MODEL,
    "fast": ROSETTA_MODEL,
    "rosetta": ROSETTA_MODEL,
    "embed": EMBED_MODEL,
    "embedding": EMBED_MODEL,
    "nomic": EMBED_MODEL,
}

# Default settings
DEFAULT_N_CTX = 4096
LARGE_N_CTX = 131072
DEFAULT_N_GPU_LAYERS = -1  # All to GPU
DEFAULT_TIMEOUT_SECS = 60
UNLOAD_TIMEOUT_SECS = 60
VRAM_HEADROOM_MB = 1024  # 1GB headroom
MAX_VRAM_MB = 11000  # ~11GB on 12GB GPU


# ============================================================================
# VRAM Management
# ============================================================================


def get_vram_usage() -> Dict[str, Any]:
    """Get current VRAM usage.

    Returns:
        Dict with total_mb, used_mb, available_mb
    """
    try:
        import subprocess

        # Try nvidia-smi first
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            used, total = map(int, result.stdout.strip().split(","))
            return {
                "total_mb": total,
                "used_mb": used,
                "available_mb": total - used - VRAM_HEADROOM_MB,
            }
    except Exception:
        pass

    # Fallback: return unlimited
    return {
        "total_mb": 12288,
        "used_mb": 0,
        "available_mb": MAX_VRAM_MB,
    }


def check_vram_available(model_name: str) -> bool:
    """Check if there's enough VRAM to load a model.

    Args:
        model_name: GGUF model name

    Returns:
        True if enough VRAM available
    """
    vram = get_vram_usage()

    # Estimate model VRAM (rough approximation)
    model_size_mb = 0
    if "0.5b" in model_name.lower():
        model_size_mb = 700  # ~700MB
    elif "7b" in model_name.lower():
        model_size_mb = 4200  # ~4GB (Q4)
    elif "embed" in model_name.lower() or "nomic" in model_name.lower():
        model_size_mb = 900  # ~900MB (Q4)
    else:
        # Default estimate
        model_size_mb = 4000

    return vram["available_mb"] >= model_size_mb


# ============================================================================
# Brain Class
# ============================================================================


@dataclass
class CompletionResult:
    """Result from text completion."""

    text: str
    tokens: int
    timing_ms: float


@dataclass
class ChatResult:
    """Result from chat completion."""

    text: str
    tokens: int
    timing_ms: float
    tool_calls: list = None  # Optional[List[Dict[str, Any]]]


class Brain:
    """Core brain wrapper for local GGUF inference.

    Features:
    - Lazy model loading (load on first use)
    - Model pool (keep models loaded for 60s after use)
    - VRAM management (check before loading)
    - Unified API: complete(), chat(), embed()

    Example:
        brain = Brain()
        result = brain.complete("Hello!")
        result = brain.chat([{"role": "user", "content": "Hello!"}])
        result = brain.embed("Your text here")
    """

    def __init__(
        self,
        default_model: str = "auto",
        n_ctx: int = DEFAULT_N_CTX,
        n_gpu_layers: int = DEFAULT_N_GPU_LAYERS,
        unload_timeout: int = UNLOAD_TIMEOUT_SECS,
    ):
        """Initialize Brain.

        Args:
            default_model: Default model ("auto", "7b", "0.5b", "embed")
            n_ctx: Context window size
            n_gpu_layers: GPU layers (-1 = all)
            unload_timeout: Seconds to keep model loaded after use
        """
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.unload_timeout = unload_timeout

        # Resolve model alias
        if default_model == "auto":
            self._default_model = DEFAULT_MODEL
        else:
            self._default_model = MODEL_ALIASES.get(default_model, default_model)

        # Model pool: model_name -> client + last_used timestamp
        self._model_pool: Dict[str, DirectLlamaClient] = {}
        self._model_timestamps: Dict[str, float] = {}

        # Currently active model
        self._active_model: Optional[str] = None
        self._active_client: Optional[DirectLlamaClient] = None

        # RAG Context Injector (lazy loaded)
        self._rag_injector: Optional[Any] = None
        self._rag_enabled: bool = True

        # Tool Caller (lazy loaded)
        self._tool_caller: Any = None
        self._tools_enabled: bool = True

        logger.info(
            f"Brain initialized: default_model={self._default_model}, n_ctx={n_ctx}"
        )

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model name from alias or default.

        Args:
            model: Model name or alias

        Returns:
            Resolved model name
        """
        if model is None:
            return self._default_model
        return MODEL_ALIASES.get(model, model)

    @property
    def rag_injector(self) -> Optional[Any]:
        """Lazy-load RAG context injector."""
        global _RAGInjector
        if self._rag_injector is None and _RAGInjector is None:
            try:
                from packages.local_llm.rag_injector import RAGContextInjector

                _RAGInjector = RAGContextInjector
                self._rag_injector = _RAGInjector()
                logger.info("RAG context injector loaded successfully")
            except Exception as e:
                logger.warning(f"RAG injector unavailable: {e}")
                self._rag_injector = None
        elif self._rag_injector is None and _RAGInjector is not None:
            self._rag_injector = _RAGInjector()
        return self._rag_injector

    def enable_rag(self, enabled: bool = True):
        """Enable or disable RAG context injection."""
        self._rag_enabled = enabled
        logger.info(f"RAG {'enabled' if enabled else 'disabled'}")

    @property
    def tool_caller(self):
        """Lazy-load ToolCaller for native tool calling."""
        global _ToolCaller
        if self._tool_caller is None and _ToolCaller is None:
            try:
                from packages.local_llm.tool_caller import (
                    ToolCaller,
                    create_search_tool,
                )

                _ToolCaller = ToolCaller
                # Create instance with RAG integration
                self._tool_caller = _ToolCaller()
                # Add search tool if RAG available
                if self.rag_injector:
                    create_search_tool(self.rag_injector)
                logger.info("Tool caller loaded successfully")
            except Exception as e:
                logger.warning(f"Tool caller unavailable: {e}")
                self._tool_caller = None
        elif self._tool_caller is None and _ToolCaller is not None:
            self._tool_caller = _ToolCaller()
        return self._tool_caller

    def enable_tools(self, enabled: bool = True):
        """Enable or disable tool calling."""
        self._tools_enabled = enabled
        logger.info(f"Tools {'enabled' if enabled else 'disabled'}")

    def _load_client(self, model_name: str) -> DirectLlamaClient:
        """Load or get client for model.

        Args:
            model_name: Resolved model name

        Returns:
            DirectLlamaClient instance
        """
        # Check if already loaded
        if model_name in self._model_pool:
            self._model_timestamps[model_name] = time.time()
            return self._model_pool[model_name]

        # Check VRAM
        if not check_vram_available(model_name):
            logger.warning(f"Insufficient VRAM for {model_name}, trying anyway...")

        # Load model
        model_path = get_model_path(model_name)
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Check if this is an embedding model
        is_embedding = model_name in (EMBED_MODEL, "embed", "embedding", "nomic")

        # Use smaller context for embedding model
        n_ctx = 512 if is_embedding else self.n_ctx

        logger.info(f"Loading model: {model_name}")
        client = DirectLlamaClient(
            model_path=str(model_path),
            n_gpu_layers=self.n_gpu_layers,
            n_ctx=n_ctx,
            verbose=False,
            embedding=is_embedding,
        )

        # Cache
        self._model_pool[model_name] = client
        self._model_timestamps[model_name] = time.time()

        return client

    def _cleanup_idle_models(self):
        """Unload models that have been idle too long."""
        now = time.time()
        idle_models = [
            name
            for name, last_used in self._model_timestamps.items()
            if now - last_used > self.unload_timeout
        ]

        for name in idle_models:
            if name in self._model_pool:
                del self._model_pool[name]
            if name in self._model_timestamps:
                del self._model_timestamps[name]

            # Unload active if matching
            if self._active_model == name:
                self._active_client = None
                self._active_model = None

            logger.info(f"Unloaded idle model: {name}")

    def _set_active(self, model_name: str):
        """Set active model.

        Args:
            model_name: Model to make active
        """
        # Cleanup idle first
        self._cleanup_idle_models()

        # Load client
        client = self._load_client(model_name)

        self._active_model = model_name
        self._active_client = client

    # ============================================================================
    # Public API
    # ============================================================================

    def complete(
        self,
        prompt: str,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> Dict[str, Any]:
        """Text completion.

        Args:
            prompt: User prompt
            model: Model to use (None = default)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional generation parameters

        Returns:
            Dict with {text, tokens, timing_ms}
        """
        model_name = self._resolve_model(model)
        start_time = time.time()

        # Ensure model loaded
        if self._active_model != model_name:
            self._set_active(model_name)

        client = self._active_client

        # Generate using simple prompt format
        response = client.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "text": response,
            "tokens": len(response.split()),
            "timing_ms": round(elapsed_ms, 2),
        }

    def chat(
        self,
        messages: list,
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
        use_rag: bool = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Chat completion.

        Args:
            messages: List[Dict] with message dicts {"role": "...", "content": "..."}
            model: Model to use (None = default)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            use_rag: Enable RAG context injection (default: self._rag_enabled)
            **kwargs: Additional generation parameters

        Returns:
            Dict with {text, tokens, timing_ms, tool_calls}
        """
        # Determine RAG usage
        use_rag = use_rag if use_rag is not None else self._rag_enabled

        # Apply RAG context injection if enabled and we have messages
        processed_messages = messages
        if use_rag and messages and self.rag_injector:
            try:
                # Get the last user message for RAG query
                last_msg = messages[-1]
                if last_msg.get("role") == "user":
                    query = last_msg.get("content", "")
                    enhanced_query = self.rag_injector.inject_context(query)
                    # Create new messages with enhanced query
                    processed_messages = messages[:-1] + [
                        {**last_msg, "content": enhanced_query}
                    ]
                    logger.debug(f"RAG enhanced query: {len(enhanced_query)} chars")
            except Exception as e:
                logger.warning(f"RAG injection failed: {e}, using original query")

        model_name = self._resolve_model(model)
        start_time = time.time()

        # Ensure model loaded
        if self._active_model != model_name:
            self._set_active(model_name)

        client = self._active_client

        # Format messages for llama-cpp-python
        formatted_messages = []
        for msg in processed_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_messages.append({"role": role, "content": content})

        # Generate
        response = client.generate(
            prompt=self._format_chat_prompt(formatted_messages),
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "text": response,
            "tokens": len(response.split()),
            "timing_ms": round(elapsed_ms, 2),
            "tool_calls": None,  # Tool calling via direct_pipeline
            "rag_used": use_rag and self.rag_injector is not None,
        }

    def _format_chat_prompt(self, messages: list) -> str:
        """Format chat messages as prompt.

        Args:
            messages: List of message dicts

        Returns:
            Formatted prompt string
        """
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"

        prompt += "Assistant:"
        return prompt

    def embed(self, text: str, model: str = None) -> Dict[str, Any]:
        """Generate embeddings.

        Args:
            text: Text to embed
            model: Embedding model (None = use embed model)

        Returns:
            Dict with {embedding: list, timing_ms}
        """
        embed_model = self._resolve_model(model) if model else EMBED_MODEL
        start_time = time.time()

        # Ensure embed model loaded
        if self._active_model != embed_model:
            self._set_active(embed_model)

        client = self._active_client

        # Generate embedding
        try:
            embedding = client.embed(text)
        except NotImplementedError:
            # Fallback: simple token-based embedding
            embedding = [hash(c) / 1000000 for c in text[:512]]

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "embedding": embedding,
            "timing_ms": round(elapsed_ms, 2),
        }

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        use_tools: bool = None,
        use_rag: bool = None,
    ) -> Dict[str, Any]:
        """Chat completion with tool calling support.

        This uses the Frankenstein approach - direct llama-cpp-python (DirectLlamaClient).

        Args:
            messages: List[Dict] with message dicts
            use_tools: Enable tool calling (default: self._tools_enabled)
            use_rag: Enable RAG (default: self._rag_enabled)

        Returns:
            Dict with {text, tool_calls, iterations, timing_ms}
        """
        # Determine settings
        use_tools = use_tools if use_tools is not None else self._tools_enabled
        use_rag = use_rag if use_rag is not None else self._rag_enabled

        # Apply RAG if enabled
        processed_messages = messages
        if use_rag and messages and self.rag_injector:
            try:
                last_msg = messages[-1]
                if last_msg.get("role") == "user":
                    query = last_msg.get("content", "")
                    enhanced_query = self.rag_injector.inject_context(query)
                    processed_messages = messages[:-1] + [
                        {**last_msg, "content": enhanced_query}
                    ]
            except Exception as e:
                logger.warning(f"RAG injection failed: {e}")

        # Use tool caller if enabled
        if use_tools and self.tool_caller:
            try:
                result = await self.tool_caller.chat_with_tools(processed_messages)
                result["rag_used"] = use_rag and self.rag_injector is not None
                result["tools_used"] = True
                return result
            except Exception as e:
                logger.warning(
                    f"Tool calling failed: {e}, falling back to regular chat"
                )

        # Fallback to regular chat
        return self.chat(processed_messages, use_rag=False)

    def set_model(self, model: str):
        """Manually set active model.

        Args:
            model: Model name or alias ("7b", "0.5b", "embed")
        """
        model_name = self._resolve_model(model)
        self._set_active(model_name)
        logger.info(f"Set active model: {model_name}")

    def get_status(self) -> Dict[str, Any]:
        """Get brain status.

        Returns:
            Dict with {loaded_model, available_models, vram_usage, rag_status}
        """
        vram = get_vram_usage()

        return {
            "loaded_model": self._active_model,
            "default_model": self._default_model,
            "available_models": list(MODEL_ALIASES.keys()),
            "pooled_models": list(self._model_pool.keys()),
            "vram_usage": {
                "total_mb": vram["total_mb"],
                "used_mb": vram["used_mb"],
                "available_mb": vram["available_mb"],
            },
            "rag_enabled": self._rag_enabled,
            "rag_available": self.rag_injector is not None,
            "tools_enabled": self._tools_enabled,
            "tools_available": self.tool_caller is not None,
        }

    # ============================================================================
    # Trigger Guardian Integration
    # ============================================================================

    def process_trigger(self, user_input: str) -> Dict[str, Any]:
        """Process user input using Rosetta to extract trigger actions.

        Uses the 0.5B Rosetta model to convert natural language into
        structured trigger/tool actions. This is the "direct hook" -
        no HTTP, no external services, 100% local.

        Args:
            user_input: Natural language input from user

        Returns:
            Dict with {action, tool, args, confidence}
        """
        # Use Rosetta model for trigger detection
        rosetta_prompt = (
            """You are a trigger classifier. Given user input, classify it as:

1. TRIGGER: User wants to invoke a registered trigger (like /start-work, /refactor)
2. TOOL: User wants to execute a specific tool
3. MESSAGE: User wants to have a conversation

Respond with JSON:
{"type": "TRIGGER|TOOL|MESSAGE", "action": "action_name", "args": {}}

User input: """
            + user_input
            + """

Response:"""
        )

        # Use 0.5B fast model for trigger classification
        result = self.complete(
            prompt=rosetta_prompt,
            model="rosetta",
            temperature=0.1,
            max_tokens=256,
        )

        # Parse the response
        try:
            import json

            # Try to extract JSON from response
            text = result.get("text", "")
            # Find JSON in response
            import re

            json_match = re.search(r"\{[^}]+\}", text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "type": parsed.get("type", "MESSAGE"),
                    "action": parsed.get("action", ""),
                    "args": parsed.get("args", {}),
                    "confidence": 0.8,
                    "raw": text,
                }
        except Exception as e:
            logger.warning(f"Failed to parse trigger response: {e}")

        # Fallback: return as message
        return {
            "type": "MESSAGE",
            "action": "",
            "args": {},
            "confidence": 0.0,
            "raw": result.get("text", ""),
        }

    def execute_tool_action(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool action using the brain.

        Uses the 7B reasoner for complex tool execution,
        or 0.5B for simple actions.

        Args:
            action: Tool/action name
            args: Arguments for the action

        Returns:
            Dict with {result, tool_calls, timing_ms}
        """
        if not action:
            return {"error": "No action specified"}

        # Select model based on action complexity
        # Simple actions → 0.5B, Complex → 7B
        complex_actions = {
            "refactor",
            "implement",
            "create",
            "build",
            "analyze",
            "debug",
        }
        model = "7b" if action.lower() in complex_actions else "rosetta"

        # Build prompt
        tool_prompt = f"""Execute the following action: {action}
With arguments: {json.dumps(args)}

Provide the result in JSON format:
{{"success": true/false, "output": "...", "error": "..."}}"""

        result = self.complete(
            prompt=tool_prompt,
            model=model,
            temperature=0.3,
            max_tokens=1024,
        )

        return {
            "action": action,
            "args": args,
            "result": result.get("text", ""),
            "timing_ms": result.get("timing_ms", 0),
        }

    def think(self, prompt: str, mode: str = "fast") -> Dict[str, Any]:
        """Main thinking interface - the brain's primary entry point.

        This is the "direct hook" - inline brain calls with zero overhead.

        Args:
            prompt: What to think about
            mode: "fast" (0.5B), "smart" (7B), "auto" (router decides)

        Returns:
            Dict with {response, model_used, timing_ms}
        """
        import time

        start = time.time()

        # Select model based on mode
        if mode == "fast":
            model = "rosetta"
        elif mode == "smart":
            model = "7b"
        else:  # auto
            # Use 7B for most tasks, 0.5B for simple ones
            simple_patterns = {"what is", "list", "show", "get", "find"}
            is_simple = any(prompt.lower().startswith(p) for p in simple_patterns)
            model = "rosetta" if is_simple else "7b"

        result = self.complete(prompt=prompt, model=model, temperature=0.7)

        elapsed_ms = (time.time() - start) * 1000

        return {
            "response": result.get("text", ""),
            "model_used": model,
            "timing_ms": round(elapsed_ms, 2),
        }

    def embed_text(self, text: str) -> Dict[str, Any]:
        """Generate embeddings for text - 1.67x faster than Ollama.

        Args:
            text: Text to embed

        Returns:
            Dict with {embedding: list, timing_ms}
        """
        return self.embed(text)


# ============================================================================
# Convenience Functions
# ============================================================================

_brain_instance: Optional[Brain] = None


def get_brain(default_model: str = "auto") -> Brain:
    """Get or create global Brain instance.

    Args:
        default_model: Default model

    Returns:
        Brain singleton
    """
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = Brain(default_model=default_model)
    return _brain_instance


def complete(prompt: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for text completion.

    Args:
        prompt: User prompt
        **kwargs: Additional parameters

    Returns:
        Dict with {text, tokens, timing_ms}
    """
    return get_brain().complete(prompt, **kwargs)


def chat(messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
    """Convenience function for chat completion.

    Args:
        messages: Chat history
        **kwargs: Additional parameters

    Returns:
        Dict with {text, tokens, timing_ms, tool_calls}
    """
    return get_brain().chat(messages, **kwargs)


def embed(text: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for embeddings.

    Args:
        text: Text to embed
        **kwargs: Additional parameters

    Returns:
        Dict with {embedding: list, timing_ms}
    """
    return get_brain().embed(text, **kwargs)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    # Test brain
    brain = Brain()

    print("=== Brain Status ===")
    print(brain.get_status())

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])

        print(f"\n=== Complete: {prompt} ===")
        result = brain.complete(prompt)
        print(f"Result: {result}")
    else:
        print("\n=== Test complete ===")
        result = brain.complete("Hello! How are you?")
        print(f"Result: {result}")

        print("\n=== Test chat ===")
        result = brain.chat([{"role": "user", "content": "Hello!"}])
        print(f"Result: {result}")

        print("\n=== Test embed ===")
        result = brain.embed("Your text here")
        print(f"Embedding dim: {len(result['embedding'])}")
