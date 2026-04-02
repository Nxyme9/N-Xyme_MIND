"""Brain API endpoints for cognitive functions."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from brain.router import Router
from brain.evidence import EvidenceCortex
from brain.critic import Critic
from brain.dual_loop import DualLoop
from brain.memory.working import WorkingMemory
from brain.memory.semantic import SemanticMemory
from brain.memory.procedural import ProceduralMemory

router = APIRouter(prefix="/brain", tags=["brain"])

_router = Router()
_evidence = EvidenceCortex()
_critic = Critic()
_dual_loop = DualLoop()
_working_mem = WorkingMemory()
_semantic_mem = SemanticMemory(storage_path="data/semantic_memory.json")
_procedural_mem = ProceduralMemory(storage_path="data/procedural_memory.json")


class RouteRequest(BaseModel):
    intent_type: str
    complexity: str = "MED"
    risk: str = "LOW"
    has_fact_claims: bool = False


class ClaimRequest(BaseModel):
    text: str


class VerdictRequest(BaseModel):
    claims: List[Dict[str, Any]]


class LoopRequest(BaseModel):
    task_description: str
    intent_type: str = "UNKNOWN"
    risk: str = "LOW"


class MemoryStoreRequest(BaseModel):
    key: str
    value: str
    layer: str = "working"


class MemorySearchRequest(BaseModel):
    query: str
    layer: str = "semantic"


@router.post("/route")
async def route_task(req: RouteRequest):
    plan = _router.route(req.intent_type, req.complexity, req.risk, req.has_fact_claims)
    return {"target": plan.target, "use_evidence": plan.use_evidence, "use_critic": plan.use_critic, "loop_cap": plan.loop_cap, "reason": plan.reason}


@router.post("/evidence/classify")
async def classify_claim(req: ClaimRequest):
    claim = _evidence.classify(req.text)
    return {"claim_id": claim.claim_id, "claim_type": claim.claim_type, "confidence": claim.confidence}


@router.post("/critic/evaluate")
async def evaluate_verdict(req: VerdictRequest):
    verdict = _critic.evaluate(req.claims)
    return {"verdict": verdict.verdict, "reasons": verdict.reasons, "risk_level": verdict.risk_level, "unsupported_facts": verdict.unsupported_facts}


@router.post("/loop/select")
async def select_loop(req: LoopRequest):
    decision = _dual_loop.select_loop(req.task_description, req.intent_type, req.risk)
    return {"loop_type": decision.loop_type, "reason": decision.reason, "word_count": decision.word_count}


@router.post("/memory/store")
async def store_memory(req: MemoryStoreRequest):
    if req.layer == "working":
        item = _working_mem.store(req.key, req.value)
        return {"key": item.key, "value": item.value, "activation": item.activation}
    elif req.layer == "semantic":
        concept = _semantic_mem.store(req.key, req.key, req.value)
        return {"concept_id": concept.concept_id, "name": concept.name}
    elif req.layer == "procedural":
        rule = _procedural_mem.store(req.key, req.key, req.value, "auto")
        return {"rule_id": rule.rule_id, "name": rule.name}
    return {"error": "Unknown layer"}


@router.post("/memory/search")
async def search_memory(req: MemorySearchRequest):
    if req.layer == "semantic":
        results = _semantic_mem.search(req.query)
        return [{"concept_id": c.concept_id, "name": c.name, "description": c.description} for c in results[:5]]
    elif req.layer == "working":
        results = [i for i in _working_mem.get_all() if req.query.lower() in i.key.lower() or req.query.lower() in i.value.lower()]
        return [{"key": i.key, "value": i.value, "activation": i.activation} for i in results[:5]]
    return []


@router.get("/memory/stats")
async def memory_stats():
    return {
        "working": len(_working_mem.get_all()),
        "semantic": len(_semantic_mem.concepts),
        "procedural": len(_procedural_mem.rules),
    }
