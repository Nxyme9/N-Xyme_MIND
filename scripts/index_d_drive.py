"""Index all D: drive archives into Graphiti memory."""

import os
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime

GRAPHITI_URL = "http://localhost:8001/json-rpc"

DIRECTORIES_TO_INDEX = [
    "D:/99_Depricated/1_N-Xyme_MIND/src",
    "D:/99_Depricated/00_N-Xyme_MIND",
    "D:/99_Depricated/_bmad",
    "D:/99_Depricated/_toolbridge",
    "D:/99_Depricated/8_N-Xyme_SPINE",
    "D:/99_Depricated/6_N-Xyme_GRIND",
    "D:/99_Depricated/5_N-Xyme_LIVE",
    "D:/99_Depricated/4_N-Xyme_VIBE",
    "D:/99_Depricated/3_N-Xyme_NEXUS",
    "D:/99_Depricated/7_N-Xyme_UI",
    "D:/99_Depricated/99_Archive",
    "D:/01_CODING/00_N-Xyme_CATALYST",
]

BATCH_SIZE = 50

INDEXED_FILE = "data/indexed_files.json"


def load_indexed():
    if os.path.exists(INDEXED_FILE):
        with open(INDEXED_FILE) as f:
            return set(json.load(f))
    return set()


def save_indexed(indexed):
    os.makedirs(os.path.dirname(INDEXED_FILE), exist_ok=True)
    with open(INDEXED_FILE, "w") as f:
        json.dump(list(indexed), f)


def get_file_hash(filepath):
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read(1024)).hexdigest()
    except:
        return None


def index_file(filepath, project_name):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(2000)

        if len(content) < 10:
            return False

        ext = os.path.splitext(filepath)[1]
        filename = os.path.basename(filepath)
        relpath = os.path.relpath(filepath, "D:/")

        text = f"FILE: {relpath}\nPROJECT: {project_name}\nTYPE: {ext}\n\n{content}"

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "graphiti_add_episode",
            "params": {
                "text": text,
                "metadata": {
                    "type": "code_archive",
                    "file": relpath,
                    "project": project_name,
                    "extension": ext,
                    "size": os.path.getsize(filepath),
                },
            },
        }

        resp = requests.post(GRAPHITI_URL, json=payload, timeout=10)
        return resp.status_code == 200
    except:
        return False


def index_directory(dirpath, indexed):
    project_name = os.path.basename(dirpath)
    files_indexed = 0
    files_skipped = 0

    extensions = {".py", ".js", ".ts", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"}

    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [
            d for d in dirs if d not in {"node_modules", "__pycache__", ".git", ".ruff_cache"}
        ]

        for filename in files:
            filepath = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()

            if ext not in extensions:
                continue

            file_hash = get_file_hash(filepath)
            if file_hash in indexed:
                files_skipped += 1
                continue

            if index_file(filepath, project_name):
                indexed.add(file_hash)
                files_indexed += 1

            if files_indexed % 100 == 0 and files_indexed > 0:
                save_indexed(indexed)

    return files_indexed, files_skipped


def main():
    indexed = load_indexed()
    total_indexed = 0

    for dirpath in DIRECTORIES_TO_INDEX:
        if not os.path.exists(dirpath):
            continue

        print(f"Indexing {dirpath}...")
        files_indexed, files_skipped = index_directory(dirpath, indexed)
        total_indexed += files_indexed
        print(f"  Indexed: {files_indexed}, Skipped: {files_skipped}")

    save_indexed(indexed)
    print(f"\nTotal indexed: {total_indexed}")


if __name__ == "__main__":
    main()
