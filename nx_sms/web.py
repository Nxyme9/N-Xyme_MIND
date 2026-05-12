from flask import Flask, request, redirect, url_for, flash, render_template_string
from nx_sms.core import NxSMS

app = Flask(__name__)
app.secret_key = "nx-sms-dev-key"


def get_key_status():
    try:
        sms = NxSMS()
        if hasattr(sms, "get_api_key_status"):
            return sms.get_api_key_status()
        return {"status": "NxSMS core loaded"}
    except Exception as e:
        return {"error": f"Core load failed: {str(e)}"}


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>NxSMS Web UI</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-top: 0; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #555; font-weight: bold; }
        input[type="tel"], textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box; }
        textarea { height: 120px; resize: vertical; }
        button { background: #007bff; color: white; border: none; padding: 12px 24px; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        .flash { padding: 12px; margin-bottom: 20px; border-radius: 4px; }
        .flash.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .status-box { margin-top: 30px; padding: 15px; background: #e9ecef; border-radius: 4px; }
        .status-box h3 { margin-top: 0; color: #333; }
        .key-item { margin: 5px 0; padding: 8px; background: white; border-radius: 3px; }
        .error-text { color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NxSMS Sender</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" action="/send">
            <div class="form-group">
                <label for="phone">Phone Number:</label>
                <input type="tel" id="phone" name="phone" required placeholder="+1234567890">
            </div>
            <div class="form-group">
                <label for="message">Message:</label>
                <textarea id="message" name="message" required placeholder="Type your SMS here..."></textarea>
            </div>
            <button type="submit">Send SMS</button>
        </form>

        <div class="status-box">
            <h3>API Key Status</h3>
            {% if key_status.error %}
                <div class="key-item error-text">{{ key_status.error }}</div>
            {% else %}
                {% for key, val in key_status.items() %}
                    <div class="key-item">{{ key }}: {{ val }}</div>
                {% endfor %}
            {% endif %}
            <p style="margin-top: 10px;"><a href="/status">View full status</a></p>
        </div>
    </div>
</body>
</html>
"""

STATUS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>NxSMS Key Status</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .key-item { margin: 10px 0; padding: 10px; background: white; border-radius: 4px; }
        .error { color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>API Key Status</h1>
        {% if key_status.error %}
            <div class="key-item error">{{ key_status.error }}</div>
        {% else %}
            {% for key, val in key_status.items() %}
                <div class="key-item">{{ key }}: {{ val }}</div>
            {% endfor %}
        {% endif %}
        <p style="margin-top: 20px;"><a href="/">Back to sender</a></p>
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE, key_status=get_key_status())


@app.route("/send", methods=["POST"])
def send_sms():
    phone = request.form.get("phone", "").strip()
    message = request.form.get("message", "").strip()

    if not phone or not message:
        flash("Phone number and message are required.", "error")
        return redirect(url_for("index"))

    try:
        sms = NxSMS()
        result = sms.send(phone, message)
        if result.success:
            flash("SMS sent successfully!", "success")
        else:
            flash(f"Send failed: {result.error}", "error")
    except Exception as e:
        flash(f"Service error: {str(e)}", "error")

    return redirect(url_for("index"))


@app.route("/status", methods=["GET"])
def status():
    return render_template_string(STATUS_TEMPLATE, key_status=get_key_status())


@app.route("/settings", methods=["GET"])
def settings():
    try:
        sms = NxSMS()
        email_config = sms.config.get("email2sms", {})
    except:
        email_config = {}
    return render_template_string(SETTINGS_TEMPLATE, config=email_config)


@app.route("/settings/save", methods=["POST"])
def save_settings():
    import json
    from pathlib import Path
    
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    smtp_host = request.form.get("smtp_host", "smtp.gmail.com").strip()
    smtp_port = request.form.get("smtp_port", "587").strip()
    carrier = request.form.get("carrier_gateway", "@vtext.com").strip()
    custom_gateway = request.form.get("custom_gateway", "").strip()
    service = request.form.get("service", "").strip()
    api_key = request.form.get("api_key", "").strip()
    
    config_dir = Path(__file__).parent / "configs" / "nx_sms"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "keys.json"
    
    config = {}
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
    
    if email and password:
        config["email2sms"] = {
            "email": email,
            "password": password,
            "smtp_host": smtp_host,
            "smtp_port": int(smtp_port),
            "carrier_gateway": custom_gateway if custom_gateway else carrier
        }
        flash("Email2SMS configured successfully!", "success")
    
    if service and api_key:
        config[service] = api_key
        flash(f"API key for {service} saved!", "success")
    
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    return redirect(url_for("settings"))


@app.route("/configure", methods=["GET"])
def configure():
    return redirect(url_for("settings"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


# Settings UI - Add routes below for API key management
SETTINGS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>NxSMS Settings</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; background: #1a1a2e; min-height: 100vh; }
        .container { background: #16213e; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
        h1 { color: #fff; margin-top: 0; border-bottom: 2px solid #0f3460; padding-bottom: 15px; }
        h2 { color: #e94560; margin-top: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #a0a0a0; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 12px; border: 1px solid #0f3460; border-radius: 6px; font-size: 14px; box-sizing: border-box; background: #0f3460; color: #fff; }
        input:focus, select:focus, textarea:focus { outline: none; border-color: #e94560; }
        textarea { height: 80px; }
        button { background: linear-gradient(135deg, #e94560, #c7314f); color: white; border: none; padding: 14px 28px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }
        button:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(233,69,96,0.4); }
        .service-card { background: #0f3460; padding: 20px; border-radius: 8px; margin-bottom: 15px; }
        .service-card h3 { color: #fff; margin: 0 0 10px 0; }
        .service-card .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .status.active { background: #28a745; color: white; }
        .status.inactive { background: #dc3545; color: white; }
        .nav { margin-bottom: 30px; }
        .nav a { color: #e94560; text-decoration: none; margin-right: 20px; font-weight: bold; }
        .nav a:hover { text-decoration: underline; }
        .flash { padding: 15px; margin-bottom: 20px; border-radius: 6px; }
        .flash.success { background: #28a745; color: white; }
        .flash.error { background: #dc3545; color: white; }
        .carrier-list { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .carrier-option { background: #0f3460; padding: 10px; border-radius: 6px; text-align: center; color: #fff; cursor: pointer; }
        .carrier-option:hover { background: #e94560; }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/">Send SMS</a>
            <a href="/settings">Settings</a>
            <a href="/configure">Configure Keys</a>
        </div>
        
        <h1>NxSMS Settings</h1>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" action="/settings/save">
            <h2>Email to SMS Configuration</h2>
            
            <div class="service-card">
                <h3>Email Account</h3>
                <div class="form-group">
                    <label>Your Email Address:</label>
                    <input type="email" name="email" value="{{ config.email or '' }}" placeholder="your@gmail.com">
                </div>
                <div class="form-group">
                    <label>Email Password / App Password:</label>
                    <input type="password" name="password" value="{{ config.password or '' }}" placeholder="16-character app password">
                </div>
                <div class="form-group">
                    <label>SMTP Server:</label>
                    <input type="text" name="smtp_host" value="{{ config.smtp_host or 'smtp.gmail.com' }}" placeholder="smtp.gmail.com">
                </div>
                <div class="form-group">
                    <label>SMTP Port:</label>
                    <input type="number" name="smtp_port" value="{{ config.smtp_port or '587' }}" placeholder="587">
                </div>
            </div>
            
            <h2>Carrier Gateway</h2>
            <div class="service-card">
                <div class="form-group">
                    <label>Select Carrier:</label>
                    <select name="carrier_gateway" id="carrierSelect">
                        <option value="@vtext.com" {{ config.carrier_gateway == '@vtext.com' or not config.carrier_gateway ? 'selected' : '' }}>Verizon</option>
                        <option value="@txt.att.net" {{ config.carrier_gateway == '@txt.att.net' ? 'selected' : '' }}>AT&T</option>
                        <option value="@tmomail.net" {{ config.carrier_gateway == '@tmomail.net' ? 'selected' : '' }}>T-Mobile</option>
                        <option value="@messaging.sprintpcs.com" {{ config.carrier_gateway == '@messaging.sprintpcs.com' ? 'selected' : '' }}>Sprint</option>
                        <option value="@email.uscc.net" {{ config.carrier_gateway == '@email.uscc.net' ? 'selected' : '' }}>US Cellular</option>
                        <option value="@mms.vectormobile.com" {{ config.carrier_gateway == '@mms.vectormobile.com' ? 'selected' : '' }}>Vector Mobile</option>
                        <option value="@cingularme.com" {{ config.carrier_gateway == '@cingularme.com' ? 'selected' : '' }}>Cingular</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Custom Gateway (optional):</label>
                    <input type="text" name="custom_gateway" value="{{ config.custom_gateway or '' }}" placeholder="@yourgateway.com">
                </div>
            </div>
            
            <h2>SMS API Services</h2>
            <div class="service-card">
                <h3>Add SMS Service API Key</h3>
                <div class="form-group">
                    <label>Service:</label>
                    <select name="service">
                        <option value="textbelt">TextBelt (free 1/day)</option>
                        <option value="smsto">SMS.to</option>
                        <option value="smsmode">SMSMode</option>
                        <option value="seasms">SeaSMS</option>
                        <option value="wifitext">WiFi Text</option>
                        <option value="textlocal">TextLocal</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>API Key:</label>
                    <input type="text" name="api_key" placeholder="Your API key">
                </div>
            </div>
            
            <button type="submit">Save Settings</button>
        </form>
        
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #0f3460;">
            <p style="color: #666;"><a href="/" style="color: #e94560;">Back to SMS Sender</a></p>
        </div>
    </div>
</body>
</html>
"""