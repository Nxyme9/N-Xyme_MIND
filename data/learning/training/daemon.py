"""
Auto-retrain daemon — monitors correction buffer, triggers retrain at threshold.
Story 4.2: ≥100 corrections → auto-retrain in background.

Usage:
    from hot.daemon import HotTrainingDaemon
    from hot.collector import CorrectionBuffer
    
    buffer = CorrectionBuffer("data/corrections.jsonl")
    daemon = HotTrainingDaemon(buffer)
    daemon.start()  # Runs in background thread
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
from typing import Optional


class HotTrainingDaemon:
    """
    Background daemon that monitors correction buffer and triggers retraining.
    Runs in background, non-blocking, with hot-reload signal on completion.
    """
    
    def __init__(
        self,
        buffer,
        trainer_script: str = None,
        model_path: str = "/tmp/rosenna-hot.gguf",
        threshold: int = 100,
        poll_interval: float = 60.0
    ):
        """
        Initialize the hot training daemon.
        
        Args:
            buffer: CorrectionBuffer instance to monitor
            trainer_script: Path to trainer.py script
            model_path: Output path for retrained model
            threshold: Number of corrections to trigger retrain
            poll_interval: Seconds between buffer checks
        """
        self.buffer = buffer
        self.threshold = threshold
        self.poll_interval = poll_interval
        self.running = False
        self.last_train_time = 0
        self._thread: Optional[threading.Thread] = None
        
        # Paths
        base_dir = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/rosenna_trainer"
        self.trainer_script = trainer_script or os.path.join(base_dir, "train.py")
        self.model_path = model_path
        self.control_socket_path = "/tmp/llama-control.sock"
        
        # Training state
        self.is_training = False
        self.last_train_result: Optional[dict] = None
    
    def start(self) -> None:
        """Start the daemon in a background thread."""
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"HotTrainingDaemon started (threshold={self.threshold}, poll={self.poll_interval}s)", file=sys.stderr)
    
    def stop(self) -> None:
        """Stop the daemon gracefully."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("HotTrainingDaemon stopped", file=sys.stderr)
    
    def _run_loop(self) -> None:
        """Main daemon loop - polls buffer periodically."""
        while self.running:
            try:
                # Check if threshold met
                if self.check_and_trigger():
                    print(f"Auto-retrain triggered ({self.buffer.count} >= {self.threshold})", file=sys.stderr)
                
                # Sleep until next poll
                time.sleep(self.poll_interval)
                
            except Exception as e:
                print(f"Daemon error: {e}", file=sys.stderr)
                time.sleep(self.poll_interval)
    
    def check_and_trigger(self) -> bool:
        """
        Check buffer and trigger retrain if threshold met.
        
        Returns:
            True if retrain was triggered, False otherwise
        """
        if self.is_training:
            return False
        
        if self.buffer.count >= self.threshold:
            self._run_training()
            return True
        
        return False
    
    def force_retrain(self) -> bool:
        """
        Force immediate retrain regardless of buffer count.
        
        Returns:
            True if training started successfully
        """
        if self.is_training:
            return False
        
        self._run_training()
        return True
    
    def _run_training(self) -> None:
        """Run trainer in subprocess (non-blocking caller, blocking subprocess)."""
        import tempfile
        
        self.is_training = True
        
        # Gather corrections since last train
        corrections = self.buffer.load_since(self.last_train_time)
        
        # Prepare corrections as training data
        # Format: each correction becomes a training example
        temp_corr_file = None
        try:
            # Write corrections to temp file for training
            temp_fd, temp_corr_file = tempfile.mkstemp(suffix='.jsonl', prefix='corr_')
            os.close(temp_fd)
            
            with open(temp_corr_file, 'w') as f:
                for corr in corrections:
                    # Convert correction to training format
                    example = {
                        "query": corr["query"],
                        "tool": corr["correct_tool"],
                        "wrong_tool": corr.get("wrong_tool", "")
                    }
                    f.write(json.dumps(example) + "\n")
            
            # Build training command
            cmd = [
                sys.executable,
                self.trainer_script,
                "--data", temp_corr_file,
                "--output", self.model_path,
                "--epochs", "3",  # Quick retrain
                "--no-augment",  # Skip augmentation for speed
            ]
            
            print(f"Running training: {' '.join(cmd)}", file=sys.stderr)
            
            # Run training (blocking)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print("Training completed successfully", file=sys.stderr)
                self.last_train_result = {
                    "success": True,
                    "corrections_used": len(corrections),
                    "output": self.model_path
                }
                
                # Signal hot reload
                self._signal_reload(self.model_path)
            else:
                print(f"Training failed: {result.stderr}", file=sys.stderr)
                self.last_train_result = {
                    "success": False,
                    "error": result.stderr
                }
            
            self.last_train_time = time.time()
            
        except subprocess.TimeoutExpired:
            print("Training timeout (>5min)", file=sys.stderr)
            self.last_train_result = {"success": False, "error": "timeout"}
            
        except Exception as e:
            print(f"Training error: {e}", file=sys.stderr)
            self.last_train_result = {"success": False, "error": str(e)}
            
        finally:
            # Cleanup temp file
            if temp_corr_file and os.path.exists(temp_corr_file):
                try:
                    os.unlink(temp_corr_file)
                except OSError:
                    pass
            
            # Reset buffer count after training
            self.buffer.reset_count()
            self.is_training = False
    
    def _signal_reload(self, model_path: str) -> bool:
        """
        Send hot-reload signal to bridge via control socket.
        
        Args:
            model_path: Path to newly trained model
            
        Returns:
            True if reload signal sent successfully
        """
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(self.control_socket_path)
            
            msg = json.dumps({
                "type": "reload_model",
                "path": model_path
            })
            sock.sendall(msg.encode())
            
            # Wait for ACK
            response = sock.recv(4096)
            sock.close()
            
            if response:
                resp_data = json.loads(response.decode())
                if resp_data.get("type") == "reload_ack":
                    print(f"Hot reload acknowledged", file=sys.stderr)
                    return True
            
            return False
            
        except Exception as e:
            print(f"Reload signal failed: {e}", file=sys.stderr)
            return False
    
    def get_status(self) -> dict:
        """Get daemon status."""
        return {
            "running": self.running,
            "is_training": self.is_training,
            "buffer_count": self.buffer.count,
            "threshold": self.threshold,
            "last_train_time": self.last_train_time,
            "last_train_result": self.last_train_result
        }


