#!/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/bin/python3
"""phone.mojo — Phone → FIFO → jarvis-pc → Mojo Brain → response.
Your phone controls your PC via Telegram + local GPU.

Usage:
  export TELEGRAM_BOT_TOKEN="xxx"
  phone.mojo                    # Start listening
  # Then message your Telegram bot from your phone
"""
import os, sys, json, time, subprocess, urllib.request

ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
FIFO_PATH = "/tmp/jarvis_fifo"
MOJO_BRAIN_URL = "http://127.0.0.1:9091"

if not BOT_TOKEN:
    print("Set TELEGRAM_BOT_TOKEN env var (get from @BotFather)")
    sys.exit(1)

def send_to_fifo(text):
    """Send to jarvis-pc for PC control."""
    try:
        if not os.path.exists(FIFO_PATH):
            os.mkfifo(FIFO_PATH)
        fd = os.open(FIFO_PATH, os.O_RDWR | os.O_NONBLOCK)
        os.write(fd, (text + "\n").encode())
        os.close(fd)
        return True
    except:
        return False

def query_mojo_brain(text):
    """Get routing decision from mojo-brain."""
    try:
        req = urllib.request.Request(
            MOJO_BRAIN_URL,
            json.dumps({"query": text, "source": "phone"}).encode(),
            {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except:
        return {"decision": "cloud", "method": "fallback"}

def transcribe_audio(file_path):
    """Transcribe via local Whisper GPU."""
    try:
        result = subprocess.run(
            [f"{ROOT}/venv/bin/python3", "-c", f"""
import sys
sys.path.insert(0, "{ROOT}/venv/lib/python3.14/site-packages")
from faster_whisper import WhisperModel
model = WhisperModel("medium", device="cuda", compute_type="int8_float16")
segments, _ = model.transcribe("{file_path}", beam_size=5, vad_filter=True)
print(" ".join(s.text for s in segments))
"""],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        return f"(transcription failed)"

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data, {"Content-Type": "application/json"})
    urllib.request.urlopen(req)

print("=== 📱 Phone → FIFO → jarvis-pc → Mojo Brain ===")
print("  Send a message from your phone. PC commands execute locally.")
print("  Everything else routes through Mojo Brain.\n")

last_update_id = 0
while True:
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
        resp = urllib.request.urlopen(url)
        data = json.loads(resp.read())

        for update in data.get("result", []):
            last_update_id = update.get("update_id", 0)
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")
            voice = msg.get("voice", {})
            from_name = msg.get("from", {}).get("first_name", "Phone")

            if text:
                print(f"  📱 {from_name}: {text}")
                pc_sent = send_to_fifo(text)
                route = query_mojo_brain(text)
                decision = route.get("decision", "cloud")
                parts = [f'🤖 "{text}"']
                if pc_sent: parts.append(f"  → Jarvis PC processing")
                parts.append(f"  🧠 Mojo: {decision.upper()} ({route.get('method','?')})")
                send_telegram(chat_id, "\n".join(parts))

            if voice:
                print(f"  🎤 {from_name}: voice message")
                file_id = voice.get("file_id")
                furl = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
                fresp = json.loads(urllib.request.urlopen(furl).read())
                fpath = fresp.get("result", {}).get("file_path", "")
                if fpath:
                    dl_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fpath}"
                    urllib.request.urlretrieve(dl_url, "/tmp/phone-voice.ogg")
                    transcript = transcribe_audio("/tmp/phone-voice.ogg")
                    pc_sent = send_to_fifo(transcript)
                    route = query_mojo_brain(transcript)
                    decision = route.get("decision", "cloud")
                    parts = [f'🎤 You said: "{transcript}"']
                    if pc_sent: parts.append("  → PC pipeline triggered")
                    parts.append(f"  🧠 Mojo: {decision.upper()} (RTX 3080 Ti)")
                    send_telegram(chat_id, "\n".join(parts))

    except KeyboardInterrupt:
        print("\n  📱 Phone bridge disconnected.")
        break
    except Exception as e:
        if "timed out" not in str(e):
            print(f"  ⚠ {e}")
    time.sleep(0.5)
