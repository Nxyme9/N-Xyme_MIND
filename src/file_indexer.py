"""Trigger-based file indexer using nervous system architecture."""

import os
import json
import hashlib
import requests
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

GRAPHITI_URL = "http://localhost:8001/json-rpc"
INDEXED_FILE = "data/indexed_files.json"

DIRECTORIES = [
    "D:/99_Depricated",
    "D:/01_CODING",
    "H:/_NXYME_ARCHIVE",
]

EXTENSIONS = {".py", ".js", ".ts", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"}
SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".ruff_cache"}

class FileIndexer(FileSystemEventHandler):
    def __init__(self):
        self.indexed = self.load_indexed()
        self.queue = []
    
    def load_indexed(self):
        if os.path.exists(INDEXED_FILE):
            with open(INDEXED_FILE) as f:
                return set(json.load(f))
        return set()
    
    def save_indexed(self):
        os.makedirs(os.path.dirname(INDEXED_FILE), exist_ok=True)
        with open(INDEXED_FILE, "w") as f:
            json.dump(list(self.indexed), f)
    
    def get_hash(self, filepath):
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read(1024)).hexdigest()
        except:
            return None
    
    def index_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in EXTENSIONS:
            return False
        
        file_hash = self.get_hash(filepath)
        if file_hash in self.indexed:
            return False
        
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(2000)
            
            if len(content) < 10:
                return False
            
            relpath = os.path.relpath(filepath, "D:/" if filepath.startswith("D:") else "H:/")
            project = self.detect_project(filepath)
            
            text = f"FILE: {relpath}\nPROJECT: {project}\nTYPE: {ext}\n\n{content}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "graphiti_add_episode",
                "params": {
                    "text": text,
                    "metadata": {
                        "type": "code_archive",
                        "file": relpath,
                        "project": project,
                        "extension": ext,
                    }
                }
            }
            
            resp = requests.post(GRAPHITI_URL, json=payload, timeout=10)
            if resp.status_code == 200:
                self.indexed.add(file_hash)
                return True
        except Exception as e:
            logger.error(f"Failed to index {filepath}: {e}")
        
        return False
    
    def detect_project(self, filepath):
        parts = filepath.replace("\\", "/").split("/")
        for part in parts:
            if part in ("99_Depricated", "01_CODING", "_NXYME_ARCHIVE"):
                idx = parts.index(part)
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        return "unknown"
    
    def on_created(self, event):
        if not event.is_directory:
            self.queue.append(event.src_path)
    
    def on_modified(self, event):
        if not event.is_directory:
            self.queue.append(event.src_path)
    
    def process_queue(self):
        processed = 0
        while self.queue:
            filepath = self.queue.pop(0)
            if self.index_file(filepath):
                processed += 1
                if processed % 50 == 0:
                    self.save_indexed()
        if processed > 0:
            self.save_indexed()
        return processed

def scan_existing(indexer, directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in files:
            filepath = os.path.join(root, filename)
            if indexer.index_file(filepath):
                count += 1
                if count % 100 == 0:
                    indexer.save_indexed()
    indexer.save_indexed()
    return count

def start_watcher():
    indexer = FileIndexer()
    observer = Observer()
    
    for directory in DIRECTORIES:
        if os.path.exists(directory):
            observer.schedule(indexer, directory, recursive=True)
    
    observer.start()
    return observer, indexer