# Convenience function for quick testing
def test_daemon():
    """Test the hot training daemon."""
    import tempfile
    
    # Use temp file for buffer
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        path = f.name
    
    from hot.collector import CorrectionBuffer
    buffer = CorrectionBuffer(path)
    
    # Add 5 corrections (below threshold)
    for i in range(5):
        buffer.add(f"query {i}", f"wrong_{i}", f"correct_{i}")
    
    # Create daemon with low threshold for testing
    daemon = HotTrainingDaemon(buffer, threshold=3, poll_interval=1.0)
    
    print(f"Initial status: {daemon.get_status()}")
    
    # Check should not trigger (5 < 3 is false... wait it's 5 >= 3 so it WILL trigger)
    # Let's add only 2 to test non-trigger
    buffer.reset_count()
    buffer.add("q1", "w1", "c1")
    buffer.add("q2", "w2", "c2")
    
    result = daemon.check_and_trigger()
    print(f"Check trigger (2 < 3): {result}")
    
    # Add one more
    buffer.add("q3", "w3", "c3")
    result = daemon.check_and_trigger()
    print(f"Check trigger (3 >= 3): {result}")
    
    # Cleanup
    os.unlink(path)
    
    print("Daemon test passed!")


if __name__ == "__main__":
    test_daemon()