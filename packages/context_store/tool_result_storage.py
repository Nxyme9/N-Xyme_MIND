"""
Tool Result Persistence for N-Xyme_MIND

Based on leaked Anthropic source code patterns from toolResultStorage.ts.
Provides disk persistence for large tool outputs with preview capability.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Constants matching TypeScript patterns
DEFAULT_MAX_RESULT_SIZE_CHARS = 50000  # 50k chars default threshold
PREVIEW_SIZE_BYTES = 2000
MAX_TOOL_RESULTS_PER_MESSAGE_CHARS = 250000
TOOL_RESULTS_SUBDIR = "tool-results"

# XML tags for persisted output messages
PERSISTED_OUTPUT_TAG = "<persisted-output>"
PERSISTED_OUTPUT_CLOSING_TAG = "</persisted-output>"

# Message when tool result content was cleared without persisting
TOOL_RESULT_CLEARED_MESSAGE = "[Old tool result content cleared]"


@dataclass
class PersistedToolResult:
    """Result of persisting a tool result to disk."""

    filepath: str
    original_size: int
    is_json: bool
    preview: str
    has_more: bool


@dataclass
class PersistToolResultError:
    """Error result when persistence fails."""

    error: str


@dataclass
class ToolResultMetadata:
    """Metadata for a persisted tool result."""

    tool_use_id: str
    tool_name: str
    filepath: str
    original_size: int
    is_json: bool
    created_at: datetime
    preview: str
    has_more: bool


@dataclass
class ContentReplacementState:
    """Per-conversation-thread state for aggregate tool result budget.

    Tracks replacement state across turns so enforceToolResultBudget makes
    the same choices every time (preserves prompt cache).
    """

    seen_ids: set = field(default_factory=set)
    replacements: dict = field(default_factory=dict)


class StorageManager:
    """Manages disk persistence of large tool results."""

    def __init__(
        self,
        base_dir: Path | None = None,
        subdir: str = TOOL_RESULTS_SUBDIR,
    ):
        """Initialize StorageManager.

        Args:
            base_dir: Base directory for tool results. Defaults to .n-xyme in workspace.
            subdir: Subdirectory name within base_dir.
        """
        self.base_dir = base_dir or Path.cwd() / ".n-xyme"
        self.subdir = subdir

    @property
    def tool_results_dir(self) -> Path:
        """Get the tool results directory path."""
        return self.base_dir / self.subdir

    def ensure_dir(self) -> None:
        """Ensure the tool results directory exists."""
        self.tool_results_dir.mkdir(parents=True, exist_ok=True)

    def get_filepath(self, tool_use_id: str, is_json: bool) -> Path:
        """Get the filepath where a tool result would be persisted."""
        ext = "json" if is_json else "txt"
        return self.tool_results_dir / f"{tool_use_id}.{ext}"

    def persist(
        self,
        content: str | list[dict[str, Any]],
        tool_use_id: str,
    ) -> PersistedToolResult | PersistToolResultError:
        """Persist a tool result to disk.

        Args:
            content: The tool result content to persist (string or list of content blocks).
            tool_use_id: The ID of the tool use that produced the result.

        Returns:
            PersistedToolResult with filepath and preview, or PersistToolResultError.
        """
        is_json = isinstance(content, list)

        # Check for non-text content - we can only persist text blocks
        if is_json:
            has_non_text = any(
                block.get("type") != "text"
                for block in content
                if isinstance(block, dict)
            )
            if has_non_text:
                return PersistToolResultError(
                    error="Cannot persist tool results containing non-text content"
                )

        self.ensure_dir()
        filepath = self.get_filepath(tool_use_id, is_json)

        # Serialize content
        if is_json:
            content_str = json.dumps(content, indent=2, ensure_ascii=False)
        else:
            content_str = content if isinstance(content, str) else str(content)

        # Check if already exists (use exclusive create to prevent race conditions)
        if filepath.exists():
            # Already persisted on a prior turn, fall through to preview
            pass
        else:
            try:
                filepath.write_text(content_str, encoding="utf-8")
            except OSError as e:
                return PersistToolResultError(error=str(e))

        # Generate preview
        preview, has_more = PreviewGenerator.generate(content_str, PREVIEW_SIZE_BYTES)

        return PersistedToolResult(
            filepath=str(filepath),
            original_size=len(content_str),
            is_json=is_json,
            preview=preview,
            has_more=has_more,
        )

    def load(self, tool_use_id: str) -> str | None:
        """Load a persisted tool result by ID.

        Args:
            tool_use_id: The tool use ID to load.

        Returns:
            The content string, or None if not found.
        """
        # Try both .txt and .json extensions
        for ext in ["txt", "json"]:
            filepath = self.tool_results_dir / f"{tool_use_id}.{ext}"
            if filepath.exists():
                return filepath.read_text(encoding="utf-8")
        return None

    def delete(self, tool_use_id: str) -> bool:
        """Delete a persisted tool result by ID.

        Args:
            tool_use_id: The tool use ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        deleted = False
        for ext in ["txt", "json"]:
            filepath = self.tool_results_dir / f"{tool_use_id}.{ext}"
            if filepath.exists():
                filepath.unlink()
                deleted = True
        return deleted

    def list_all(self) -> list[ToolResultMetadata]:
        """List all persisted tool results with metadata."""
        results = []
        if not self.tool_results_dir.exists():
            return results

        for filepath in self.tool_results_dir.iterdir():
            if filepath.suffix not in [".txt", ".json"]:
                continue

            try:
                content = filepath.read_text(encoding="utf-8")
                preview, has_more = PreviewGenerator.generate(
                    content, PREVIEW_SIZE_BYTES
                )

                # Extract tool_use_id from filename
                tool_use_id = filepath.stem

                results.append(
                    ToolResultMetadata(
                        tool_use_id=tool_use_id,
                        tool_name="unknown",  # Would need additional tracking
                        filepath=str(filepath),
                        original_size=len(content),
                        is_json=filepath.suffix == ".json",
                        created_at=datetime.fromtimestamp(filepath.stat().st_mtime),
                        preview=preview,
                        has_more=has_more,
                    )
                )
            except OSError:
                continue

        return sorted(results, key=lambda x: x.created_at, reverse=True)


