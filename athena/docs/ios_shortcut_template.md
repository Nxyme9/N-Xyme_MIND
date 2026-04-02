# iOS Edge Node — Shortcut Template

> **Purpose**: Turn your iPhone into a dumb sensor for the Bionic Unit.  
> **Requires**: Athena Daemon running (`athenad.py` on port 8000).

## Endpoint

```
POST http://<YOUR_IP>:8000/ingest
Content-Type: application/json
```

## Quick Capture (Text)

Create an iOS Shortcut with these steps:

1. **Ask for Input** → Text → "Quick thought?"
2. **Get Contents of URL**:
   - URL: `http://<YOUR_TAILSCALE_IP>:8000/ingest`
   - Method: POST
   - Headers: `Content-Type: application/json`
   - Request Body (JSON):

     ```json
     {
       "type": "text",
       "data": "[Provided Input]",
       "metadata": {"source": "ios_shortcut"}
     }
     ```

3. **Show Result**

## Camera Capture

1. **Take Photo**
2. **Base64 Encode** (use "Encode" action → Base64)
3. **Get Contents of URL**:
   - Body:

     ```json
     {
       "type": "camera",
       "data": "[Base64 Encoded]",
       "metadata": {"source": "iphone_camera"}
     }
     ```

## Location Capture

1. **Get Current Location**
2. **Get Contents of URL**:
   - Body:

     ```json
     {
       "type": "location",
       "data": "[Latitude],[Longitude]",
       "metadata": {
         "source": "iphone_gps",
         "altitude": "[Altitude]"
       }
     }
     ```

## Voice Memo Capture

1. **Record Audio** (set to m4a)
2. **Base64 Encode**
3. **Get Contents of URL**:
   - Body:

     ```json
     {
       "type": "voice",
       "data": "[Base64 Encoded]",
       "metadata": {"source": "iphone_mic"}
     }
     ```

## Testing via curl

```bash
# Text capture
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"type": "text", "data": "Test capture from terminal", "metadata": {"source": "curl"}}'

# Location
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"type": "location", "data": "1.3521,103.8198", "metadata": {"source": "manual", "city": "Singapore"}}'
```
