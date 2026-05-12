from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import csv
from transformers import PreTrainedTokenizer


class DataLoader:
    def __init__(
        self,
        tokenizer: Optional[PreTrainedTokenizer] = None,
        max_length: int = 2048,
    ):
        self.tokenizer = tokenizer
        self.max_length = max_length

    def load_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    def load_csv(self, path: Path) -> List[Dict[str, Any]]:
        data = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data

    def load(self, path: Path) -> List[Dict[str, Any]]:
        if path.suffix == ".jsonl":
            return self.load_jsonl(path)
        elif path.suffix == ".csv":
            return self.load_csv(path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def tokenize(self, data: List[Dict[str, Any]], format: str = "default") -> List[Any]:
        if not self.tokenizer:
            return data

        formatter = DatasetFormatter()
        formatted = [formatter.format(item, format) for item in data]

        tokens = []
        for item in formatted:
            text = item.get("text") or item.get("content") or str(item)
            encoded = self.tokenizer(
                text,
                max_length=self.max_length,
                truncation=True,
                padding="max_length",
            )
            tokens.append(encoded)

        return tokens


class DatasetFormatter:
    FORMAT_TEMPLATES = {
        "default": {"text": "{text}"},
        "chatml": {
            "system": "<|im_start|>system\n{system}<|im_end|>\n",
            "user": "<|im_start|>user\n{user}<|im_end|>\n",
            "assistant": "<|im_start|>assistant\n{assistant}<|im_end|>\n",
        },
        "sharegpt": {
            "conversations": [
                {"from": "human", "value": "{user}"},
                {"from": "gpt", "value": "{assistant}"},
            ]
        },
    }

    def format(self, item: Dict[str, Any], format: str = "default") -> Dict[str, Any]:
        if format == "chatml":
            return self._format_chatml(item)
        elif format == "sharegpt":
            return self._format_sharegpt(item)
        else:
            return item

    def _format_chatml(self, item: Dict[str, Any]) -> Dict[str, Any]:
        messages = item.get("messages", [])
        if not messages:
            return item

        text = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                text += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                text += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                text += f"<|im_start|>assistant\n{content}<|im_end|>\n"

        return {"text": text}

    def _format_sharegpt(self, item: Dict[str, Any]) -> Dict[str, Any]:
        conversations = item.get("conversations", [])
        if not conversations:
            return item

        text = ""
        for msg in conversations:
            role = msg.get("from", "human")
            content = msg.get("value", "")
            if role == "human":
                text += f"Human: {content}\n"
            else:
                text += f"Assistant: {content}\n"

        return {"text": text}


class DPODataset:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]


class KTODataset:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]