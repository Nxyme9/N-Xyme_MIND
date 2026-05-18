"""
Dataset loading and processing for RosEnna Trainer.
Loads all .jsonl files and normalizes to {query, tool, text} format.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from torch.utils.data import Dataset
import torch


class RosEnnaDataset(Dataset):
    """
    Dataset for Rosetta semantic routing training.
    Each item contains query, tool name, and tool description.
    """

    def __init__(self, data_dir: str, min_examples_per_tool: int = 100):
        """
        Initialize dataset by loading all .jsonl files from data_dir.

        Args:
            data_dir: Directory containing .jsonl training files
            min_examples_per_tool: Minimum examples required per tool
        """
        self.data_dir = data_dir
        self.min_examples_per_tool = min_examples_per_tool
        self.examples: List[Dict] = []
        self.tool_counts: Dict[str, int] = {}

        self._load_all()

    def _load_all(self) -> None:
        """Load all .jsonl files from data directory."""
        if not os.path.exists(self.data_dir):
            return

        for filename in os.listdir(self.data_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(self.data_dir, filename)
                self._load_file(filepath)

        self._filter_by_min_examples()

    def _load_file(self, filepath: str) -> None:
        """Load a single .jsonl file and normalize entries."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        normalized = self._normalize_entry(entry)
                        if normalized:
                            self.examples.append(normalized)
                            tool = normalized['tool']
                            self.tool_counts[tool] = self.tool_counts.get(tool, 0) + 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Warning: Could not load {filepath}: {e}")

    def _normalize_entry(self, entry: Dict) -> Optional[Dict]:
        """
        Normalize entry to {query, tool, text} format.
        Handles various input formats.
        """
        query = entry.get('query') or entry.get('instruction') or entry.get('text') or entry.get('input')
        tool = entry.get('tool') or entry.get('label') or entry.get('target')
        text = entry.get('text') or entry.get('description') or entry.get('tool_description') or entry.get('output')

        if not query or not tool:
            return None

        if not text:
            from data.tools import get_tool_description
            text = get_tool_description(tool)
            if not text:
                return None

        return {
            'query': str(query).strip(),
            'tool': str(tool).strip(),
            'text': str(text).strip()
        }

    def _filter_by_min_examples(self) -> None:
        """Filter out tools with fewer than min_examples_per_tool examples."""
        valid_tools = {
            tool for tool, count in self.tool_counts.items()
            if count >= self.min_examples_per_tool
        }
        self.examples = [ex for ex in self.examples if ex['tool'] in valid_tools]
        self.tool_counts = {t: c for t, c in self.tool_counts.items() if t in valid_tools}

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict:
        return self.examples[idx]

    def get_tool_counts(self) -> Dict[str, int]:
        """Return the count of examples per tool."""
        return self.tool_counts.copy()

    def get_unique_tools(self) -> List[str]:
        """Return list of unique tool names in dataset."""
        return list(self.tool_counts.keys())


def load_all(data_dir: str, min_examples_per_tool: int = 100) -> RosEnnaDataset:
    """
    Load all .jsonl files from data_dir and return normalized dataset.

    Args:
        data_dir: Directory containing .jsonl training files
        min_examples_per_tool: Minimum examples required per tool

    Returns:
        RosEnnaDataset with normalized {query, tool, text} entries
    """
    return RosEnnaDataset(data_dir, min_examples_per_tool)


class ContrastiveDataset(Dataset):
    """
    Dataset that provides contrastive triplets: (anchor, positive, negative).
    Used for contrastive learning training.
    """

    def __init__(self, base_dataset: RosEnnaDataset):
        """
        Initialize with a base RosEnnaDataset.

        Args:
            base_dataset: The normalized RosEnnaDataset
        """
        self.base = base_dataset
        self.tools = base_dataset.get_unique_tools()
        self.tool_to_indices = self._build_tool_index()

    def _build_tool_index(self) -> Dict[str, List[int]]:
        """Build index mapping tool names to example indices."""
        index = {tool: [] for tool in self.tools}
        for idx, example in enumerate(self.base.examples):
            tool = example['tool']
            if tool in index:
                index[tool].append(idx)
        return index

    def __len__(self) -> int:
        return len(self.base)

    def __getitem__(self, idx: int) -> Dict:
        """Get a contrastive triplet for the given index."""
        example = self.base[idx]
        anchor = example['query']
        positive = example['text']
        tool = example['tool']

        negative_tool = self._get_negative_tool(tool)
        negative_text = self._get_tool_text(negative_tool)

        return {
            'anchor': anchor,
            'positive': positive,
            'negative': negative_text,
            'positive_tool': tool,
            'negative_tool': negative_tool
        }

    def _get_negative_tool(self, positive_tool: str) -> str:
        """Get a random different tool as negative."""
        candidates = [t for t in self.tools if t != positive_tool]
        if candidates:
            import random
            return random.choice(candidates)
        return positive_tool

    def _get_tool_text(self, tool: str) -> str:
        """Get tool description text."""
        for example in self.base.examples:
            if example['tool'] == tool:
                return example['text']
        from data.tools import get_tool_text
        return get_tool_text(tool)