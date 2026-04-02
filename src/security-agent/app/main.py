import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Optional
import structlog

# API Key Authentication
SECURITY_AGENT_API_KEY = os.getenv("SECURITY_AGENT_API_KEY", "")


def verify_api_key(authorization: str = Header(None)):
    """Verify API key from Authorization header."""
    if not SECURITY_AGENT_API_KEY:
        return True  # No key configured = dev mode

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization[7:]
    if token != SECURITY_AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


from app.service import (
    analyze_with_ollama,
    check_blacklist,
    check_sensitive,
    check_whitelist,
    get_cached,
    store_feedback,
    Decision,
)

structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
)

logger = structlog.get_logger()

app = FastAPI(title="N-XYME Security Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5002",
        "http://127.0.0.1",
        "http://127.0.0.1:5002",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    command: str
    context: Optional[dict] = None
    skip_cache: bool = False


class AnalyzeResponse(BaseModel):
    decision: Decision
    reason: str
    confidence: float
    cached: bool = False


class FeedbackRequest(BaseModel):
    command: str
    user_decision: Decision


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "security-agent",
        "version": "1.0.0",
        "timestamp": __import__("time").time(),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, auth: bool = Depends(verify_api_key)):
    command = request.command
    context = request.context or {}
    logger.info("analyze_request", command=command[:50], context=context)

    if not request.skip_cache:
        cached = get_cached(command)
        if cached:
            decision, reason, confidence = cached
            return AnalyzeResponse(
                decision=decision, reason=reason, confidence=confidence, cached=True
            )

    whitelisted, wl_reason = check_whitelist(command)
    if whitelisted:
        decision, reason, confidence = "allow", wl_reason, 0.95
    else:
        blacklisted, bl_reason = check_blacklist(command)
        if blacklisted:
            decision, reason, confidence = "deny", bl_reason, 0.95
        else:
            has_sensitive, patterns = check_sensitive(command)
            if has_sensitive:
                decision, reason, confidence = (
                    "prompt",
                    f"Contains sensitive patterns: {patterns}",
                    0.8,
                )
            else:
                decision, reason, confidence = analyze_with_ollama(command, context)

    entry = {
        "decision": decision,
        "reason": reason,
        "confidence": confidence,
        "hits": 0,
    }
    from app.service import CACHE

    CACHE[command[:200]] = entry

    return AnalyzeResponse(decision=decision, reason=reason, confidence=confidence, cached=False)


@app.post("/feedback")
async def feedback(request: FeedbackRequest, auth: bool = Depends(verify_api_key)):
    store_feedback(request.command, "prompt", request.user_decision)
    logger.info("user_feedback", command=request.command[:50], decision=request.user_decision)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5002)
