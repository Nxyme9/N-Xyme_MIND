#!/usr/bin/env python3
"""
N-Xyme Dictate - Standalone Launcher
Voice dictation system with UI and text injection
"""

import argparse
import os
import sys
import signal
import fcntl
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("nxyme_dictate")

LOCK_FILE = "/tmp/nxyme_dictate.lock"


def acquire_lock():
    """Acquire single-instance lock."""
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except BlockingIOError:
        try:
            with open(LOCK_FILE, 'r') as f:
                existing_pid = f.read().strip()
        except:
            existing_pid = "unknown"
        print(f"Already running (PID: {existing_pid}). Use 'pkill -f run_dictate.py' to stop first.")
        return None
    except Exception as e:
        print(f"Lock error: {e}")
        return None


def release_lock(lock_fd):
    """Release lock."""
    if lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        except:
            pass
        try:
            os.remove(LOCK_FILE)
        except:
            pass


def setup_signal_handler(app_ref):
    """Setup SIGTERM handler for clean shutdown."""
    def handle_sigterm(signum, frame):
        print("Received SIGTERM, shutting down...")
        if app_ref and hasattr(app_ref, 'shutdown'):
            app_ref.shutdown()
        sys.exit(0)
    signal.signal(signal.SIGTERM, handle_sigterm)


def main():
    lock_fd = acquire_lock()
    if lock_fd is None:
        return 1
    
    app_ref = [None]  # Mutable container for app reference
    
    parser = argparse.ArgumentParser(
        description="N-Xyme Dictate - Voice Dictation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Start with GUI (if PyQt6 available)
  %(prog)s --headless        # Start API server only
  %(prog)s --hotkey          # Register global hotkey
  %(prog)s --injection       # Enable text injection
  %(prog)s --test            # Run self-test
        """
    )
    
    parser.add_argument(
        "--headless", 
        action="store_true",
        help="Run without GUI (API server only)"
    )
    parser.add_argument(
        "--host", 
        default="127.0.0.1",
        help="API server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8765,
        help="API server port (default: 8765)"
    )
    parser.add_argument(
        "--hotkey",
        action="store_true",
        help="Enable global hotkey for dictation"
    )
    parser.add_argument(
        "--injection",
        action="store_true",
        help="Enable text injection into active applications"
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device for inference (default: auto)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run self-test and exit"
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        default=True,
        help="Launch PyQt6 GUI (default: enabled)"
    )
    parser.add_argument(
        "--realtime",
        action="store_true",
        default=False,
        help="Enable real-time partial results streaming (FASTER live typing)"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        default=False,
        help="Ultra-fast mode: no noise suppression + faster decoding"
    )

    args = parser.parse_args()
    
    # Add current directory to path for imports
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    
    # Add parent (nx_engine) for imports
    parent_dir = os.path.dirname(script_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    if args.test:
        print("Running self-test...")
        from nx_dictate import commands, metrics, text_processor
        print("✓ Commands module")
        print("✓ Metrics module") 
        print("✓ Text processor module")
        print("\nAll modules OK!")
        print("\nTo run full tests: PYTHONPATH=. pytest tests/")
        release_lock(lock_fd)
        return 0
    
    if args.headless:
        # Run API server only (headless mode)
        print(f"Starting N-Xyme Dictate API server on {args.host}:{args.port}")
        print("Use --ui to launch GUI (default)")
        
        try:
            from nx_dictate.__main__ import main as dictate_main
            result = dictate_main(
                host=args.host,
                port=args.port,
                hotkey=args.hotkey,
                injection=args.injection,
                model=args.model,
                device=args.device,
                realtime=args.realtime,
                fast=args.fast
            )
            release_lock(lock_fd)
            return result
        except ImportError as e:
            print(f"Error: {e}")
            print("Make sure dependencies are installed: pip install -r requirements.txt")
            return 1
    else:
        print("Starting N-Xyme Dictate with GUI...")
        
        try:
            from nx_dictate.dictate_app import DictationApp
            
            app = DictationApp()
            if not app.initialize():
                print("Failed to initialize dictation app")
                return 1
            
            app_ref[0] = app
            setup_signal_handler(app)
            
            from nx_dictate.ui import create_ui
            
            def on_toggle():
                print(">>> TOGGLE CALLBACK FIRED <<<")
                logger.info("Toggle recording triggered")
                app.toggle_recording()
            
            def on_quit():
                print(">>> QUIT CALLBACK FIRED <<<")
                logger.info("Quit requested")
                app.shutdown()
                ui.quit()
            
            ui = create_ui(on_toggle, on_quit)
            if not ui:
                print("Failed to create UI - falling back to headless")
                args.headless = True
                return main()
            
            def on_settings():
                print(">>> SETTINGS CALLBACK FIRED <<<")
                logger.info("Settings clicked")
                ui.show_settings()
            
            ui._tray.set_callback("show_settings", on_settings)
            ui._tray.set_callback("toggle", on_toggle)
            ui._tray.set_callback("quit", on_quit)
            
            def handle_state(state):
                ui.update_state(state)
            
            def handle_text(text):
                ui.notify_text(text)
            
            app.set_state_callback(handle_state)
            app.set_text_callback(handle_text)
            
            result = ui.run()
            release_lock(lock_fd)
            return result
            
        except ImportError as e:
            print(f"GUI Error: {e}")
            print("PyQt6 not available. Install with: pip install PyQt6")
            print("Falling back to headless mode...")
            release_lock(lock_fd)
            args.headless = True
            return main()


if __name__ == "__main__":
    sys.exit(main() or 0)