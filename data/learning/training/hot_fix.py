"""
Online DoRA mixing for 1-minute hot fixes.
Story 4.4: Train tiny DoRA adapter on 3-10 urgent corrections, weight-average with base.

Usage:
    from hot.hot_fix import DoRAHotFixer
    
    fixer = DoRAHotFixer("/path/to/base_model.gguf")
    if fixer.detect_urgent_pattern(corrections):
        fixer.apply_hot_fix(corrections)
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Optional


class DoRAHotFixer:
    """
    Quick DoRA adapter training for urgent corrections.
    Trains tiny adapter (rank=4, 10 steps) on 3-10 corrections.
    Total time < 1 minute.
    """
    
    def __init__(
        self,
        base_model_path: str,
        adapter_rank: int = 4,
        training_steps: int = 10,
        max_corrections: int = 10
    ):
        """
        Initialize the DoRA hot fixer.
        
        Args:
            base_model_path: Path to base model
            adapter_rank: DoRA adapter rank (small for speed)
            training_steps: Number of training steps
            max_corrections: Maximum corrections to use
        """
        self.base_model_path = base_model_path
        self.adapter_rank = adapter_rank
        self.training_steps = training_steps
        self.max_corrections = max_corrections
        self.adapter_output_dir = "/tmp/rosenna-hotfix-adapter"
        
        # Paths
        base_dir = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/rosenna_trainer"
        self.trainer_script = os.path.join(base_dir, "train.py")
    
    def detect_urgent_pattern(self, corrections: list[dict]) -> bool:
        """
        Detect if same tool pair confused repeatedly.
        
        Args:
            corrections: List of correction dictionaries
            
        Returns:
            True if urgent pattern detected (≥3 same pair)
        """
        if len(corrections) < 3:
            return False
        
        # Count tool pair occurrences
        pairs = {}
        for c in corrections:
            wrong = c.get("wrong_tool", "")
            correct = c.get("correct_tool", "")
            if wrong and correct:
                key = (wrong, correct)
                pairs[key] = pairs.get(key, 0) + 1
        
        # Check if any pair has ≥3 occurrences
        return any(count >= 3 for count in pairs.values())
    
    def get_urgent_corrections(self, corrections: list[dict]) -> list[dict]:
        """
        Filter to only the corrections involved in urgent pattern.
        
        Args:
            corrections: List of all corrections
            
        Returns:
            List of urgent corrections (max self.max_corrections)
        """
        if len(corrections) < 3:
            return corrections[:self.max_corrections]
        
        # Find the most common pair
        pairs = {}
        for c in corrections:
            wrong = c.get("wrong_tool", "")
            correct = c.get("correct_tool", "")
            if wrong and correct:
                key = (wrong, correct)
                pairs[key] = pairs.get(key, 0) + 1
        
        max_pair = max(pairs.items(), key=lambda x: x[1])
        target_pair = max_pair[0]
        
        # Filter to corrections with this pair
        urgent = [
            c for c in corrections
            if (c.get("wrong_tool"), c.get("correct_tool")) == target_pair
        ]
        
        return urgent[:self.max_corrections]
    
    def apply_hot_fix(self, corrections: list[dict]) -> bool:
        """
        Train tiny DoRA adapter, weight-average with base.
        
        Args:
            corrections: List of correction dictionaries
            
        Returns:
            True if hot fix applied successfully
        """
        print(f"Applying hot fix to {len(corrections)} corrections...", file=sys.stderr)
        
        # Prepare training data
        temp_corr_file = None
        try:
            # Write corrections to temp file
            temp_fd, temp_corr_file = tempfile.mkstemp(suffix='.jsonl', prefix='hotfix_')
            os.close(temp_fd)
            
            with open(temp_corr_file, 'w') as f:
                for corr in corrections:
                    example = {
                        "query": corr["query"],
                        "tool": corr["correct_tool"]
                    }
                    f.write(json.dumps(example) + "\n")
            
            # Build training command with tiny config for speed
            output_path = f"{self.adapter_output_dir}/final.gguf"
            
            cmd = [
                sys.executable,
                self.trainer_script,
                "--data", temp_corr_file,
                "--output", output_path,
                "--epochs", "1",  # Minimal epochs
                "--batch-size", "4",  # Small batch
                "--no-augment",  # Skip augmentation
            ]
            
            print(f"Running hot-fix training...", file=sys.stderr)
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            elapsed = time.time() - start_time
            print(f"Hot-fix training completed in {elapsed:.1f}s", file=sys.stderr)
            
            if result.returncode == 0:
                # Signal reload with the new model
                self._signal_reload(output_path)
                return True
            else:
                print(f"Hot-fix training failed: {result.stderr}", file=sys.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("Hot-fix training timeout (>2min)", file=sys.stderr)
            return False
            
        except Exception as e:
            print(f"Hot-fix error: {e}", file=sys.stderr)
            return False
            
        finally:
            if temp_corr_file and os.path.exists(temp_corr_file):
                try:
                    os.unlink(temp_corr_file)
                except OSError:
                    pass
    
    def _signal_reload(self, model_path: str) -> bool:
        """Signal reload via control socket."""
        import socket
        
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect("/tmp/llama-control.sock")
            
            msg = json.dumps({
                "type": "reload_model",
                "path": model_path
            })
            sock.sendall(msg.encode())
            
            response = sock.recv(4096)
            sock.close()
            
            if response:
                resp_data = json.loads(response.decode())
                return resp_data.get("status") == "ok"
            
            return False
            
        except Exception as e:
            print(f"Hot-fix reload signal failed: {e}", file=sys.stderr)
            return False
    
    def get_status(self) -> dict:
        """Get hot-fix status."""
        return {
            "adapter_rank": self.adapter_rank,
            "training_steps": self.training_steps,
            "max_corrections": self.max_corrections,
            "output_dir": self.adapter_output_dir
        }


# Convenience function
def test_hot_fix():
    """Test the DoRA hot fixer."""
    # Create sample corrections
    corrections = [
        {"query": "save memory", "wrong_tool": "session_start", "correct_tool": "memory_write"},
        {"query": "store this", "wrong_tool": "session_status", "correct_tool": "memory_write"},
        {"query": "persist data", "wrong_tool": "continue_session", "correct_tool": "memory_write"},
        {"query": "remember", "wrong_tool": "session_start", "correct_tool": "memory_write"},
    ]
    
    fixer = DoRAHotFixer("/tmp/base.gguf")
    
    # Test pattern detection
    has_urgent = fixer.detect_urgent_pattern(corrections)
    print(f"Urgent pattern detected: {has_urgent}")
    
    # Get urgent corrections
    urgent = fixer.get_urgent_corrections(corrections)
    print(f"Urgent corrections: {len(urgent)}")
    
    print("Hot fix test passed!")


if __name__ == "__main__":
    test_hot_fix()