class PreviewGenerator:
    """Generates preview truncation for large tool results."""

    @staticmethod
    def generate(
        content: str,
        max_bytes: int,
    ) -> tuple[str, bool]:
        """Generate a preview of content, truncating at newline when possible.

        Args:
            content: The content to preview.
            max_bytes: Maximum bytes for preview.

        Returns:
            Tuple of (preview string, has_more bool).
        """
        if len(content) <= max_bytes:
            return content, False

        # Find the last newline within the limit to avoid cutting mid-line
        truncated = content[:max_bytes]
        last_newline = truncated.rfind("\n")

        # If we found a newline reasonably close to the limit, use it
        # Otherwise fall back to the exact limit
        cut_point = last_newline if last_newline > max_bytes * 0.5 else max_bytes

        return content[:cut_point], True

    @staticmethod
    def build_message(result: PersistedToolResult) -> str:
        """Build a message for large tool results with preview.

        Args:
            result: The persisted tool result.

        Returns:
            Formatted message string with preview.
        """
        size_str = format_file_size(result.original_size)
        preview_size_str = format_file_size(PREVIEW_SIZE_BYTES)

        message = f"{PERSISTED_OUTPUT_TAG}\n"
        message += f"Output too large ({size_str}). Full output saved to: {result.filepath}\n\n"
        message += f"Preview (first {preview_size_str}):\n"
        message += result.preview
        message += "\n...\n" if result.has_more else "\n"
        message += PERSISTED_OUTPUT_CLOSING_TAG
        return message


