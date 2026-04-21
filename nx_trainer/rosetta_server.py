#!/usr/bin/env python3
"""
Rosetta Stone Trainer - FastAPI Inference Server

Provides a REST API for running inference with the trained Rosetta model.

Usage:
    # Start server
    python -m rosetta_server
    
    # Or with uvicorn directly
    uvicorn rosetta_server:app --host 0.0.0.0 --port 8080

Endpoints:
    POST /v1/chat/completions  - Chat completion (OpenAI-compatible)
    POST /inference            - Native inference endpoint
    GET  /tools                - List available tools
    GET  /health               - Health check
    GET  /models               - List loaded models
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rosetta_server")

# Global model instance
MODEL = None
TOKENIZER = None
BASE_MODEL_PATH = os.environ.get("ROSETTA_BASE_MODEL", "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/qwen2.5-0.5b-instruct")
ADAPTER_PATH = os.environ.get("ROSETTA_ADAPTER", "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/outputs/rosetta_0.5b/final")


def load_model():
    """Load the Rosetta model and tokenizer"""
    global MODEL, TOKENIZER
    
    if MODEL is not None:
        logger.info("Model already loaded")
        return
    
    logger.info(f"Loading base model from: {BASE_MODEL_PATH}")
    
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import PeftModel
        
        # Load tokenizer
        TOKENIZER = AutoTokenizer.from_pretrained(BASE_MODEL_PATH, trust_remote_code=True)
        
        # Load base model
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_PATH,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else "cpu",
            trust_remote_code=True,
        )
        
        # Load LoRA adapter if exists
        if os.path.exists(ADAPTER_PATH):
            adapter_file = os.path.join(ADAPTER_PATH, "adapter_model.safetensors")
            if os.path.exists(adapter_file):
                logger.info(f"Loading adapter from: {ADAPTER_PATH}")
                MODEL = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
            else:
                logger.warning("Adapter directory exists but no adapter_model.safetensors found, using base model")
                MODEL = base_model
        else:
            logger.warning("No adapter path found, using base model")
            MODEL = base_model
            
        MODEL.eval()
        logger.info("Model loaded successfully!")
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for loading/unloading model"""
    # Startup
    logger.info("Starting Rosetta Inference Server...")
    load_model()
    yield
    # Shutdown
    logger.info("Shutting down Rosetta Inference Server...")


