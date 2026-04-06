"""Serialization — JSON/MessagePack serialization"""

import json, logging
from typing import Any

logger = logging.getLogger(__name__)


class Serializer:
    @staticmethod
    def to_json(data: Any, indent: int = 2) -> str:
        return json.dumps(data, indent=indent, default=str)

    @staticmethod
    def from_json(text: str) -> Any:
        return json.loads(text)

    @staticmethod
    def to_msgpack(data: Any) -> bytes:
        try:
            import msgpack

            return msgpack.packb(data, default=str)
        except ImportError:
            return json.dumps(data, default=str).encode()

    @staticmethod
    def from_msgpack(data: bytes) -> Any:
        try:
            import msgpack

            return msgpack.unpackb(data)
        except ImportError:
            return json.loads(data.decode())

    @staticmethod
    def to_file(data: Any, path: str):
        Path(path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    @staticmethod
    def from_file(path: str) -> Any:
        return json.loads(Path(path).read_text(encoding="utf-8"))
