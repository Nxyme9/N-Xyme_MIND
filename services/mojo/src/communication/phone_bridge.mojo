"""
communication/phone_bridge.mojo — Phone→Mojo bridge via Telegram webhook.
Your phone sends voice/text → Telegram bot → this server → GPU → response.

Usage:
  TELEGRAM_BOT_TOKEN="xxx" mojo communication/phone_bridge.mojo
  # Then message your bot on Telegram from your phone
"""
from std.python import Python

def main() raises:
    var py_os = Python.import_module("os")
    var py_json = Python.import_module("json")
    var py_time = Python.import_module("time")
    var py_threading = Python.import_module("threading")
    var py_subprocess = Python.import_module("subprocess")
    var py_http_server = Python.import_module("http.server")
    var py_socketserver = Python.import_module("socketserver")
    var py_urllib = Python.import_module("urllib.request")
    var py_urllib_parse = Python.import_module("urllib.parse")

    var bot_token = String(py_os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    if len(bot_token) == 0:
        print("Set TELEGRAM_BOT_TOKEN env var")
        return

    var PORT = 9090
    var last_update_id = 0

    print("=== Phone Bridge (Mojo) ===")
    print("  Telegram bot polling on :" + String(PORT))
    print("  Send a message to your bot from your phone")
    print("")

    # Polling loop — checks Telegram for new messages
    while True:
        var url = "https://api.telegram.org/bot" + bot_token + "/getUpdates?offset=" + String(last_update_id + 1) + "&timeout=30"
        try:
            var resp = py_urllib.urlopen(url)
            var data = py_json.loads(resp.read())
            var results = data.get("result", Python.eval("[]"))

            for i in range(len(results)):
                var update = results[i]
                last_update_id = int(update.get("update_id", 0))
                var message = update.get("message", Python.eval("{}"))
                var chat_id = message.get("chat", Python.eval("{}")).get("id", 0)
                var text = String(message.get("text", ""))
                var from_name = String(message.get("from", Python.eval("{}")).get("first_name", "Unknown"))

                if len(text) > 0:
                    print("  Phone " + from_name + ": " + text)

                    # Route through GPU pipeline
                    var gpu_result = py_subprocess.run(
                        Python.eval("['sh', '-c', 'echo \"" + text.replace("\"", "\\\"") + "\" | /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/gpu-route']"),
                        capture_output=True, text=True
                    )
                    var route_info = gpu_result.stdout.strip()

                    # Generate response
                    var response = "Hey " + from_name + "! I heard you through my GPU. You said: " + text + "\n(Routed: " + route_info + ")"

                    # Send response back to phone
                    var send_url = "https://api.telegram.org/bot" + bot_token + "/sendMessage"
                    var payload = py_json.dumps(Python.eval("{'chat_id': " + String(chat_id) + ", 'text': '" + response.replace("'", "\\'") + "'}"))
                    var req = py_urllib.Request(send_url, payload.encode("utf-8"), Python.eval("{'Content-Type': 'application/json'}"))
                    py_urllib.urlopen(req)
                    print("  OK Response sent to " + from_name + "'s phone")

                # Handle voice messages
                var voice = message.get("voice", Python.eval("{}"))
                if voice:
                    var file_id = String(voice.get("file_id", ""))
                    print("  Voice message from " + from_name + " (file_id: " + file_id + ")")

                    # Get file path from Telegram
                    var file_url = "https://api.telegram.org/bot" + bot_token + "/getFile?file_id=" + file_id
                    var file_resp = py_urllib.urlopen(file_url)
                    var file_data = py_json.loads(file_resp.read())
                    var file_path = String(file_data.get("result", Python.eval("{}")).get("file_path", ""))

                    if len(file_path) > 0:
                        # Download and transcribe via local Whisper GPU
                        var download_url = "https://api.telegram.org/file/bot" + bot_token + "/" + file_path
                        py_urllib.urlretrieve(download_url, "/tmp/telegram-voice.ogg")

                        var transcribe_result = py_subprocess.run(
                            Python.eval("['/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/bin/python3', '-c', '''\nimport sys\nsys.path.insert(0, \"/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/lib/python3.14/site-packages\")\nfrom faster_whisper import WhisperModel\nmodel = WhisperModel(\"medium\", device=\"cuda\", compute_type=\"int8_float16\")\nsegments, _ = model.transcribe(\"/tmp/telegram-voice.ogg\", beam_size=5, vad_filter=True)\nprint(\" \".join(s.text for s in segments))\n''']"),
                            capture_output=True, text=True
                        )
                        var transcript = transcribe_result.stdout.strip()
                        if len(transcript) > 0:
                            var response = "I heard: \"" + transcript + "\" — processed on my local GPU"
                            var send_url = "https://api.telegram.org/bot" + bot_token + "/sendMessage"
                            var payload = py_json.dumps(Python.eval("{'chat_id': " + String(chat_id) + ", 'text': '" + response.replace("'", "\\'") + "'}"))
                            var req = py_urllib.Request(send_url, payload.encode("utf-8"), Python.eval("{'Content-Type': 'application/json'}"))
                            py_urllib.urlopen(req)
                            print("  OK Transcribed and sent back to phone")
        except:
            pass

        py_time.sleep(1)