# Create FastAPI app
app = FastAPI(
    title="Rosetta Stone Inference API",
    description="Fast inference API for Rosetta Stone tool-calling model",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Pydantic Models
# ============================================================================


class Message(BaseModel):
    """Chat message"""
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""
    model: str = "rosetta"
    messages: List[Message]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    stream: bool = False
    stop: Optional[List[str]] = None


class InferenceRequest(BaseModel):
    """Native inference request"""
    prompt: str
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    stream: bool = False


class ToolCall(BaseModel):
    """Tool call response"""
    tool: str
    args: Dict[str, Any]
    confidence: Optional[float] = None


class InferenceResponse(BaseModel):
    """Inference response"""
    tool_call: ToolCall
    raw_output: str
    tokens_used: int


# ============================================================================
# Routes
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    gpu_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else None
    
    return {
        "status": "healthy",
        "model_loaded": MODEL is not None,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "base_model": BASE_MODEL_PATH,
        "adapter_path": ADAPTER_PATH,
    }


@app.get("/models")
async def list_models():
    """List available models"""
    return {
        "models": [
            {
                "id": "rosetta",
                "object": "model",
                "owned_by": "n-xyme",
                "base_model": BASE_MODEL_PATH,
                "adapter_path": ADAPTER_PATH,
            }
        ]
    }


@app.get("/tools")
async def list_tools():
    """List available tools (MCP tools)"""
    # Load from the training data if available
    tools_file = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/data/v4_real.jsonl"
    tools = []
    
    if os.path.exists(tools_file):
        try:
            with open(tools_file) as f:
                for line in f:
                    d = json.loads(line)
                    if "messages" in d:
                        msgs = d.get("messages", [])
                        if len(msgs) >= 2:
                            try:
                                resp = json.loads(msgs[1].get("content", "{}"))
                                tool_name = resp.get("tool", "")
                                tool_args = resp.get("args", {})
                                if tool_name and tool_name not in [t["name"] for t in tools]:
                                    tools.append({
                                        "name": tool_name,
                                        "description": f"Tool: {tool_name}",
                                        "parameters": tool_args,
                                    })
                            except:
                                pass
        except Exception as e:
            logger.warning(f"Could not load tools from {tools_file}: {e}")
    
    # Fallback to common tools
    if not tools:
        tools = [
            {"name": "read", "description": "Read a file", "parameters": {"filePath": "/path/to/file"}},
            {"name": "write", "description": "Write to a file", "parameters": {"filePath": "/path", "content": "text"}},
            {"name": "grep", "description": "Search in files", "parameters": {"pattern": "regex", "path": "."}},
            {"name": "glob", "description": "Find files by pattern", "parameters": {"pattern": "*.py"}},
            {"name": "memory_search", "description": "Search memory", "parameters": {"query": "search terms"}},
            {"name": "memory_write", "description": "Write to memory", "parameters": {"content": "text"}},
            {"name": "github_search_repos", "description": "Search GitHub repos", "parameters": {"query": "search"}},
            {"name": "github_list_issues", "description": "List GitHub issues", "parameters": {"owner": "user", "repo": "name"}},
            {"name": "browser_navigate", "description": "Navigate browser", "parameters": {"url": "https://..."}},
            {"name": "sqlite_query", "description": "Query SQLite", "parameters": {"sql": "SELECT *"}},
        ]
    
    return {"tools": tools}


@app.post("/inference", response_model=InferenceResponse)
async def inference(request: InferenceRequest):
    """Native inference endpoint"""
    if MODEL is None or TOKENIZER is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Use simple format that works
        text = f"The user said: \"{request.prompt}\"\n\nGenerate the tool call in JSON format:"
        
        # Tokenize
        inputs = TOKENIZER(text, return_tensors="pt")
        input_ids = inputs["input_ids"]
        if torch.cuda.is_available():
            input_ids = input_ids.cuda()
        
        # Generate
        with torch.no_grad():
            outputs = MODEL.generate(
                input_ids=input_ids,
                attention_mask=inputs["attention_mask"].cuda() if torch.cuda.is_available() and "attention_mask" in inputs else None,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=request.temperature > 0,
            )
        
        # Decode
        response = TOKENIZER.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)
        
        # Try to parse tool call
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                tool_json = json.loads(response[start:end])
                tool_call = ToolCall(
                    tool=tool_json.get("tool", "unknown"),
                    args=tool_json.get("args", {}),
                )
            else:
                tool_call = ToolCall(tool="text", args={"content": response})
        except:
            tool_call = ToolCall(tool="text", args={"content": response})
        
        return InferenceResponse(
            tool_call=tool_call,
            raw_output=response,
            tokens_used=outputs.shape[1] - inputs.input_ids.shape[1],
        )
        
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute")
async def execute(request: InferenceRequest):
    """
    Execute tool call endpoint - inference + execution in one call
    
    Takes a natural language prompt, runs inference to get tool call,
    then executes the tool and returns the result.
    """
    if MODEL is None or TOKENIZER is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        text = request.prompt + "\n\nGenerate the tool call in JSON format:"
        
        inputs = TOKENIZER(text, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = MODEL.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=request.temperature > 0,
            )
        
        response = TOKENIZER.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        
        tool_json = None
        tool_name = "text"
        tool_args = {}
        
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                tool_json = json.loads(response[start:end])
                tool_name = tool_json.get("tool", "text")
                tool_args = tool_json.get("args", {})
        except:
            pass
        
        return {
            "success": True,
            "prompt": request.prompt,
            "tool_call": {
                "tool": tool_name,
                "args": tool_args,
            },
            "raw_output": response,
            "note": "Execution not implemented in server - use rosetta_client.execute() or rosetta_executor",
            "tokens_used": outputs.shape[1] - inputs.input_ids.shape[1],
        }
        
    except Exception as e:
        logger.error(f"Execute error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint"""
    if MODEL is None or TOKENIZER is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Convert messages to prompt
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        if request.stream:
            # Streaming response
            return StreamingResponse(
                stream_chat(messages, request, MODEL, TOKENIZER),
                media_type="text/event-stream",
            )
        
        # Non-streaming response
        text = TOKENIZER.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = TOKENIZER(text, return_tensors="pt")
        
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = MODEL.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=request.temperature > 0,
                stop_strings=request.stop,
            )
        
        response = TOKENIZER.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        
        # Build OpenAI-compatible response
        return JSONResponse({
            "id": f"chatcmpl-{os.urandom(12).hex()}",
            "object": "chat.completion",
            "created": int(os.time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": inputs.input_ids.shape[1],
                "completion_tokens": outputs.shape[1] - inputs.input_ids.shape[1],
                "total_tokens": outputs.shape[1],
            },
        })
        
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat(messages: List[Dict], request: ChatCompletionRequest, model, tokenizer):
    """Stream chat responses"""
    import asyncio
    
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt")
    
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    
    buffer = ""
    chunk_id = f"chatcmpl-{os.urandom(12).hex()}"
    
    # Generate token by token
    max_new_tokens = request.max_tokens
    generated_ids = inputs.input_ids
    
    for _ in range(max_new_tokens):
        with torch.no_grad():
            outputs = model.generate(
                **generated_ids,
                max_new_tokens=1,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=request.temperature > 0,
                return_dict_in_generate=True,
            )
        
        new_token = outputs.sequences[0, -1]
        generated_ids = outputs.sequences
        
        # Decode single token
        token_text = tokenizer.decode(new_token, skip_special_tokens=True)
        buffer += token_text
        
        # Yield chunk
        chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(os.time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": token_text},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        
        # Check for stop
        if request.stop:
            for s in request.stop:
                if s in buffer:
                    break
    
    # Final chunk
    yield f"data: [DONE]\n\n"


# ============================================================================
# CLI
# ============================================================================


def main():
    """Main entry point"""
    import uvicorn
    
    port = int(os.environ.get("ROSETTA_PORT", "8000"))
    host = os.environ.get("ROSETTA_HOST", "0.0.0.0")
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     Rosetta Stone Inference Server v1.0                   ║
╠══════════════════════════════════════════════════════════════╣
║  Base Model: {BASE_MODEL_PATH[:40]:<40}║
║  Adapter:   {ADAPTER_PATH[:40]:<40}║
║  Server:    http://{host}:{port}                           ║
╠══════════════════════════════════════════════════════════════╣
║  Endpoints:                                              ║
║    GET  /health    - Health check                        ║
║    GET  /models    - List models                         ║
║    GET  /tools     - List tools                         ║
║    POST /inference - Native inference                   ║
║    POST /v1/chat/completions - OpenAI compatible         ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()