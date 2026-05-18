"""
communication/telegram.mojo — Telegram DM hook.
Compiles to one ELF, uses Python interop for HTTPS (same as daemon.mojo).

Usage:
  TELEGRAM_BOT_TOKEN="xxx" PABLO_TELEGRAM_ID="123" mojo communication/telegram.mojo
  echo "hey pablo from my gpu" | TELEGRAM_BOT_TOKEN="xxx" PABLO_TELEGRAM_ID="123" ./telegram
"""
from std.python import Python

def main() raises:
    var py_os = Python.import_module("os")
    var py_sys = Python.import_module("sys")
    var py_json = Python.import_module("json")
    var py_urllib = Python.import_module("urllib.request")
    var py_urllib_error = Python.import_module("urllib.error")

    var py_builtins = Python.import_module("builtins")
    
    # Read token + chat ID from env
    var bot_token = String(py_os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    var chat_id = String(py_os.environ.get("PABLO_TELEGRAM_ID", ""))

    if len(bot_token) == 0:
        print("Set TELEGRAM_BOT_TOKEN env var (get from @BotFather)")
        return
    if len(chat_id) == 0:
        print("Set PABLO_TELEGRAM_ID env var")
        return

    # Read message from stdin
    var lines = py_sys.stdin.readlines()
    var message = String("")
    for line in lines:
        message += String(line)

    message = String(message.strip())
    if len(message) == 0:
        print("Pipe a message: echo 'hello' | ./telegram")
        return

    # Send via Telegram Bot API — use Python's urllib properly
    var url = "https://api.telegram.org/bot" + bot_token + "/sendMessage"
    var payload_str = String("{\"chat_id\": \"") + chat_id + String("\", \"text\": \"") + message.replace("\"", "\\\"") + String("\"}")
    var payload_data = py_builtins.bytes(payload_str, "utf-8")
    var headers = py_builtins.dict()
    headers["Content-Type"] = "application/json"
    var req = py_urllib.Request(url, payload_data, headers)

    try:
        var resp = py_urllib.urlopen(req)
        var result = py_json.loads(resp.read())
        if result.get("ok"):
            print("OK Telegram DM sent")
        else:
            print("FAIL Telegram error: " + String(result.get("description", "unknown")))
    except:
        print("FAIL Failed to send. Check your token and network.")