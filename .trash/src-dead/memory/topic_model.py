"""Topic model for auto-categorizing files into topics/clusters.

This module provides keyword-based topic assignment without ML dependencies.
Files can belong to multiple topics based on content, extension, and directory.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Predefined topics
PREDEFINED_TOPICS = [
    "python",
    "javascript",
    "typescript",
    "documentation",
    "configuration",
    "docker",
    "devops",
    "testing",
    "data",
    "web",
    "api",
    "database",
    "security",
    "ui",
    "infrastructure",
]

# Topic keyword mappings (keyword -> topic)
TOPIC_KEYWORDS = {
    "python": [
        "import ",
        "from ",
        "def ",
        "class ",
        "__init__",
        "self.",
        "pip",
        "venv",
        "requirements.txt",
        "setup.py",
        "pyproject.toml",
        "flask",
        "django",
        "fastapi",
        "pandas",
        "numpy",
        "pytest",
    ],
    "javascript": [
        "const ",
        "let ",
        "var ",
        "function",
        "=>",
        "require(",
        "module.exports",
        "export ",
        "import ",
        "console.log",
        "package.json",
        "node_modules",
        "npm ",
        "yarn ",
        "react",
        "vue",
        "angular",
        "express",
        "webpack",
    ],
    "typescript": [
        "interface ",
        "type ",
        ": string",
        ": number",
        ": boolean",
        "as const",
        "as any",
        "import type",
        "export type",
        "<T>",
        " generics",
        "enum ",
        "namespace",
    ],
    "documentation": [
        "# ",
        "## ",
        "### ",
        "**bold**",
        "*italic*",
        "README",
        "CHANGELOG",
        "LICENSE",
        "CONTRIBUTING",
        "```",
        "```python",
        "```js",
        "```bash",
    ],
    "configuration": [
        "settings",
        "config",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".conf",
        ".env",
        "environment",
        "settings.py",
        "application.yml",
        "appsettings.json",
    ],
    "docker": [
        "docker",
        "Dockerfile",
        "docker-compose",
        "FROM ",
        "RUN ",
        "CMD ",
        "ENTRYPOINT",
        "EXPOSE ",
        "VOLUME ",
        "COPY ",
        "docker build",
        "docker run",
        "kubernetes",
        "k8s",
    ],
    "devops": [
        "ci/cd",
        "github actions",
        "gitlab ci",
        "jenkins",
        "pipeline",
        "deploy",
        "terraform",
        "ansible",
        "chef",
        "cloudformation",
        "helm",
        "ingress",
        "service mesh",
    ],
    "testing": [
        "test",
        "spec",
        "describe(",
        "it(",
        "expect(",
        "pytest",
        "unittest",
        "junit",
        "mocha",
        "jest",
        "coverage",
        "integration test",
        "unit test",
        "e2e",
    ],
    "data": [
        "csv",
        "json",
        "xml",
        "database",
        "query",
        "select",
        "insert",
        "update",
        "delete",
        "table",
        "index",
        "pandas",
        "numpy",
        "etl",
        "pipeline",
        "stream",
    ],
    "web": [
        "http",
        "https",
        "url",
        "request",
        "response",
        "html",
        "css",
        "javascript",
        "frontend",
        "browser",
        "websocket",
        "rest",
        "graphql",
        "cors",
        "cookie",
    ],
    "api": [
        "endpoint",
        "route",
        "controller",
        "handler",
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "swagger",
        "openapi",
        "graphql",
        "restful",
        "request",
        "response",
        "status code",
    ],
    "database": [
        "sql",
        "mysql",
        "postgresql",
        "mongodb",
        "redis",
        "sqlite",
        "oracle",
        "dynamodb",
        "table",
        "index",
        "migration",
        "schema",
        "query",
        "transaction",
    ],
    "security": [
        "auth",
        "password",
        "encrypt",
        "decrypt",
        "token",
        "jwt",
        "oauth",
        "certificate",
        "ssl",
        "tls",
        "secret",
        "key",
        "permission",
        "access control",
    ],
    "ui": [
        "button",
        "input",
        "modal",
        "dialog",
        "layout",
        "component",
        "style",
        "css",
        "sass",
        "tailwind",
        "responsive",
        "accessibility",
        "animation",
        "theme",
    ],
    "infrastructure": [
        "server",
        "cluster",
        "node",
        "pod",
        "container",
        "aws",
        "azure",
        "gcp",
        "kubernetes",
        "vm",
        "network",
        "load balancer",
        "firewall",
        "dns",
    ],
}

# Extension to topic mapping
EXTENSION_TOPICS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".md": "documentation",
    ".markdown": "documentation",
    ".txt": "documentation",
    ".json": "configuration",
    ".yaml": "configuration",
    ".yml": "configuration",
    ".toml": "configuration",
    ".ini": "configuration",
    ".conf": "configuration",
    ".env": "configuration",
    "Dockerfile": "docker",
    "docker-compose.yml": "docker",
    "docker-compose.yaml": "docker",
    ".sql": "database",
    ".sh": "devops",
    ".bash": "devops",
    ".zsh": "devops",
    ".test.js": "testing",
    ".test.ts": "testing",
    ".spec.js": "testing",
    ".spec.ts": "testing",
    ".go": "api",
    ".rs": "api",
    ".java": "api",
    ".rb": "api",
    ".php": "api",
}

# Directory name to topic mapping
DIRECTORY_TOPICS = {
    "test": "testing",
    "tests": "testing",
    "spec": "testing",
    "__tests__": "testing",
    "docs": "documentation",
    "doc": "documentation",
    "documentation": "documentation",
    "config": "configuration",
    "configs": "configuration",
    ".github": "devops",
    "ci": "devops",
    "scripts": "devops",
    "kubernetes": "infrastructure",
    "k8s": "infrastructure",
    "docker": "docker",
    "database": "database",
    "db": "database",
    "api": "api",
    "routes": "api",
    "controllers": "api",
    "models": "data",
    "views": "ui",
    "components": "ui",
    "src": "web",
    "public": "web",
    "static": "web",
    "security": "security",
    "auth": "security",
}


class TopicModel:
    """Topic model for auto-categorizing files into topics.

    Uses keyword-based clustering to assign topics to files.
    Each file can belong to multiple topics.
    """

    def __init__(self, topics_path: str = "context/memory/topics.json"):
        """Initialize TopicModel, loading or creating topics file.

        Args:
            topics_path: Path to the topics JSON file.
        """
        self.topics_path: str = topics_path
        self.topics: dict[str, list[str]] = {}
        self.metadata: dict[str, Any] = {"version": "1.0", "last_updated": ""}
        self._load()

    def _load(self) -> None:
        """Load topics from JSON file or create default structure."""
        try:
            if os.path.exists(self.topics_path):
                with open(self.topics_path, "r", encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)
                    self.topics = data.get("topics", {})
                    self.metadata = data.get("metadata", {"version": "1.0"})
                    logger.info(f"Loaded topics from {self.topics_path}")
            else:
                # Initialize with empty topics
                for topic in PREDEFINED_TOPICS:
                    self.topics[topic] = []
                self._update_metadata()
                self.save()
                logger.info(f"Created new topics file at {self.topics_path}")
        except Exception as e:
            logger.error(f"Failed to load topics: {e}")
            # Initialize with empty topics on error
            for topic in PREDEFINED_TOPICS:
                self.topics[topic] = []

    def _update_metadata(self) -> None:
        """Update metadata timestamp."""
        self.metadata["last_updated"] = datetime.now(timezone.utc).isoformat()

    def categorize_file(
        self, file_path: str, content: str, metadata: dict[str, Any]
    ) -> list[str]:
        """Assign topics to a file based on content, extension, and directory.

        Args:
            file_path: Full path to the file.
            content: File content (for keyword matching).
            metadata: File metadata containing extension, file_name, etc.

        Returns:
            List of assigned topic names.
        """
        topics: set[str] = set()

        # 1. Extension-based topic detection
        extension = metadata.get("extension", Path(file_path).suffix.lower())
        if extension in EXTENSION_TOPICS:
            topics.add(EXTENSION_TOPICS[extension])
        elif extension == ".py":
            topics.add("python")
        elif extension in (".js", ".jsx"):
            topics.add("javascript")
        elif extension in (".ts", ".tsx"):
            topics.add("typescript")

        # 2. Directory-based topic detection
        path_obj = Path(file_path)
        for part in path_obj.parts:
            part_lower = part.lower()
            if part_lower in DIRECTORY_TOPICS:
                topics.add(DIRECTORY_TOPICS[part_lower])
            # Check for common directory patterns
            if "test" in part_lower or "spec" in part_lower:
                topics.add("testing")
            if "doc" in part_lower:
                topics.add("documentation")
            if "config" in part_lower:
                topics.add("configuration")
            if "docker" in part_lower or part_lower.startswith("docker"):
                topics.add("docker")

        # 3. Content-based keyword detection
        content_lower = content.lower()
        file_name_lower = metadata.get("file_name", "").lower()

        for topic, keywords in TOPIC_KEYWORDS.items():
            for keyword in keywords:
                # Check both content and filename
                if (
                    keyword.lower() in content_lower
                    or keyword.lower() in file_name_lower
                ):
                    topics.add(topic)
                    break

        # 4. Special file name detection
        if "dockerfile" in file_name_lower:
            topics.add("docker")
        if "readme" in file_name_lower or "changelog" in file_name_lower:
            topics.add("documentation")
        if ".env" in file_name_lower or file_name_lower.startswith("."):
            topics.add("configuration")

        # 5. Infer topics based on combinations
        if "python" in topics and "web" in topics:
            topics.add("api")
        if "javascript" in topics and "web" in topics:
            topics.add("api")

        # Add to internal tracking if file_path provided
        if file_path:
            self._add_file_to_topics(file_path, list(topics))

        return list(topics)

    def _add_file_to_topics(self, file_path: str, topics: list[str]) -> None:
        """Add file to topic lists.

        Args:
            file_path: Path to the file.
            topics: List of topic names.
        """
        # Remove from all topics first
        for topic_files in self.topics.values():
            if file_path in topic_files:
                topic_files.remove(file_path)

        # Add to new topics
        for topic in topics:
            if topic in self.topics:
                if file_path not in self.topics[topic]:
                    self.topics[topic].append(file_path)

    def get_topics(self) -> dict[str, list[str]]:
        """Get all topics with their assigned files.

        Returns:
            Dictionary mapping topic names to lists of file paths.
        """
        return self.topics

    def assign_topics(self, file_path: str, topics: list[str]) -> None:
        """Manually assign topics to a file.

        Args:
            file_path: Path to the file.
            topics: List of topic names to assign.
        """
        self._add_file_to_topics(file_path, topics)
        self._update_metadata()
        self.save()
        logger.info(f"Assigned topics {topics} to {file_path}")

    def get_topic_files(self, topic: str) -> list[str]:
        """Get all files in a specific topic.

        Args:
            topic: Topic name to query.

        Returns:
            List of file paths in the topic.
        """
        return self.topics.get(topic, [])

    def cluster_files(self, files: list[dict[str, Any]]) -> dict[str, list[str]]:
        """Cluster files by topic similarity.

        Args:
            files: List of file dictionaries with 'file_path', 'content', and 'metadata'.

        Returns:
            Dictionary mapping topic names to lists of file paths.
        """
        clusters: dict[str, list[str]] = {topic: [] for topic in PREDEFINED_TOPICS}

        for file_info in files:
            file_path = file_info.get("file_path", "")
            content = file_info.get("content", "")
            metadata = file_info.get("metadata", {})

            topics = self.categorize_file(file_path, content, metadata)

            for topic in topics:
                if topic in clusters:
                    clusters[topic].append(file_path)

        return clusters

    def save(self) -> None:
        """Save topics to JSON file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.topics_path), exist_ok=True)

            data = {"topics": self.topics, "metadata": self.metadata}
            with open(self.topics_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved topics to {self.topics_path}")
        except Exception as e:
            logger.error(f"Failed to save topics: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get topic statistics.

        Returns:
            Dictionary with topic counts and statistics.
        """
        topic_counts = {topic: len(files) for topic, files in self.topics.items()}

        total_files = sum(topic_counts.values())
        topics_with_files = sum(1 for count in topic_counts.values() if count > 0)

        return {
            "total_files": total_files,
            "topics_with_files": topics_with_files,
            "total_topics": len(PREDEFINED_TOPICS),
            "topic_counts": topic_counts,
            "last_updated": self.metadata.get("last_updated", ""),
        }


def categorize_file(
    file_path: str,
    content: str,
    metadata: dict[str, Any],
    topics_path: str = "context/memory/topics.json",
) -> list[str]:
    """Convenience function to categorize a file.

    Args:
        file_path: Full path to the file.
        content: File content for keyword matching.
        metadata: File metadata dictionary.
        topics_path: Path to topics JSON file.

    Returns:
        List of assigned topic names.
    """
    model = TopicModel(topics_path)
    return model.categorize_file(file_path, content, metadata)


def get_topics(topics_path: str = "context/memory/topics.json") -> dict[str, list[str]]:
    """Convenience function to get all topics.

    Args:
        topics_path: Path to topics JSON file.

    Returns:
        Dictionary mapping topic names to file lists.
    """
    model = TopicModel(topics_path)
    return model.get_topics()


def assign_topics(
    file_path: str, topics: list[str], topics_path: str = "context/memory/topics.json"
) -> None:
    """Convenience function to manually assign topics.

    Args:
        file_path: Path to the file.
        topics: List of topic names.
        topics_path: Path to topics JSON file.
    """
    model = TopicModel(topics_path)
    model.assign_topics(file_path, topics)


def cluster_files(
    files: list[dict[str, Any]],
    topics_path: str = "context/memory/topics.json",
) -> dict[str, list[str]]:
    """Convenience function to cluster files by topics.

    Args:
        files: List of file dictionaries.
        topics_path: Path to topics JSON file.

    Returns:
        Dictionary mapping topic names to file lists.
    """
    model = TopicModel(topics_path)
    return model.cluster_files(files)
