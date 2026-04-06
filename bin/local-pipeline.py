#!/usr/bin/env python3
"""Local Pipeline - Multi-step pipeline orchestrator for local LLM chains."""

import argparse
import json
import sys
from typing import Any, Optional

try:
    import requests
except ImportError:
    requests = None


POOR_QUALITY_KEYWORDS = [
    "i don't know",
    "unable to",
    "cannot",
    "can't",
    "error",
    "failed",
    "exception",
]
MIN_RESPONSE_LENGTH = 10


class LocalRouter:
    """Router for local LLM operations - simplified for pipeline use."""

    DEFAULT_OLLAMA_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2:3b"
    HEALTH_ENDPOINT = "/api/version"
    GENERATE_ENDPOINT = "/api/generate"

    def __init__(self, ollama_url: Optional[str] = None):
        self.ollama_url = ollama_url or self.DEFAULT_OLLAMA_URL
        self.default_model = self.DEFAULT_MODEL

    def is_available(self, timeout: float = 2.0) -> bool:
        """Check if Ollama is running."""
        if requests is None:
            return False
        try:
            response = requests.get(
                f"{self.ollama_url}{self.HEALTH_ENDPOINT}", timeout=timeout
            )
            return response.status_code == 200
        except (requests.RequestException, requests.Timeout):
            return False

    def generate(
        self, prompt: str, model: Optional[str] = None, timeout: float = 120.0
    ) -> dict:
        """Generate response from local model."""
        if requests is None:
            return {"success": False, "error": "requests library not available"}

        model = model or self.default_model
        try:
            response = requests.post(
                f"{self.ollama_url}{self.GENERATE_ENDPOINT}",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=timeout,
            )
            if response.status_code == 200:
                return {
                    "success": True,
                    "response": response.json().get("response", ""),
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except requests.Timeout:
            return {"success": False, "error": "Request timeout"}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}


class PipelineRunner:
    """Executes multi-step pipelines using local models with pass/fail routing."""

    def __init__(self, local_router: Optional[LocalRouter] = None):
        self.router = local_router or LocalRouter()

    def assess_quality(self, response: str) -> bool:
        """Assess if response quality is good using heuristics."""
        if not response or len(response.strip()) < MIN_RESPONSE_LENGTH:
            return False

        response_lower = response.lower()
        for keyword in POOR_QUALITY_KEYWORDS:
            if keyword in response_lower:
                return False

        return True

    def execute_step(
        self, step: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single pipeline step."""
        task = step.get("task", "")
        model = step.get("model")

        if not task:
            return {"success": False, "error": "Empty task"}

        full_prompt = task
        if context.get("previous_output"):
            full_prompt = (
                f"Previous context: {context['previous_output']}\n\nTask: {task}"
            )

        result = self.router.generate(full_prompt, model=model)

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Generation failed"),
                "step": step,
            }

        response = result.get("response", "")
        quality = self.assess_quality(response)

        return {"success": True, "response": response, "quality": quality, "step": step}

    def execute_pipeline(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Execute sequential pipeline with pass/fail routing."""
        results = []
        context = {"previous_output": None}

        for i, step in enumerate(steps):
            depends_on = step.get("depends_on")
            if depends_on and i > 0:
                if not results:
                    return {
                        "success": False,
                        "error": f"Step depends on '{depends_on}' but no prior results",
                    }

            step_result = self.execute_step(step, context)
            results.append(step_result)

            if step_result.get("success"):
                context["previous_output"] = step_result.get("response", "")
            else:
                return {
                    "success": False,
                    "error": f"Step {i + 1} failed: {step_result.get('error')}",
                    "failed_step": i,
                    "results": results,
                }

            if step_result.get("success") and not step_result.get("quality", True):
                continue

        return {"success": True, "results": results, "context": context}


def load_steps_from_file(path: str) -> list[dict[str, Any]]:
    """Load pipeline steps from JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "steps" in data:
        return data["steps"]
    raise ValueError("Invalid JSON format - expected array or object with 'steps' key")


def format_results(results: dict, output_format: str) -> str:
    """Format pipeline results for output."""
    if output_format == "json":
        return json.dumps(results, indent=2)
    else:
        lines = []
        if results.get("success"):
            lines.append("Pipeline completed successfully")
        else:
            lines.append(f"Pipeline failed: {results.get('error', 'Unknown error')}")

        for i, result in enumerate(results.get("results", [])):
            status = "PASS" if result.get("success") else "FAIL"
            quality = result.get("quality", True)
            if result.get("success"):
                response = result.get("response", "")[:100]
                lines.append(
                    f"  Step {i + 1}: {status} (quality: {'OK' if quality else 'POOR'})"
                )
                lines.append(f"    Response: {response}...")
            else:
                lines.append(f"  Step {i + 1}: {status}")
                lines.append(f"    Error: {result.get('error')}")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Multi-step pipeline orchestrator for local LLM chains"
    )
    parser.add_argument(
        "--steps",
        type=str,
        help='JSON array of steps (e.g., \'[{"task": "step1"}, {"task": "step2"}]\')',
    )
    parser.add_argument("--file", type=str, help="Load steps from JSON file")
    parser.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show pipeline without executing"
    )

    args = parser.parse_args()

    steps = []
    if args.steps:
        try:
            steps = json.loads(args.steps)
        except json.JSONDecodeError as e:
            print(f"Error parsing --steps: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.file:
        try:
            steps = load_steps_from_file(args.file)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    if args.dry_run:
        print("Pipeline dry-run:")
        print(json.dumps(steps, indent=2))
        sys.exit(0)

    router = LocalRouter()
    if not router.is_available():
        print("Warning: Ollama is not available, pipeline may fail", file=sys.stderr)

    runner = PipelineRunner(local_router=router)
    results = runner.execute_pipeline(steps)

    print(format_results(results, args.format))

    sys.exit(0 if results.get("success") else 1)


if __name__ == "__main__":
    main()
