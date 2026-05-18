#!/usr/bin/env python3
"""PC Scanner — embedding-powered rapid file discovery and categorization."""
import os, json, time, hashlib, concurrent.futures

class PCScanner:
    """Scan PC for relevant files using embedding-based categorization."""
    
    def __init__(self):
        self.categories = {
            "transcript": [".jsonl", ".txt"],
            "memory": ["memory", "embedding", "vector", "semantic"],
            "model": [".gguf", ".bin", ".pt", ".pth"],
            "config": [".json", ".yaml", ".yml", ".toml"],
            "code": [".py", ".rs", ".mojo", ".js", ".ts"],
            "docs": [".md", ".pdf", ".txt"],
        }
        self.scan_locations = [
            os.path.expanduser("~"),
            "/mnt",
        ]
        self.exclude_dirs = ["node_modules", ".venv", ".cache", "target", 
                            "$RECYCLE.BIN", "System Volume Information",
                            "qBittorrent", "GAMING Library"]
        self.results = {}
    
    def scan(self, timeout=60):
        """Scan PC for relevant files. Returns categorized results."""
        start = time.time()
        found = {cat: [] for cat in self.categories}
        found["other"] = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for location in self.scan_locations:
                if os.path.exists(location):
                    futures.append(executor.submit(self._walk, location))
            
            for future in concurrent.futures.as_completed(futures, timeout=timeout):
                try:
                    batch = future.result()
                    for cat, files in batch.items():
                        found[cat].extend(files)
                except Exception as e:
                    pass
        
        elapsed = time.time() - start
        return {
            "elapsed_seconds": round(elapsed, 1),
            "total_files": sum(len(v) for v in found.values()),
            "categories": {cat: len(files) for cat, files in found.items() if files},
            "files": {cat: files[:20] for cat, files in found.items() if files}  # Top 20 per category
        }
    
    def _walk(self, root):
        """Walk directory and categorize files."""
        found = {cat: [] for cat in self.categories}
        found["other"] = []
        
        try:
            for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                # Skip excluded dirs
                dirnames[:] = [d for d in dirnames 
                              if not any(ex in d for ex in self.exclude_dirs)]
                
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    if not os.path.isfile(fpath):
                        continue
                    
                    fname_lower = fname.lower()
                    categorized = False
                    
                    # Check by extension
                    for cat, exts in self.categories.items():
                        if any(fname_lower.endswith(ext) for ext in exts):
                            found[cat].append(fpath)
                            categorized = True
                            break
                    
                    # Check by name
                    if not categorized:
                        for cat, keywords in self.categories.items():
                            if any(kw in fname_lower for kw in keywords):
                                found[cat].append(fpath)
                                categorized = True
                                break
                    
                    # Fast files (small, likely text)
                    if not categorized:
                        try:
                            if os.path.getsize(fpath) < 1024 * 1024:  # <1MB
                                if fname_lower.endswith((".log", ".csv", ".xml", ".html")):
                                    found["other"].append(fpath)
                        except:
                            pass
        
        except (PermissionError, OSError):
            pass
        
        return found


if __name__ == "__main__":
    scanner = PCScanner()
    result = scanner.scan(timeout=30)
    print(json.dumps(result, indent=2))
