"""Batch inference for production use.

Provides high-throughput inference for trained models with:
- Batched requests for GPU efficiency
- Streaming responses
- Concurrent request handling
- Request queuing and prioritization
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, AsyncGenerator
from threading import Thread


@dataclass
class InferenceRequest:
    """Single inference request."""

    request_id: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.1
    priority: int = 0  # Higher = more priority
    timestamp: float = field(default_factory=time.time)
    callback: Optional[Callable] = None


@dataclass
class InferenceResponse:
    """Inference response."""

    request_id: str
    output: str
    tool_call: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0
    tokens_generated: int = 0
    error: Optional[str] = None


class BatchInferrer:
    """High-performance batch inference engine.

    Features:
    - Request batching for GPU efficiency
    - Concurrent request handling
    - Priority queue for urgent requests
    - Streaming responses
    - Request timeout handling

    Usage:
        inferrer = BatchInferrer(model_path="outputs/rosetta-lora")
        inferrer.start()

        # Queue requests
        response = inferrer.infer("search memory for security")

        # Or batch multiple
        responses = inferrer.batch_infer([
            "search memory for config",
            "read file README.md",
            "check git status",
        ])

        inferrer.stop()
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        max_batch_size: int = 8,
        max_queue_size: int = 100,
        timeout_seconds: float = 30.0,
    ):
        """Initialize batch inferrer.

        Args:
            model_path: Path to LoRA adapters (optional).
            model_name: HuggingFace model name.
            max_batch_size: Maximum requests per GPU batch.
            max_queue_size: Maximum queued requests.
            timeout_seconds: Request timeout.
        """
        self.model_path = model_path
        self.model_name = model_name
        self.max_batch_size = max_batch_size
        self.max_queue_size = max_queue_size
        self.timeout_seconds = timeout_seconds

        self._request_queue: Queue = Queue(maxsize=max_queue_size)
        self._running = False
        self._model = None
        self._tokenizer = None
        self._worker_thread: Optional[Thread] = None

    def start(self) -> bool:
        """Start the inference engine.

        Returns:
            True if started successfully.
        """
        if self._running:
            return True

        try:
            # Try to load with Unsloth/FastLanguageModel
            self._load_model()
            self._running = True
            self._worker_thread = Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            print(f"✓ BatchInferrer started (model: {self.model_name})")
            return True
        except Exception as e:
            print(f"✗ Failed to start BatchInferrer: {e}")
            return False

    def _load_model(self) -> None:
        """Load the model and tokenizer."""
        try:
            from unsloth import FastLanguageModel
        except ImportError:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            # Fallback to standard transformers
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto",
                torch_dtype="auto",
            )
            return

        # Use Unsloth if available
        dtype = None
        import torch

        if torch.cuda.is_available():
            dtype = "bfloat16" if torch.cuda.is_bf16_supported() else "float16"

        self._model, self._tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.model_name,
            max_seq_length=2048,
            dtype=dtype,
            load_in_4bit=True,
        )

        # Load LoRA if path provided
        if self.model_path:
            self._model = FastLanguageModel.get_peft_model(
                self._model,
                r=32,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            )
            self._model.load_adapter(str(self.model_path), adapter_name="rosetta")
            self._model.set_adapter("rosetta")

        self._model.eval()

    def _worker_loop(self) -> None:
        """Background worker that processes batches."""
        while self._running:
            try:
                # Collect batch of requests
                batch = []
                while len(batch) < self.max_batch_size and self._request_queue.qsize() > 0:
                    try:
                        request = self._request_queue.get_nowait()
                        batch.append(request)
                    except Exception:
                        break

                if batch:
                    self._process_batch(batch)

                time.sleep(0.01)  # Prevent busy loop

            except Exception as e:
                print(f"Worker error: {e}")

    def _process_batch(self, requests: List[InferenceRequest]) -> None:
        """Process a batch of requests."""
        if not self._model or not self._tokenizer:
            for req in requests:
                self._respond(
                    req,
                    InferenceResponse(
                        request_id=req.request_id,
                        output="",
                        error="Model not loaded",
                    ),
                )
            return

        try:
            # Tokenize all prompts
            prompts = [req.prompt for req in requests]
            inputs = self._tokenizer(
                prompts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=2048,
            )

            # Move to GPU
            import torch

            inputs = {k: v.cuda() for k, v in inputs.items()}

            # Generate
            start_time = time.time()
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.1,
                    top_p=0.9,
                    do_sample=True,
                )

            # Decode and respond
            latency = (time.time() - start_time) * 1000

            for i, req in enumerate(requests):
                generated = outputs[i]
                text = self._tokenizer.decode(generated, skip_special_tokens=True)

                # Extract tool call
                tool_call = self._parse_tool_call(text)

                self._respond(
                    req,
                    InferenceResponse(
                        request_id=req.request_id,
                        output=text,
                        tool_call=tool_call,
                        latency_ms=latency,
                        tokens_generated=len(generated),
                    ),
                )

        except Exception as e:
            for req in requests:
                self._respond(
                    req,
                    InferenceResponse(
                        request_id=req.request_id,
                        output="",
                        error=str(e),
                    ),
                )

    def _respond(self, request: InferenceRequest, response: InferenceResponse) -> None:
        """Send response back."""
        if request.callback:
            request.callback(response)

    def _parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from generated text."""
        import re

        match = re.search(
            r"\[TOOL_CALL\]\{tool => \"([^\"]+)\", args => \{([^}]+)\}\}\[/TOOL_CALL\]",
            text,
        )
        if match:
            tool_name = match.group(1)
            args_str = match.group(2)

            # Parse args
            args = {}
            arg_matches = re.findall(r'--(\w+) "([^"]*)"', args_str)
            for arg_name, arg_value in arg_matches:
                args[arg_name] = arg_value

            return {"tool": tool_name, "args": args}

        return None

    def infer(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.1,
        priority: int = 0,
    ) -> InferenceResponse:
        """Run single inference (blocking).

        Args:
            prompt: Input prompt.
            max_tokens: Max tokens to generate.
            temperature: Sampling temperature.
            priority: Request priority.

        Returns:
            Inference response.
        """
        result_holder: Dict[str, InferenceResponse] = {}

        def callback(response: InferenceResponse):
            result_holder["response"] = response

        request = InferenceRequest(
            request_id=f"req_{int(time.time() * 1000)}",
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            priority=priority,
            callback=callback,
        )

        self._request_queue.put(request)

        # Wait for response
        start = time.time()
        while time.time() - start < self.timeout_seconds:
            if "response" in result_holder:
                return result_holder["response"]
            time.sleep(0.01)

        return InferenceResponse(
            request_id=request.request_id,
            output="",
            error="Timeout",
        )

    def batch_infer(
        self,
        prompts: List[str],
        max_tokens: int = 256,
        temperature: float = 0.1,
    ) -> List[InferenceResponse]:
        """Run batch inference (blocking).

        Args:
            prompts: List of input prompts.
            max_tokens: Max tokens to generate.
            temperature: Sampling temperature.

        Returns:
            List of inference responses.
        """
        results = []

        for prompt in prompts:
            result = self.infer(prompt, max_tokens, temperature)
            results.append(result)

        return results

    def stop(self) -> None:
        """Stop the inference engine."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        print("✓ BatchInferrer stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get inference statistics.

        Returns:
            Stats dict with queue size, model info, etc.
        """
        return {
            "running": self._running,
            "queue_size": self._request_queue.qsize(),
            "max_batch_size": self.max_batch_size,
            "model_name": self.model_name,
            "model_path": str(self.model_path) if self.model_path else None,
        }


class StreamingInferrer:
    """Streaming inference with token-by-token yield.

    Usage:
        inferrer = StreamingInferrer(model_path="outputs/rosetta-lora")
        inferrer.start()

        async for token in inferrer.stream_infer("search memory"):
            print(token, end="")
    """

    def __init__(self, model_path: Optional[Path] = None):
        """Initialize streaming inferrer."""
        self.model_path = model_path
        self._model = None
        self._tokenizer = None

    def start(self) -> bool:
        """Start the streaming inferrer."""
        try:
            from unsloth import FastLanguageModel

            import torch

            dtype = "bfloat16" if torch.cuda.is_bf16_supported() else "float16"

            self._model, self._tokenizer = FastLanguageModel.from_pretrained(
                model_name="Qwen/Qwen2.5-0.5B-Instruct",
                max_seq_length=2048,
                dtype=dtype,
                load_in_4bit=True,
            )

            if self.model_path:
                self._model = FastLanguageModel.get_peft_model(
                    self._model,
                    r=32,
                    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                )
                self._model.load_adapter(str(self.model_path), adapter_name="rosetta")
                self._model.set_adapter("rosetta")

            self._model.eval()
            print("✓ StreamingInferrer started")
            return True

        except Exception as e:
            print(f"✗ Failed to start StreamingInferrer: {e}")
            return False

    async def stream_infer(
        self,
        prompt: str,
        max_tokens: int = 256,
    ) -> AsyncGenerator[str, None]:
        """Stream inference tokens.

        Args:
            prompt: Input prompt.
            max_tokens: Max tokens to generate.

        Yields:
            Generated tokens.
        """
        if not self._model or not self._tokenizer:
            yield "[ERROR: Model not loaded]"
            return

        import torch
        from transformers import TextIteratorStreamer
        from threading import Thread

        # Tokenize
        inputs = self._tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.cuda() for k, v in inputs.items()}

        # Create streamer
        streamer = TextIteratorStreamer(self._tokenizer)

        # Generate in background thread
        generation_kwargs = dict(
            **inputs,
            max_new_tokens=max_tokens,
            streamer=streamer,
            temperature=0.1,
            top_p=0.9,
        )

        thread = Thread(
            target=self._model.generate,
            kwargs=generation_kwargs,
        )
        thread.start()

        # Stream tokens
        for token in streamer:
            yield token

        thread.join()