class CleanupPolicy:
    """Manages cleanup of old tool result files."""

    def __init__(
        self,
        storage_manager: StorageManager,
        max_size_bytes: int = 100 * 1024 * 1024,  # 100MB default
        max_age_days: int = 7,  # 7 days default
    ):
        """Initialize CleanupPolicy.

        Args:
            storage_manager: The storage manager to clean up.
            max_size_bytes: Maximum total size of tool results directory.
            max_age_days: Maximum age of files in days.
        """
        self.storage = storage_manager
        self.max_size_bytes = max_size_bytes
        self.max_age_days = max_age_days

    def should_clean(self) -> bool:
        """Check if cleanup is needed based on size or age."""
        tool_results_dir = self.storage.tool_results_dir
        if not tool_results_dir.exists():
            return False

        # Check total size
        total_size = sum(
            f.stat().st_size for f in tool_results_dir.iterdir() if f.is_file()
        )
        if total_size > self.max_size_bytes:
            return True

        # Check age of oldest file
        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        for filepath in tool_results_dir.iterdir():
            if filepath.is_file():
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                if mtime < cutoff:
                    return True

        return False

    def cleanup(self) -> int:
        """Run cleanup, removing oldest/-largest files as needed.

        Returns:
            Number of files removed.
        """
        removed = 0
        tool_results_dir = self.storage.tool_results_dir
        if not tool_results_dir.exists():
            return 0

        # Get all files sorted by age (oldest first)
        files = []
        for f in tool_results_dir.iterdir():
            if f.is_file():
                files.append(
                    (
                        f,
                        datetime.fromtimestamp(f.stat().st_mtime),
                        f.stat().st_size,
                    )
                )

        files.sort(key=lambda x: x[1])  # Sort by age

        # First, remove old files
        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        for f, mtime, _ in files[:]:
            if mtime < cutoff:
                try:
                    f.unlink()
                    files.remove((f, mtime, f.stat().st_size))
                    removed += 1
                except OSError:
                    pass

        # Then, if still over size, remove oldest until under limit
        if files:
            total_size = sum(size for _, _, size in files)
            while total_size > self.max_size_bytes and files:
                f, mtime, size = files.pop(0)
                try:
                    f.unlink()
                    total_size -= size
                    removed += 1
                except OSError:
                    pass

        return removed

    def clear_all(self) -> int:
        """Manually clear all persisted tool results.

        Returns:
            Number of files removed.
        """
        removed = 0
        tool_results_dir = self.storage.tool_results_dir
        if not tool_results_dir.exists():
            return 0

        for f in tool_results_dir.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                    removed += 1
                except OSError:
                    pass

        return removed


# --- Tool Result Budget Enforcement ---


def get_persistence_threshold(
    tool_name: str,
    declared_max_result_size_chars: int,
    tool_overrides: dict[str, int] | None = None,
) -> int:
    """Resolve the effective persistence threshold for a tool.

    Args:
        tool_name: Name of the tool.
        declared_max_result_size_chars: Tool's declared max result size.
        tool_overrides: Optional override map (tool_name -> threshold).

    Returns:
        Effective threshold in characters.
    """
    # Infinity = hard opt-out. Read tool should never persist its output
    # as reading it back would be circular.
    if not isinstance(
        declared_max_result_size_chars, (int, float)
    ) or not math.isfinite(declared_max_result_size_chars):
        return declared_max_result_size_chars

    # Check override
    if tool_overrides and tool_name in tool_overrides:
        override = tool_overrides[tool_name]
        if (
            isinstance(override, (int, float))
            and math.isfinite(override)
            and override > 0
        ):
            return int(override)

    return min(declared_max_result_size_chars, DEFAULT_MAX_RESULT_SIZE_CHARS)


def is_tool_result_empty(content: str | list[dict[str, Any]] | None) -> bool:
    """Check if tool result content is empty or effectively empty."""
    if not content:
        return True
    if isinstance(content, str):
        return content.strip() == ""
    if isinstance(content, list):
        if len(content) == 0:
            return True
        return all(
            isinstance(block, dict)
            and block.get("type") == "text"
            and (not block.get("text") or block.get("text", "").strip() == "")
            for block in content
        )
    return False


def has_image_block(content: list[dict[str, Any]]) -> bool:
    """Check if content contains image blocks."""
    if not isinstance(content, list):
        return False
    return any(
        isinstance(block, dict) and block.get("type") == "image" for block in content
    )


