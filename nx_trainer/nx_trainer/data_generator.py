"""Training data generator for Rosetta Stone.

Generates diverse training data for tool call translation with:
- Multiple templates per tool category
- Random sampling for variation
- Edge case handling
- Phrase variety for natural language patterns
"""

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from nx_trainer.config import DEFAULT_TOOLS


class DataGenerator:
    """Generate training data for tool call translation.

    Creates pairs of simple user requests mapped to MCP tool calls.
    """

    # Expanded phrase variations for more natural training data
    PHRASE_VARIATIONS = {
        "search_memory": [
            "search memory for {}",
            "look up {} in memory",
            "find {} in memory",
            "remember anything about {}",
            "search for {} in my memory",
            "retrieve info about {} from memory",
            "find memories containing {}",
            "query memory for {}",
            "look for {} in stored memories",
        ],
        "memory_write": [
            "remember {}",
            "store {}",
            "memorize {}",
            "save to memory {}",
            "remember that {}",
            "save this: {}",
            "note: {}",
            "keep in mind: {}",
            "record: {}",
        ],
        "file_read": [
            "read {}",
            "show me {}",
            "display {}",
            "open {}",
            "view {}",
            "cat {}",
            "get contents of {}",
            "show contents of {}",
            "load {}",
        ],
        "file_write": [
            "write {} to {}",
            "save {} to {}",
            "create {} with {}",
            "write {} in {}",
            "save content {} to {}",
            "output {} to {}",
        ],
        "list_dir": [
            "list files in {}",
            "show files in {}",
            "ls {}",
            "what's in {}",
            "list directory {}",
            "show me {}",
            "files in {}",
            "directory listing for {}",
        ],
        "git_status": [
            "check git status",
            "git status",
            "show repo status",
            "what's changed",
            "modified files",
            "check status",
        ],
        "git_log": [
            "show git log",
            "git log",
            "recent commits",
            "commit history",
            "show commits",
            "what commits",
        ],
        "fetch": [
            "fetch {}",
            "get {}",
            "retrieve {}",
            "download {}",
            "grab {}",
            "fetch content from {}",
        ],
        "navigate": [
            "open {}",
            "go to {}",
            "navigate to {}",
            "visit {}",
            "browse {}",
            "load {}",
        ],
    }

    def __init__(self, tools: Optional[Dict[str, Dict[str, str]]] = None):
        """Initialize the data generator.

        Args:
            tools: Dictionary of tool names to their parameter types.
                   Defaults to DEFAULT_TOOLS if not provided.
        """
        self.tools = tools or DEFAULT_TOOLS
        self._templates = self._build_templates()

    def _build_templates(self) -> List[Dict[str, Any]]:
        """Build template combinations for data generation.

        Expanded with:
        - More phrase variations per tool
        - Edge case templates (empty args, multiple args, etc.)
        - Synonym variations for natural language
        """
        templates = []

        # === Memory tools ===
        templates.extend(
            [
                # Primary templates
                ("search memory for {query}", "memory_search", {"query": "{query}", "limit": 10}),
                ("look up {query} in memory", "memory_search", {"query": "{query}"}),
                ("find info about {query}", "memory_search", {"query": "{query}", "limit": 5}),
                # Variations
                (
                    "remember {content}",
                    "memory_write",
                    {"content": "{content}", "kind": "episodic"},
                ),
                (
                    "store {content} in memory",
                    "memory_write",
                    {"content": "{content}", "kind": "semantic"},
                ),
                ("note: {content}", "memory_write", {"content": "{content}", "kind": "note"}),
            ]
        )

        # === Search tools ===
        templates.extend(
            [
                ("find info about {query}", "athena_smart_search", {"query": "{query}"}),
                ("search for {query}", "athena_smart_search", {"query": "{query}"}),
                ("look up {query}", "athena_smart_search", {"query": "{query}"}),
            ]
        )

        # === File tools ===
        templates.extend(
            [
                # Read operations
                ("read {path}", "read_file", {"path": "{path}"}),
                ("show me {path}", "read_file", {"path": "{path}"}),
                ("display {path}", "read_file", {"path": "{path}"}),
                ("view {path}", "read_file", {"path": "{path}"}),
                # Write operations
                (
                    "write {content} to {path}",
                    "write_file",
                    {"path": "{path}", "content": "{content}"},
                ),
                (
                    "save {content} to {path}",
                    "write_file",
                    {"path": "{path}", "content": "{content}"},
                ),
                (
                    "create {path} with {content}",
                    "write_file",
                    {"path": "{path}", "content": "{content}"},
                ),
                # Directory operations
                ("list files in {path}", "list_directory", {"path": "{path}"}),
                ("show files in {path}", "list_directory", {"path": "{path}"}),
                ("ls {path}", "list_directory", {"path": "{path}"}),
                ("what's in {path}", "list_directory", {"path": "{path}"}),
            ]
        )

        # === Git tools ===
        templates.extend(
            [
                # Status variations
                ("check git status", "git_status", {"repo_path": "."}),
                ("git status", "git_status", {"repo_path": "."}),
                ("show repo status", "git_status", {"repo_path": "."}),
                ("what's changed", "git_status", {"repo_path": "."}),
                # Log variations
                ("show git log", "git_log", {"repo_path": ".", "max_count": 10}),
                ("git log", "git_log", {"repo_path": ".", "max_count": 10}),
                ("recent commits", "git_log", {"repo_path": ".", "max_count": 5}),
                ("commit history", "git_log", {"repo_path": ".", "max_count": 20}),
                # Diff variations
                ("show diff", "git_diff", {"repo_path": ".", "target": "HEAD"}),
                ("git diff", "git_diff", {"repo_path": ".", "target": "HEAD"}),
                ("show changes", "git_diff", {"repo_path": ".", "target": "HEAD~1"}),
            ]
        )

        # === GitHub tools ===
        templates.extend(
            [
                (
                    "list issues for {owner}/{repo}",
                    "github_list_issues",
                    {"owner": "{owner}", "repo": "{repo}"},
                ),
                (
                    "show issues for {owner}/{repo}",
                    "github_list_issues",
                    {"owner": "{owner}", "repo": "{repo}", "state": "open"},
                ),
                (
                    "find issues in {owner}/{repo}",
                    "github_list_issues",
                    {"owner": "{owner}", "repo": "{repo}"},
                ),
                # Additional GitHub operations
                (
                    "search code in {owner}/{repo}",
                    "github_search_code",
                    {"owner": "{owner}", "repo": "{repo}", "q": "test"},
                ),
            ]
        )

        # === Web tools ===
        templates.extend(
            [
                # Fetch operations
                ("fetch {url}", "fetch_url", {"url": "{url}", "format": "markdown"}),
                ("get {url}", "fetch_url", {"url": "{url}", "format": "text"}),
                ("retrieve {url}", "fetch_url", {"url": "{url}"}),
                # Browser operations
                ("open {url}", "browser_navigate", {"url": "{url}"}),
                ("go to {url}", "browser_navigate", {"url": "{url}"}),
                ("navigate to {url}", "browser_navigate", {"url": "{url}"}),
                # Documentation
                (
                    "get docs for {lib}",
                    "context7_query_docs",
                    {"library_id": "/{lib}", "query": "basics"},
                ),
                (
                    "query {lib} docs",
                    "context7_query_docs",
                    {"library_id": "/{lib}", "query": "api"},
                ),
            ]
        )

        # === Thinking tools ===
        templates.extend(
            [
                (
                    "think about {problem}",
                    "sequential_thinking",
                    {
                        "thought": "{problem}",
                        "nextThoughtNeeded": "True",
                        "thoughtNumber": 1,
                        "totalThoughts": 3,
                    },
                ),
                (
                    "reason through {problem}",
                    "sequential_thinking",
                    {
                        "thought": "{problem}",
                        "nextThoughtNeeded": "True",
                        "thoughtNumber": 1,
                        "totalThoughts": 5,
                    },
                ),
                (
                    "analyze {problem}",
                    "sequential_thinking",
                    {
                        "thought": "{problem}",
                        "nextThoughtNeeded": "True",
                        "thoughtNumber": 1,
                        "totalThoughts": 4,
                    },
                ),
            ]
        )

        # === Context/System tools ===
        templates.extend(
            [
                # Context operations
                ("what's the active context", "get_active_context", {}),
                ("get active context", "get_active_context", {}),
                ("show current context", "get_active_context", {}),
                ("health check", "get_health", {"level": "l0"}),
                ("check system health", "get_health", {"level": "l1"}),
                ("deep health check", "get_health", {"level": "l2"}),
            ]
        )

        # === Routing tools ===
        templates.extend(
            [
                ("route task: {task}", "route_task", {"task_description": "{task}"}),
                ("delegate: {task}", "route_task", {"task_description": "{task}"}),
                ("find agent for: {task}", "route_task", {"task_description": "{task}"}),
            ]
        )

        # === Edge cases - empty args ===
        templates.extend(
            [
                ("get active context", "get_active_context", {}),
                ("check health", "get_health", {}),
                ("list files", "list_directory", {"path": "."}),
            ]
        )

        # === Edge cases - many args ===
        templates.extend(
            [
                (
                    "search memory for {query} with limit 50",
                    "memory_search",
                    {"query": "{query}", "limit": 50},
                ),
                (
                    "write {content} to {path} and verify",
                    "write_file",
                    {"path": "{path}", "content": "{content}"},
                ),
                ("log git status for {path} with verbose", "git_status", {"repo_path": "{path}"}),
            ]
        )

        # === Coding tools (code generation, analysis, refactoring) ===
        templates.extend(
            [
                # Code generation
                (
                    "generate function {func_name}",
                    "code_generate",
                    {"func_name": "{func_name}", "language": "python"},
                ),
                (
                    "write {language} code for {func_name}",
                    "code_generate",
                    {"func_name": "{func_name}", "language": "{language}"},
                ),
                (
                    "create {language} class {class_name}",
                    "code_generate",
                    {"class_name": "{class_name}", "language": "{language}"},
                ),
                # Code analysis
                ("analyze code complexity", "code_analyze", {"path": "{path}"}),
                ("find bugs in {path}", "code_analyze", {"path": "{path}", "mode": "bugs"}),
                ("check code quality", "code_analyze", {"path": "{path}", "mode": "quality"}),
                # Refactoring
                ("refactor {path}", "code_refactor", {"path": "{path}", "style": "functional"}),
                ("improve {path}", "code_refactor", {"path": "{path}", "style": "modern"}),
                ("optimize {path}", "code_refactor", {"path": "{path}", "style": "performance"}),
            ]
        )

        # === Math tools (computation, formulas, data) ===
        templates.extend(
            [
                # Basic computation
                ("calculate {expression}", "math_compute", {"expression": "{expression}"}),
                ("compute {expression}", "math_compute", {"expression": "{expression}"}),
                ("evaluate {expression}", "math_compute", {"expression": "{expression}"}),
                # Formula evaluation
                (
                    "solve formula {formula}",
                    "math_solve",
                    {"formula": "{formula}", "variables": {}},
                ),
                (
                    "calculate {formula} with {variables}",
                    "math_solve",
                    {"formula": "{formula}", "variables": "{variables}"},
                ),
                # Data analysis
                (
                    "analyze dataset {dataset}",
                    "math_analyze",
                    {"dataset": "{dataset}", "operations": ["mean", "std"]},
                ),
                (
                    "compute statistics for {dataset}",
                    "math_analyze",
                    {"dataset": "{dataset}", "operations": ["mean", "median", "mode"]},
                ),
                # Statistics
                (
                    "run regression on {data}",
                    "math_statistics",
                    {"data": "{data}", "method": "linear_regression"},
                ),
                (
                    "calculate correlation",
                    "math_statistics",
                    {"data": "{data}", "method": "correlation"},
                ),
            ]
        )

        # === Code execution tools ===
        templates.extend(
            [
                ("run tests in {path}", "run_tests", {"path": "{path}", "framework": "pytest"}),
                ("execute {path}", "run_code", {"path": "{path}", "language": "python"}),
                ("run benchmark {path}", "run_benchmark", {"path": "{path}", "iterations": 100}),
                ("lint {path}", "run_linter", {"path": "{path}", "linter": "ruff"}),
                ("format {path}", "run_formatter", {"path": "{path}", "formatter": "black"}),
            ]
        )

        return templates

    def generate(
        self,
        num_variations: int = 10,
        output_path: Optional[Path] = None,
        use_phrase_variations: bool = True,
    ) -> List[Dict[str, Any]]:
        """Generate training dataset.

        Args:
            num_variations: Number of variations to generate per template.
            output_path: Optional path to save the generated data.
            use_phrase_variations: If True, randomly select from phrase variations.

        Returns:
            List of training pairs (dicts with input/output/tool/args).
        """
        # Expanded sample values for placeholder substitution
        queries = [
            "security",
            "authentication",
            "deployment",
            "testing",
            "API",
            "config",
            "error handling",
            "performance",
            "optimization",
            "logging",
            "caching",
            "database",
            "migration",
            "validation",
            "serialization",
            "parsing",
            "routing",
            "middleware",
            "authentication",
            "authorization",
        ]
        paths = [
            "src/main.py",
            "README.md",
            "config.json",
            "package.json",
            ".env",
            "src/utils.py",
            "tests/test.py",
            "setup.py",
            "pyproject.toml",
            "src/models/user.py",
            "src/api/routes.py",
            "docs/README.md",
        ]
        repos = [
            ("facebook", "react"),
            ("microsoft", "vscode"),
            ("vercel", "next.js"),
            ("openai", "openai-python"),
            ("anthropic", "anthropic-sdk-python"),
            ("tensorflow", "tensorflow"),
            ("pytorch", "pytorch"),
        ]
        urls = [
            "https://docs.python.org",
            "https://nodejs.org",
            "https://react.dev",
            "https://python.org",
            "https://typescriptlang.org",
            "https://fastapi.tiangolo.com",
            "https://docs.github.com",
            "https://platform.openai.com",
        ]
        libs = [
            "react",
            "python",
            "typescript",
            "express",
            "fastapi",
            "django",
            "pytorch",
            "tensorflow",
            "pandas",
            "numpy",
            "llama",
            "transformers",
        ]
        problems = [
            "debug this error",
            "optimize performance",
            "design API",
            "fix memory leak",
            "improve security",
            "refactor code",
            "write tests",
            "handle edge cases",
            "add caching",
            "implement auth",
            "optimize queries",
            "handle concurrency",
        ]
        tasks = [
            "implement auth",
            "write tests",
            "refactor code",
            "add logging",
            "optimize performance",
            "fix bug",
            "create API endpoint",
            "add validation",
            "implement caching",
            "write documentation",
            "create migration",
        ]
        # New sample values for coding templates
        func_names = [
            "authenticate_user",
            "process_payment",
            "fetch_data",
            "validate_input",
            "calculate_total",
            "serialize_json",
            "parse_response",
            "hash_password",
            "generate_token",
            "send_email",
        ]
        class_names = [
            "UserManager",
            "PaymentProcessor",
            "DataFetcher",
            "AuthHandler",
            "CacheManager",
            "QueueWorker",
            "APIClient",
            "Validator",
            "Serializer",
            "Logger",
        ]
        languages = ["python", "javascript", "typescript", "go", "rust", "java", "c++"]
        expressions = [
            "2 + 2",
            "sqrt(16) + 5",
            "10 * (3 + 7) / 2",
            "log(100)",
            "sin(pi/4)",
            "factorial(5)",
            "sum(1..100)",
            "pow(2, 8)",
        ]
        formulas = [
            "area = pi * r^2",
            "distance = speed * time",
            "volume = l * w * h",
            "force = mass * acceleration",
            "energy = mass * c^2",
        ]
        datasets = ["sales_data", "user_logs", "api_metrics", "performance_stats", "test_results"]
        data_samples = [
            "[1,2,3,4,5]",
            "[10,20,30,40,50]",
            "[5,15,25,35,45]",
            "[2,4,6,8,10]",
            "[1,1,2,3,5,8,13]",
        ]
        contents = [
            "hello world",
            "test data",
            "config here",
            "user preferences",
            "application settings",
            "temporary cache data",
            "session state",
            "api response",
            "error message",
            "debug information",
        ]

        training_pairs = []
        random.seed(42)

        for template, tool_name, args in self._templates:
            for i in range(num_variations):
                input_text = template
                args_copy = dict(args)

                # Replace placeholders
                if "{query}" in input_text:
                    input_text = input_text.replace("{query}", queries[i % len(queries)])
                    if "{query}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{query}", queries[i % len(queries)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{path}" in input_text:
                    input_text = input_text.replace("{path}", paths[i % len(paths)])
                    if "{path}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{path}", paths[i % len(paths)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{owner}" in input_text and "{repo}" in input_text:
                    owner, repo = repos[i % len(repos)]
                    input_text = input_text.replace("{owner}", owner).replace("{repo}", repo)
                    if "{owner}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{owner}", owner).replace("{repo}", repo)
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{url}" in input_text:
                    input_text = input_text.replace("{url}", urls[i % len(urls)])
                    if "{url}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{url}", urls[i % len(urls)]) if isinstance(v, str) else v
                            for k, v in args_copy.items()
                        }

                if "{lib}" in input_text:
                    input_text = input_text.replace("{lib}", libs[i % len(libs)])
                    if "{lib}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{lib}", libs[i % len(libs)]) if isinstance(v, str) else v
                            for k, v in args_copy.items()
                        }

                if "{problem}" in input_text:
                    input_text = input_text.replace("{problem}", problems[i % len(problems)])
                    if "{problem}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{problem}", problems[i % len(problems)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{task}" in input_text:
                    input_text = input_text.replace("{task}", tasks[i % len(tasks)])
                    if "{task}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{task}", tasks[i % len(tasks)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{content}" in input_text:
                    input_text = input_text.replace("{content}", contents[i % len(contents)])
                    if "{content}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{content}", contents[i % len(contents)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                # === New placeholder handling for coding/math templates ===
                if "{func_name}" in input_text:
                    input_text = input_text.replace("{func_name}", func_names[i % len(func_names)])
                    if "{func_name}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{func_name}", func_names[i % len(func_names)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{class_name}" in input_text:
                    input_text = input_text.replace(
                        "{class_name}", class_names[i % len(class_names)]
                    )
                    if "{class_name}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{class_name}", class_names[i % len(class_names)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{language}" in input_text:
                    input_text = input_text.replace("{language}", languages[i % len(languages)])
                    if "{language}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{language}", languages[i % len(languages)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{expression}" in input_text:
                    input_text = input_text.replace(
                        "{expression}", expressions[i % len(expressions)]
                    )
                    if "{expression}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{expression}", expressions[i % len(expressions)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{formula}" in input_text:
                    input_text = input_text.replace("{formula}", formulas[i % len(formulas)])
                    if "{formula}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{formula}", formulas[i % len(formulas)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{dataset}" in input_text:
                    input_text = input_text.replace("{dataset}", datasets[i % len(datasets)])
                    if "{dataset}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{dataset}", datasets[i % len(datasets)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{data}" in input_text:
                    input_text = input_text.replace("{data}", data_samples[i % len(data_samples)])
                    if "{data}" in str(args_copy):
                        args_copy = {
                            k: v.replace("{data}", data_samples[i % len(data_samples)])
                            if isinstance(v, str)
                            else v
                            for k, v in args_copy.items()
                        }

                if "{variables}" in input_text:
                    input_text = input_text.replace("{variables}", '{"x": 5, "y": 10}')

                if "{mode}" in input_text:
                    # Keep mode as-is in input, just pass through
                    pass

                # Clean empty args
                args_clean = {k: v for k, v in args_copy.items() if v}

                # Format output
                output_text = self._format_output(tool_name, args_clean)

                training_pairs.append(
                    {
                        "input": input_text,
                        "output": output_text,
                        "tool": tool_name,
                        "args": args_clean,
                    }
                )

        # Save if output path provided
        if output_path:
            self.save(training_pairs, output_path)

        return training_pairs

    def _format_output(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Format tool call as output string.

        Args:
            tool_name: Name of the tool.
            args: Tool arguments.

        Returns:
            Formatted tool call string.
        """
        if not args:
            return f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ }}}}[/TOOL_CALL]'

        args_str = ", ".join(f'--{k} "{v}"' for k, v in args.items())
        return f'[TOOL_CALL]{{tool => "{tool_name}", args => {{ {args_str} }}}}[/TOOL_CALL]'

    def save(self, data: List[Dict[str, Any]], output_path: Path) -> None:
        """Save training data to JSONL file.

        Args:
            data: Training data to save.
            output_path: Path to save the file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

    def load(self, input_path: Path) -> List[Dict[str, Any]]:
        """Load training data from JSONL file.

        Args:
            input_path: Path to the JSONL file.

        Returns:
            List of training pairs.
        """
        with open(input_path) as f:
            return [json.loads(line) for line in f]

    def prepare_for_fine_tuning(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """Convert data to fine-tuning format (instruction tuning style).

        Args:
            input_path: Path to input JSONL file.
            output_path: Optional path to save converted data.

        Returns:
            Formatted data for fine-tuning.
        """
        data = self.load(input_path)

        formatted = []
        for item in data:
            formatted.append(
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a tool call translator. Convert user requests into MCP tool calls.",
                        },
                        {"role": "user", "content": item["input"]},
                        {"role": "assistant", "content": item["output"]},
                    ]
                }
            )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(formatted, f, indent=2)

        return formatted

    def generate_preference_pairs(
        self,
        num_pairs: int = 100,
        output_path: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """Generate preference pairs for GRPO/SimPO/KTO training.

        For preference optimization, we need pairs of:
        - prompt: The user request
        - chosen: The correct/good tool call
        - rejected: The incorrect/bad tool call

        Args:
            num_pairs: Number of preference pairs to generate.
            output_path: Optional path to save the pairs.

        Returns:
            List of preference pairs with prompt, chosen, rejected.
        """
        # First generate base examples
        base_examples = self.generate(num_variations=1, output_path=None)

        # Create preference pairs by pairing correct with incorrect tool calls
        # We can create "wrong" outputs by:
        # 1. Swapping tool names (memory_search -> memory_write)
        # 2. Swapping arguments between tools
        # 3. Creating malformed tool calls

        tool_pairs = [
            ("memory_search", "memory_write"),
            ("read_file", "write_file"),
            ("git_status", "git_log"),
            ("fetch_url", "browser_navigate"),
            ("get_active_context", "get_health"),
        ]

        preference_pairs = []
        random.seed(42)

        for i in range(min(num_pairs, len(base_examples))):
            example = base_examples[i % len(base_examples)]
            prompt = example["input"]
            chosen = example["output"]

            # Create a rejected (wrong) output
            tool_name = example["tool"]

            # Strategy 1: Use a different tool from the same category
            rejected_tool = None
            for correct, wrong in tool_pairs:
                if tool_name == correct:
                    rejected_tool = wrong
                    break
                elif tool_name == wrong:
                    rejected_tool = correct
                    break

            if rejected_tool:
                # Create rejected output with same args but wrong tool
                rejected_args = dict(example.get("args", {}))
                rejected = self._format_output(rejected_tool, rejected_args)
            else:
                # Strategy 2: Create malformed tool call
                rejected = f'[TOOL_CALL]{{tool => "invalid_tool", args => {{ }}}}[/TOOL_CALL]'

            preference_pairs.append(
                {
                    "prompt": prompt,
                    "chosen": chosen,
                    "rejected": rejected,
                }
            )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                for pair in preference_pairs:
                    f.write(json.dumps(pair) + "\n")

        return preference_pairs

    def generate_multi_turn_conversation(
        self,
        num_conversations: int = 10,
        turns_per_conversation: int = 3,
        output_path: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """Generate multi-turn conversation data for training.

        Creates conversational training data where:
        - Each conversation has multiple turns
        - Context from previous turns informs subsequent tool calls
        - System can learn to maintain conversation state

        Args:
            num_conversations: Number of conversations to generate.
            turns_per_conversation: Number of turns per conversation.
            output_path: Optional path to save the conversations.

        Returns:
            List of conversation objects with turns and context.
        """
        conversations = []
        random.seed(42)

        # Define conversation scenarios for multi-turn flows
        scenarios = [
            {
                "name": "file_operations_sequence",
                "steps": [
                    ("list_directory", {"path": "src/"}),
                    ("read_file", {"path": "src/main.py"}),
                    ("write_file", {"path": "src/main.py", "content": "# updated"}),
                ],
            },
            {
                "name": "memory_search_write_sequence",
                "steps": [
                    ("memory_search", {"query": "config", "limit": 5}),
                    ("memory_write", {"content": "config data", "kind": "semantic"}),
                    ("memory_search", {"query": "config", "limit": 10}),
                ],
            },
            {
                "name": "git_workflow",
                "steps": [
                    ("git_status", {"repo_path": "."}),
                    ("git_log", {"repo_path": ".", "max_count": 10}),
                    ("git_diff", {"repo_path": ".", "target": "HEAD"}),
                ],
            },
            {
                "name": "web_research",
                "steps": [
                    ("fetch_url", {"url": "https://docs.python.org", "format": "markdown"}),
                    ("context7_query_docs", {"library_id": "/python", "query": "basics"}),
                    ("browser_navigate", {"url": "https://python.org"}),
                ],
            },
            {
                "name": "code_analysis",
                "steps": [
                    ("list_directory", {"path": "src/"}),
                    ("code_analyze", {"path": "src/", "mode": "quality"}),
                    ("code_refactor", {"path": "src/utils.py", "style": "modern"}),
                ],
            },
        ]

        # Phrase variations for each turn position
        turn_phrases = {
            0: [  # Opening turn
                "list what's in src directory",
                "search memory for config",
                "check git status",
                "fetch python docs",
                "show me files in src",
            ],
            1: [  # Second turn
                "now read the main file",
                "write this to memory",
                "show recent commits",
                "get more details",
                "analyze the code",
            ],
            2: [  # Third turn
                "update it with new content",
                "search again for context",
                "show what changed",
                "navigate to reference",
                "refactor for better style",
            ],
        }

        for conv_idx in range(num_conversations):
            scenario = scenarios[conv_idx % len(scenarios)]
            conversation = {
                "conversation_id": f"conv_{conv_idx}",
                "scenario": scenario["name"],
                "turns": [],
            }

            # Build context from previous turns
            context_summary = ""

            for turn_idx in range(min(turns_per_conversation, len(scenario["steps"]))):
                tool_name, args = scenario["steps"][turn_idx]

                # Generate natural language input for this turn
                if turn_idx < len(turn_phrases):
                    input_text = turn_phrases[turn_idx][conv_idx % len(turn_phrases[turn_idx])]
                else:
                    input_text = f"continue with {tool_name}"

                # Include context from previous turns
                if context_summary:
                    input_text = f"{context_summary} Also, {input_text}"

                # Format the expected tool call
                output_text = self._format_output(tool_name, args)

                turn = {
                    "turn_id": turn_idx,
                    "input": input_text,
                    "output": output_text,
                    "tool": tool_name,
                    "args": args,
                    "context_before": context_summary,
                }

                conversation["turns"].append(turn)

                # Update context for next turn
                context_summary += f"[Turn {turn_idx + 1}: {tool_name}] "

            conversations.append(conversation)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                for conv in conversations:
                    f.write(json.dumps(conv) + "\n")

        return conversations

    def prepare_multi_turn_for_fine_tuning(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """Convert multi-turn conversations to fine-tuning format.

        Creates training examples where each turn includes conversation history.

        Args:
            input_path: Path to multi-turn JSONL file.
            output_path: Optional path to save converted data.

        Returns:
            Formatted data with conversation context.
        """
        with open(input_path) as f:
            conversations = [json.loads(line) for line in f]

        formatted = []

        for conv in conversations:
            system_prompt = "You are a tool call translator. Maintain conversation context and convert user requests to MCP tool calls."

            for turn in conv["turns"]:
                # Build conversation history
                history = []
                for prev_turn in conv["turns"][: turn["turn_id"]]:
                    history.append({"role": "user", "content": prev_turn["input"]})
                    history.append({"role": "assistant", "content": prev_turn["output"]})

                # Create messages with context
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(history)
                messages.append({"role": "user", "content": turn["input"]})

                formatted.append(
                    {
                        "messages": messages,
                        "ground_truth": turn["output"],
                        "tool": turn["tool"],
                        "conversation_id": conv["conversation_id"],
                        "turn_id": turn["turn_id"],
                    }
                )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(formatted, f, indent=2)

        return formatted
