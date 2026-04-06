"""Synthesizer — Generate summaries and find connections between files."""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any, Dict, List, Set, Union

logger = logging.getLogger(__name__)

# Default summarization parameters
DEFAULT_SUMMARY_SENTENCES = 3
DEFAULT_KEY_CONCEPTS = 10


class Synthesizer:
    """Generate summaries and find connections between indexed files."""

    def __init__(self, summaries_dir: str = "context/memory/summaries"):
        """Initialize synthesizer with summaries directory.

        Args:
            summaries_dir: Directory to store cached summaries.
        """
        self.summaries_dir: Path = Path(summaries_dir)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized Synthesizer with summaries_dir: {self.summaries_dir}")

    def generate_summary(self, file_path: str, content: str) -> Dict[str, Any]:
        """Generate summary for a single file using extractive method.

        Args:
            file_path: Path to the source file.
            content: Text content to summarize.

        Returns:
            Dictionary with summary structure:
            - file_path: Source file path
            - title: Extracted title from file
            - description: Brief description (first sentences)
            - key_concepts: List of key terms/concepts
            - file_type: File extension/type
            - word_count: Number of words in content
            - generated_at: ISO timestamp
        """
        if not content or not content.strip():
            return {
                "file_path": file_path,
                "title": Path(file_path).name,
                "description": "Empty file",
                "key_concepts": [],
                "file_type": self._get_file_type(file_path),
                "word_count": 0,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        # Extract title from file
        title = self._extract_title(file_path, content)

        # Extract description (first N sentences)
        description = self._extract_description(content)

        # Extract key concepts/terms
        key_concepts = self._extract_key_concepts(content, file_path)

        return {
            "file_path": file_path,
            "title": title,
            "description": description,
            "key_concepts": key_concepts,
            "file_type": self._get_file_type(file_path),
            "word_count": len(content.split()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def find_connections(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Find connections between files based on various signals.

        Args:
            file_paths: List of file paths to analyze.

        Returns:
            List of connection dictionaries:
            - from_file: Source file path
            - to_file: Target file path
            - connection_type: Type of connection (shared_concept, same_directory, import, similar_type)
            - strength: Connection strength (0.0-1.0)
            - shared_concepts: List of shared concepts/keywords
        """
        if len(file_paths) < 2:
            return []

        # Load summaries for all files
        summaries = {}
        for fp in file_paths:
            summary = self.get_summary(fp)
            if summary is None:
                # Generate summary if not cached
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    summary = self.generate_summary(fp, content)
                    self.save_summary(fp, summary)
                except Exception as e:
                    logger.warning(f"Could not load {fp}: {e}")
                    continue
            summaries[fp] = summary

        connections = []
        file_list = list(summaries.keys())

        # Compare each pair of files
        for i, file_a in enumerate(file_list):
            for file_b in file_list[i + 1 :]:
                summary_a = summaries[file_a]
                summary_b = summaries[file_b]

                # Find shared concepts
                concepts_a = set(summary_a.get("key_concepts", []))
                concepts_b = set(summary_b.get("key_concepts", []))
                shared = concepts_a & concepts_b

                if not shared:
                    continue

                # Determine connection type
                conn_type = self._determine_connection_type(file_a, file_b, shared)

                # Calculate strength based on number of shared concepts
                strength = min(
                    len(shared) / max(len(concepts_a), len(concepts_b), 1), 1.0
                )

                connections.append(
                    {
                        "from_file": file_a,
                        "to_file": file_b,
                        "connection_type": conn_type,
                        "strength": round(strength, 2),
                        "shared_concepts": list(shared),
                    }
                )

        # Sort by strength (highest first)
        connections.sort(key=lambda x: x["strength"], reverse=True)
        return connections

    def synthesize_directory(self, dir_path: Union[str, Path]) -> Dict[str, Any]:
        """Summarize all files in a directory.

        Args:
            dir_path: Path to directory to summarize.

        Returns:
            Dictionary with directory summary:
            - directory: Directory path
            - file_count: Number of files processed
            - summaries: List of file summaries
            - key_concepts: Aggregate key concepts across all files
            - synthesized_at: ISO timestamp
        """
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {dir_path}")

        # Find all files in directory (recursive)
        files = []
        for ext in ["py", "js", "ts", "tsx", "jsx", "md", "txt", "json", "yaml", "yml"]:
            files.extend(dir_path.rglob(f"*.{ext}"))

        # Also include files without extension
        files.extend(dir_path.rglob("*"))
        files = [
            f
            for f in files
            if f.is_file()
            and f.suffix
            in [
                "",
                ".py",
                ".js",
                ".ts",
                ".tsx",
                ".jsx",
                ".md",
                ".txt",
                ".json",
                ".yaml",
                ".yml",
            ]
        ]

        summaries = []
        all_concepts = set()

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                summary = self.generate_summary(str(file_path), content)
                summaries.append(summary)

                # Aggregate concepts
                all_concepts.update(summary.get("key_concepts", []))

                # Cache summary
                self.save_summary(str(file_path), summary)
            except Exception as e:
                logger.warning(f"Could not process {file_path}: {e}")

        return {
            "directory": str(dir_path),
            "file_count": len(summaries),
            "summaries": summaries,
            "key_concepts": list(all_concepts)[: DEFAULT_KEY_CONCEPTS * 2],
            "synthesized_at": datetime.now(timezone.utc).isoformat(),
        }

    def synthesize_project(self, project_path: Union[str, Path]) -> Dict[str, Any]:
        """Summarize entire project with structure.

        Args:
            project_path: Path to project root.

        Returns:
            Dictionary with project summary:
            - project_path: Project root path
            - directories: List of subdirectories with summaries
            - all_connections: All file connections found
            - key_concepts: Aggregate key concepts
            - synthesized_at: ISO timestamp
        """
        project_path = Path(project_path)
        if not project_path.is_dir():
            raise ValueError(f"Not a directory: {project_path}")

        # Find all subdirectories with source files
        subdirs = []
        for item in project_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # Check if directory has source files
                has_files = any(
                    item.rglob(f"*.{ext}")
                    for ext in ["py", "js", "ts", "tsx", "jsx", "md"]
                )
                if has_files:
                    subdirs.append(item)

        # Synthesize each subdirectory
        dir_summaries = {}
        all_files = []

        for subdir in subdirs:
            try:
                dir_summary = self.synthesize_directory(str(subdir))
                dir_summaries[str(subdir)] = dir_summary
                all_files.extend([s["file_path"] for s in dir_summary["summaries"]])
            except Exception as e:
                logger.warning(f"Could not synthesize {subdir}: {e}")

        # Find all connections
        connections = self.find_connections(all_files)

        # Aggregate all key concepts
        all_concepts = set()
        for dir_summary in dir_summaries.values():
            all_concepts.update(dir_summary.get("key_concepts", []))

        return {
            "project_path": str(project_path),
            "directories": list(dir_summaries.keys()),
            "directory_summaries": dir_summaries,
            "all_connections": connections,
            "key_concepts": list(all_concepts)[: DEFAULT_KEY_CONCEPTS * 3],
            "synthesized_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_summary(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached summary for a file.

        Args:
            file_path: Path to the source file.

        Returns:
            Cached summary dictionary or None if not found.
        """
        cache_path = self._get_cache_path(file_path)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load cached summary for {file_path}: {e}")
            return None

    def save_summary(self, file_path: str, summary: Dict[str, Any]) -> None:
        """Save summary to disk.

        Args:
            file_path: Path to the source file.
            summary: Summary dictionary to save.
        """
        cache_path = self._get_cache_path(file_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            logger.debug(f"Saved summary for {file_path}")
        except Exception as e:
            logger.warning(f"Could not save summary for {file_path}: {e}")

    def _get_cache_path(self, file_path: str) -> Path:
        """Get cache file path for a source file."""
        # Create a safe filename from the file path
        safe_name = file_path.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.summaries_dir / f"{safe_name}.json"

    def _get_file_type(self, file_path: str) -> str:
        """Extract file type from path."""
        ext = Path(file_path).suffix.lower()
        type_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".jsx": "jsx",
            ".md": "markdown",
            ".txt": "text",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".sh": "shell",
            ".bash": "shell",
        }
        return type_map.get(ext, "text")

    def _extract_title(self, file_path: str, content: str) -> str:
        """Extract title from file content."""
        path = Path(file_path)

        # For markdown files, try to get title from first heading
        if path.suffix == ".md":
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()

        # Fallback to filename without extension
        return path.stem.replace("_", " ").replace("-", " ").title()

    def _extract_description(self, content: str) -> str:
        """Extract first N sentences from content."""
        # Remove code blocks and extra whitespace
        content = re.sub(r"```[\s\S]*?```", "", content)
        content = re.sub(r"`[^`]+`", "", content)
        content = content.replace("\n", " ").replace("\r", " ")

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", content)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Get first N sentences
        first_n = sentences[:DEFAULT_SUMMARY_SENTENCES]
        description = " ".join(first_n)

        # Truncate if too long
        if len(description) > 500:
            description = description[:497] + "..."

        return description if description else "No description available"

    def _extract_key_concepts(self, content: str, file_path: str) -> list[str]:
        """Extract key concepts/terms from content."""
        path = Path(file_path)
        concepts = set()

        # Add file type as concept
        file_type = self._get_file_type(file_path)
        concepts.add(file_type)

        # For Python files, extract imports and function names
        if path.suffix == ".py":
            # Extract imports
            imports = re.findall(r"^(?:from|import)\s+(\w+)", content, re.MULTILINE)
            concepts.update(imports[:5])

            # Extract function names
            functions = re.findall(r"^def\s+(\w+)", content, re.MULTILINE)
            concepts.update(functions[:5])

            # Extract class names
            classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
            concepts.update(classes[:5])

        # For JavaScript/TypeScript, extract imports and functions
        elif path.suffix in [".js", ".ts", ".tsx", ".jsx"]:
            # Extract imports
            imports = re.findall(
                r"^import\s+.*?from\s+['\"]([^'\"]+)['\"]", content, re.MULTILINE
            )
            concepts.update([imp.split("/")[-1] for imp in imports[:5]])

            # Extract function declarations
            functions = re.findall(
                r"(?:function|const|let|var)\s+(\w+)\s*=", content, re.MULTILINE
            )
            concepts.update(functions[:5])

        # For markdown, extract headings
        elif path.suffix == ".md":
            headings = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
            concepts.update(headings[:5])

        # Extract common programming keywords
        common_keywords = {
            "function",
            "class",
            "interface",
            "type",
            "enum",
            "const",
            "let",
            "var",
            "def",
            "return",
            "if",
            "else",
            "for",
            "while",
            "try",
            "except",
            "catch",
            "async",
            "await",
            "export",
            "import",
            "from",
            "module",
            "public",
            "private",
            "static",
            "void",
            "null",
            "true",
            "false",
            "string",
            "number",
            "boolean",
        }
        found_keywords = common_keywords & set(content.split())
        concepts.update(found_keywords)

        # Limit to top concepts
        return list(concepts)[:DEFAULT_KEY_CONCEPTS]

    def _determine_connection_type(
        self, file_a: str, file_b: str, shared_concepts: set[str]
    ) -> str:
        """Determine the type of connection between two files."""
        path_a = Path(file_a)
        path_b = Path(file_b)

        # Check if same directory
        if path_a.parent == path_b.parent:
            return "same_directory"

        # Check for import relationships
        try:
            with open(file_a, "r", encoding="utf-8", errors="ignore") as f:
                content_a = f.read()
            with open(file_b, "r", encoding="utf-8", errors="ignore") as f:
                content_b = f.read()

            name_b = path_b.stem
            if name_b in content_a:
                return "import"
        except Exception:
            pass

        # Check for similar file types
        if path_a.suffix == path_b.suffix:
            return "similar_type"

        # Default to shared concepts
        return "shared_concept"


# ---------------------------------------------------------------------------
# Package Exports
# ---------------------------------------------------------------------------

__all__ = [
    "Synthesizer",
]