def content_size(content: str | list[dict[str, Any]]) -> int:
    """Calculate the size of tool result content."""
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(
            len(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return 0


def build_tool_name_map(messages: list[dict[str, Any]]) -> dict[str, str]:
    """Build tool_use_id -> tool_name map from messages."""
    result = {}
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        content = msg.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_use":
                result[block.get("id", "")] = block.get("name", "")
    return result


def collect_candidates_by_message(
    messages: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Collect candidate tool_result blocks grouped by API-level user message.

    Returns list of groups, where each group is a list of candidates.
    """
    groups = []
    current = []
    seen_assistant_ids = set()

    def flush():
        if current:
            groups.append(current)
            current.clear()

    for msg in messages:
        if msg.get("type") == "user":
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") != "tool_result":
                        continue
                    if not block.get("content"):
                        continue
                    if is_content_already_compacted(block.get("content")):
                        continue
                    if has_image_block(block.get("content", [])):
                        continue
                    current.append(
                        {
                            "tool_use_id": block.get("tool_use_id", ""),
                            "content": block.get("content"),
                            "size": content_size(block.get("content")),
                        }
                    )
        elif msg.get("type") == "assistant":
            msg_id = msg.get("message", {}).get("id", "")
            if msg_id not in seen_assistant_ids:
                flush()
                seen_assistant_ids.add(msg_id)

    flush()
    return groups


def is_content_already_compacted(content: str | list | None) -> bool:
    """Check if content was already compacted by budget."""
    return isinstance(content, str) and content.startswith(PERSISTED_OUTPUT_TAG)


def select_fresh_to_replace(
    fresh: list[dict[str, Any]],
    frozen_size: int,
    limit: int,
) -> list[dict[str, Any]]:
    """Select largest fresh results to replace until under budget."""
    sorted_fresh = sorted(fresh, key=lambda x: x.get("size", 0), reverse=True)
    selected = []
    remaining = frozen_size + sum(c.get("size", 0) for c in fresh)

    for c in sorted_fresh:
        if remaining <= limit:
            break
        selected.append(c)
        remaining -= c.get("size", 0)

    return selected


async def enforce_tool_result_budget(
    messages: list[dict[str, Any]],
    state: ContentReplacementState,
    skip_tool_names: set[str] | None = None,
    storage: StorageManager | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Enforce per-message budget on aggregate tool result size.

    Args:
        messages: List of messages to process.
        state: Content replacement state for tracking decisions.
        skip_tool_names: Set of tool names to skip (e.g., Read tool).
        storage: Optional storage manager for persistence.

    Returns:
        Tuple of (processed messages, newly replaced records).
    """
    skip_tool_names = skip_tool_names or set()
    candidates_by_message = collect_candidates_by_message(messages)

    name_by_tool_use_id = build_tool_name_map(messages)

    def should_skip(tool_use_id: str) -> bool:
        tool_name = name_by_tool_use_id.get(tool_use_id, "")
        return tool_name in skip_tool_names

    limit = MAX_TOOL_RESULTS_PER_MESSAGE_CHARS

    replacement_map: dict[str, str] = {}
    to_persist: list[dict[str, Any]] = []
    newly_replaced: list[dict[str, Any]] = []

    for candidates in candidates_by_message:
        # Partition by prior decision
        must_reapply = []
        frozen = []
        fresh = []

        for c in candidates:
            tid = c.get("tool_use_id", "")
            if tid in state.replacements:
                must_reapply.append({**c, "replacement": state.replacements[tid]})
            elif tid in state.seen_ids:
                frozen.append(c)
            else:
                fresh.append(c)

        # Re-apply cached replacements
        for c in must_reapply:
            replacement_map[c["tool_use_id"]] = c["replacement"]

        # No fresh candidates - just mark all as seen
        if not fresh:
            for c in candidates:
                state.seen_ids.add(c.get("tool_use_id", ""))
            continue

        # Filter skipped tools
        skipped = [c for c in fresh if should_skip(c.get("tool_use_id", ""))]
        for c in skipped:
            state.seen_ids.add(c.get("tool_use_id", ""))

        eligible = [c for c in fresh if not should_skip(c.get("tool_use_id", ""))]

        frozen_size = sum(c.get("size", 0) for c in frozen)

        selected = select_fresh_to_replace(eligible, frozen_size, limit)
        selected_ids = set(c.get("tool_use_id", "") for c in selected)

        # Mark non-selected as seen
        for c in candidates:
            tid = c.get("tool_use_id", "")
            if tid not in selected_ids:
                state.seen_ids.add(tid)

        if not selected:
            continue

        to_persist.extend(selected)

    # Persist selected candidates
    if storage and to_persist:
        for candidate in to_persist:
            tid = candidate.get("tool_use_id", "")
            content = candidate.get("content")

            result = storage.persist(content, tid)
            if isinstance(result, PersistToolResultError):
                state.seen_ids.add(tid)
                continue

            message = PreviewGenerator.build_message(result)
            replacement_map[tid] = message
            state.seen_ids.add(tid)
            state.replacements[tid] = message
            newly_replaced.append(
                {
                    "kind": "tool-result",
                    "tool_use_id": tid,
                    "replacement": message,
                }
            )

    # Apply replacements to messages
    if not replacement_map:
        return messages, newly_replaced

    processed = []
    for msg in messages:
        if msg.get("type") != "user":
            processed.append(msg)
            continue

        content = msg.get("message", {}).get("content", [])
        if not isinstance(content, list):
            processed.append(msg)
            continue

        needs_replace = any(
            block.get("type") == "tool_result"
            and block.get("tool_use_id", "") in replacement_map
            for block in content
        )

        if not needs_replace:
            processed.append(msg)
            continue

        new_content = []
        for block in content:
            if block.get("type") == "tool_result":
                tid = block.get("tool_use_id", "")
                if tid in replacement_map:
                    new_content.append({**block, "content": replacement_map[tid]})
                    continue
            new_content.append(block)

        processed.append(
            {
                **msg,
                "message": {
                    **msg.get("message", {}),
                    "content": new_content,
                },
            }
        )

    return processed, newly_replaced


# --- Utility Functions ---


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


import math  # noqa: E402


# --- Integration API ---


class ToolResultStorage:
    """Main integration class for tool result persistence."""

    def __init__(
        self,
        workspace_dir: Path | None = None,
        max_size_bytes: int = 100 * 1024 * 1024,
        max_age_days: int = 7,
        tool_overrides: dict[str, int] | None = None,
    ):
        """Initialize ToolResultStorage.

        Args:
            workspace_dir: Workspace directory for storage.
            max_size_bytes: Maximum storage size.
            max_age_days: Maximum file age.
            tool_overrides: Per-tool threshold overrides.
        """
        self.storage = StorageManager(base_dir=workspace_dir or Path.cwd() / ".n-xyme")
        self.cleanup = CleanupPolicy(
            self.storage,
            max_size_bytes=max_size_bytes,
            max_age_days=max_age_days,
        )
        self.tool_overrides = tool_overrides or {}

    def should_persist(
        self,
        content_size: int,
        tool_name: str,
        declared_max_size: int = DEFAULT_MAX_RESULT_SIZE_CHARS,
    ) -> bool:
        """Check if a tool result should be persisted based on size.

        Args:
            content_size: Size of the content in characters.
            tool_name: Name of the tool.
            declared_max_size: Tool's declared max result size.

        Returns:
            True if should persist.
        """
        threshold = get_persistence_threshold(
            tool_name, declared_max_size, self.tool_overrides
        )
        # Check for Infinity
        if not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
            return False
        return content_size > threshold

    async def persist_and_replace(
        self,
        tool_result_block: dict[str, Any],
        tool_name: str,
        declared_max_size: int = DEFAULT_MAX_RESULT_SIZE_CHARS,
    ) -> dict[str, Any]:
        """Persist large tool result and return preview-replaced block.

        Args:
            tool_result_block: The tool result block to process.
            tool_name: Name of the tool.
            declared_max_size: Tool's declared max result size.

        Returns:
            Modified tool result block (preview instead of full content).
        """
        content = tool_result_block.get("content")

        # Handle empty content - inject marker
        if is_tool_result_content_empty(content):
            return {
                **tool_result_block,
                "content": f"({tool_name} completed with no output)",
            }

        # Skip for image content
        if isinstance(content, list) and has_image_block(content):
            return tool_result_block

        size = content_size(content)
        threshold = get_persistence_threshold(
            tool_name, declared_max_size, self.tool_overrides
        )

        # Check threshold
        if not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
            return tool_result_block

        if size <= threshold:
            return tool_result_block

        # Persist
        tool_use_id = tool_result_block.get("tool_use_id", str(uuid.uuid4()))
        result = self.storage.persist(content, tool_use_id)

        if isinstance(result, PersistToolResultError):
            return tool_result_block

        # Replace with preview message
        message = PreviewGenerator.build_message(result)
        return {**tool_result_block, "content": message}

    def get_persisted(self, tool_use_id: str) -> str | None:
        """Retrieve full persisted result by ID.

        Args:
            tool_use_id: The tool use ID to retrieve.

        Returns:
            The full content, or None if not found.
        """
        return self.storage.load(tool_use_id)

    def list_persisted(self) -> list[ToolResultMetadata]:
        """List all persisted results with metadata."""
        return self.storage.list_all()

    def clear_persisted(self) -> int:
        """Manually clear all persisted results.

        Returns:
            Number of files removed.
        """
        return self.storage.clear_all()

    def run_cleanup(self) -> int:
        """Run cleanup policy.

        Returns:
            Number of files removed.
        """
        return self.cleanup.cleanup()


def is_tool_result_content_empty(
    content: str | list[dict[str, Any]] | None,
) -> bool:
    """Check if tool result content is empty or effectively empty."""
    return is_tool_result_empty(content)
