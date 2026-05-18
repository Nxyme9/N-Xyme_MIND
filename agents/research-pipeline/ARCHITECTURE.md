# Research Pipeline Architecture — OMO Native Integration

**Designers:** Metis (analysis) + Prometheus (planning) — fused
**Date:** 2026-05-18
**Status:** Design Complete

---

## Executive Summary

Integrar best practices y bleeding-edge research como **parte nativa del workflow OMO**, no como tarea ad-hoc. Esto requiere 3 mecanismos (Research Gate, Research Feed, Research Memory Layer) que modifican 4 agentes existentes, crean 1 nuevo skill y 1 nuevo agente, y añaden ~6 días-hombre al Master Plan.

---

## Arquitectura Overview

```
                    ┌────────────────────────────────────────────┐
                    │           RESEARCH PIPELINE                │
                    │                                            │
                    │  ┌─────────────────────────────────────┐   │
                    │  │    A. Research Gate (síncrono)       │   │
                    │  │    Catalyst → Metis → Librarian →    │   │
                    │  │    memoria → Hephaestus              │   │
                    │  └─────────────────────────────────────┘   │
                    │                                            │
                    │  ┌─────────────────────────────────────┐   │
                    │  │    B. Research Feed (asíncrono)      │   │
                    │  │    Cron/trigger → Librarian →        │   │
                    │  │    extraer → memoria(best_practice)  │   │
                    │  └─────────────────────────────────────┘   │
                    │                                            │
                    │  ┌─────────────────────────────────────┐   │
                    │  │    C. Research Memory Layer           │   │
                    │  │    Memoria con metadatos: fuente,     │   │
                    │  │    fecha, tags, confianza             │   │
                    │  └─────────────────────────────────────┘   │
                    └────────────────────────────────────────────┘
```

---

## A. Research Gate — Pre-build Validation

### ¿Qué es?

Un **checkpoint obligatorio** que Catalyst ejecuta ANTES de rutear cualquier tarea COMPLEX o MEDIUM con confianza < 90%. Responde:
1. ¿Existe una librería/best practice moderna que haga esto mejor?
2. ¿Hay cambios recientes en el ecosistema que afecten el approach?
3. ¿Qué recomiendan fuentes autoritativas hoy (2025-2026)?

### Flujo detallado

```
Catalyst PHASE 0 (Adaptive Router modificado):
  │
  ├── Complex task detected (eff_complexity ≥ MEDIUM)
  │   └── eff_confidence < 90%?
  │       ├── NO  → ΣKIP Research Gate (too confident, skip)
  │       └── YES → ENTER RESEARCH GATE
  │                 │
  │                 ├── 1. Metis analiza: ¿qué tecnologías/patrones
  │                 │     son relevantes para este task?
  │                 │     → Output: research_queries[] (1-3 queries)
  │                 │
  │                 ├── 2. Catalyst: call_omo_agent("Librarian", research_queries)
  │                 │     → Librarian busca en paralelo:
  │                 │       a) Best practices actuales para {technology}
  │                 │       b) Cambios recientes en ecosistema {changelog}
  │                 │       c) Implementaciones de referencia
  │                 │     → Output: estructurado con sources, confidence, freshness
  │                 │
  │                 ├── 3. Librarian almacena en memoria como "research_gate:{task_hash}"
  │                 │     → Metadatos: source, date, tags, confidence, task_hash
  │                 │
  │                 ├── 4. Catalyst inyecta research findings en el task de Hephaestus:
  │                 │     "TASK: ...
  │                 │      RESEARCH_CONTEXT:
  │                 │        - Best practice: {pattern} ({source})
  │                 │        - Warning: {ecosystem change} ({source})
  │                 │        - Recommendation: {approach}"
  │                 │
  │                 └── 5. Hephaestus PHASE 0: load research context → build
```

### Condiciones de activación

| Tipo de tarea | Confidence | Research Gate |
|--------------|-----------|---------------|
| SIMPLE       | cualquier | SKIP (no necesario) |
| MEDIUM       | ≥ 90%     | SKIP |
| MEDIUM       | < 90%     | **LIGHT GATE** — 1 query rápida |
| COMPLEX      | ≥ 90%     | **LIGHT GATE** — best practice check |
| COMPLEX      | < 90%     | **FULL GATE** — 3 queries paralelas |
| UNKNOWN      | cualquier | SKIP (primero explorar, luego decidir) |

### Latencia esperada

- **LIGHT GATE:** ~10-20s (1 websearch + 1 webfetch)
- **FULL GATE:** ~30-60s (3 queries paralelas en Librarian)

---

## B. Research Feed — Conocimiento Continuo

### ¿Qué es?

Un **skill autónomo** que Librarian ejecuta periódicamente para mantener el sistema actualizado automáticamente. No requiere invocación explícita.

### Mecanismo

```
1. TRIGGER: Semanal (o bajo demanda vía Catalyst "research:feed:run")
   ├── Configurable en data/research-feed/sources.json
   │
2. Librarian carga skill("nx-research-feed")
   │
3. Para cada fuente en sources.json:
   ├── Changelogs:
   │   ├── Mojo → modular.com/changelog
   │   ├── OpenCode → github.com/nicepkg/opencode/releases
   │   ├── MCP → modelcontextprotocol.io/changelog
   │   ├── Rust → blog.rust-lang.org/releases
   │   └── Python → docs.python.org/3/whatsnew
   │
   ├── Best practices feeds:
   │   ├── OWASP Top 10 (seguridad)
   │   ├── Rust API Guidelines
   │   ├── Google AI Principles
   │   └── MDN Web Docs (web platform updates)
   │
   └── Community signals:
       ├── HackerNews frontpage (tech)
       ├── Lobsters (Rust/compilers)
       └── r/rust, r/programminglanguages

4. Por cada entrada:
   ├── Extraer: title, summary, relevance_tags[], action_items[]
   ├── Clasificar:  // qué agente debería saber esto
   │   ├── tag:"hephaestus" → patrones de código
   │   ├── tag:"catalyst" → cambios en ecosistema que afectan routing
   │   ├── tag:"all" → cambios importantes que todos deben saber
   │   └── tag:"momis" → nuevas vulnerabilidades/anti-patrones
   │
   ├── Almacenar en memoria:
   │   write_memory("research_feed:{date}:{hash}", {
   │     title: "...",
   │     summary: "...",
   │     source: URL,
   │     date: ISO,
   │     tags: ["mojo", "compiler", "best_practice"],
   │     freshness: "hot" | "warm" | "stale",
   │     confidence: "verified" | "pending" | "speculative",
   │     affected_agents: ["hephaestus", "catalyst"],
   │     action_items: ["Update pattern X", "Avoid pattern Y"]
   │   })
   │
   └── Si freshness == "stale" → marcar para revisión

5. Post-feed:
   ├── Resumir en write_memory("research_feed:latest_summary", {...})
   └── Notificar a Catalyst: "New research feed available"
```

### Sources Config

Archivo: `config/research-feed-sources.json`

```json
{
  "version": 1,
  "feeds": {
    "changelogs": {
      "mojo": "https://docs.modular.com/mojo/changelog",
      "opencode": "https://github.com/nicepkg/opencode/releases",
      "mcp": "https://modelcontextprotocol.io/changelog",
      "rust": "https://blog.rust-lang.org/releases/",
      "python": "https://docs.python.org/3/whatsnew/"
    },
    "best_practices": {
      "owasp": "https://owasp.org/www-project-top-ten/",
      "rust_api": "https://rust-lang.github.io/api-guidelines/",
      "google_ai": "https://ai.google/responsibility/principles/"
    }
  },
  "schedule": {
    "interval_hours": 168,
    "max_items_per_feed": 10,
    "freshness_days": {
      "hot": 7,
      "warm": 30,
      "stale": 90
    }
  }
}
```

### Skill: `nx-research-feed`

Nuevo skill en `agents/librarian/skills/nx-research-feed/SKILL.md`. Contiene:
- Protocolo de ejecución feed (fuentes, extracción, clasificación)
- Formato de almacenamiento en memoria
- Política de freshness
- Integración con anti-hallucination rules

---

## C. Research Memory Layer

### Esquema de Memoria

Cada research finding se almacena con metadatos completos:

```
Memoria key: research:{type}:{date}:{hash_id}

{
  "meta": {
    "type": "research_gate" | "research_feed" | "manual",
    "date_ingested": "2026-05-18T10:00:00Z",
    "date_source": "2026-05-17T00:00:00Z",  // fecha original de la fuente
    "freshness": "hot" | "warm" | "stale",
    "confidence": "verified" | "pending" | "speculative",
    "version": 1
  },
  "source": {
    "url": "https://...",
    "title": "...",
    "type": "changelog" | "paper" | "blog" | "docs" | "github",
    "author": "..."
  },
  "content": {
    "summary": "...",
    "key_findings": ["...", "..."],
    "action_items": ["...", "..."],
    "affected_patterns": ["pattern:mojo/async", "pattern:rust/error_handling"],
    "code_examples": []  // opcional, URLs o snippets
  },
  "tags": [
    "mojo", "compiler", "best_practice",
    "hephaestus",  // qué agente debe saber esto
    "org:n-xyme",  // dominio
    "tech:mojo"    // tecnología
  ],
  "routing_impact": {
    "affected_agents": ["hephaestus"],
    "recommendation": "Use mojo async pattern instead of threading",
    "severity": "info" | "warning" | "critical"
  }
}
```

### Índices de Búsqueda

Para queries eficientes desde los agentes:

| Query | Uso | Agente |
|-------|-----|--------|
| `search_memory("research:*:best_practice:mojo")` | Hephaestus busca best practices de Mojo | Hephaestus |
| `search_memory("research:research_gate:*")` | Catalyst busca gates recientes por task | Catalyst |
| `search_memory("research:*:*:hephaestus")` | Todo lo relevante para Hephaestus | Catalyst antes de rutear |
| `search_memory("research:*:*:freshness:hot")` | Solo findings recientes | Todos en PHASE 0 |
| `search_memory("research:*:*:severity:critical")` | Alertas importantes | Catalyst en PHASE 0 |

### Cache / Frescura

- Findings con `freshness: hot` (< 7 días) → se checkean siempre
- Findings con `freshness: warm` (7-30 días) → se checkean si hay match de tag
- Findings con `freshness: stale` (> 30 días) → se ignoran, Librarian los re-checkea en próximo feed si son tags activas
- Findings con `freshness: stale` > 90 días → se archivan (no se borran, solo se marcan)

---

## D. Modificaciones a .agent.md

### 1. catalyst.agent.md

**Cambios necesarios:**

En `PHASE 0: ADAPTIVE ROUTER`, añadir subfase `0b: RESEARCH GATE CHECK`:

```
PHASE 0: ADAPTIVE ROUTER (modificado)
│
├── 0a: Load adaptive-router → score confidence → estimate complexity
├── 0b: RESEARCH GATE CHECK (NUEVO)
│     ├── IF task is COMPLEX OR (MEDIUM AND confidence < 90%):
│     │     ├── Load skill("nx-research-gate")
│     │     ├── Query: "search_memory research:*:*:freshness:hot"
│     │     │         + "search_memory research:*:{tag_match}"
│     │     ├── IF relevant findings exist AND fresh:
│     │     │     └── Inject into task context → SKIP Librarian call
│     │     ├── IF no relevant findings OR stale:
│     │     │     └── Route to Librarian for gate research
│     │     │         → Parallel: delegate_task("Metis", "analyze queries")
│     │     │         → call_omo_agent("Librarian", "research queries")
│     │     │         → Collect, store, inject
│     │     │
│     │     └── Confidence update: recalculate after research
│     │
│     └── ELSE: SKIP Gate (SIMPLE or high confidence)
│
├── 0c: Apply catalyst modifier (existing)
├── 0d: Select pipeline (existing)
└── 0e: Track and adapt (existing)
```

**Nuevas skills en catalyst.agent.md:**
- `nx-research-gate` — protocolo RESEARCH GATE (load on demand en Phase 0b)

**Nuevos tools:**
- `search_memory` con filtros por tags — ya existe, solo se añade query pattern

**Sección QUALITY GATE:**
Añadir check:
```
- [ ] Research Gate evaluated (skipped or executed)
- [ ] If Gate ran: findings injected into task context
- [ ] If findings found: confidence updated
```

### 2. librarian.agent.md

**Cambios necesarios:**

Nuevo protocolo `PHASE 0: CHECK RESEARCH FEED CONFIG`:

```
PHASE 0: LOAD CONTEXT
├── Load skill("nx-research-feed") for feed execution
├── OR load skill("nx-librarian-deepdive") for on-demand research
├── Load config/research-feed-sources.json

PHASE 1: DETERMINE MODE (NUEVO)
├── "research_gate" mode:
│   ├── Input: research_queries[] from Catalyst
│   ├── Execute: parallel webfetch/websearch per query
│   ├── Format: structured with confidence, sources, freshness
│   └── Store: write_memory("research_gate:{task_hash}", result)
│
├── "research_feed" mode:
│   ├── Execute: nx-research-feed skill
│   ├── Iterate sources.json, extract, classify, store
│   └── Store: write_memory("research_feed:{date}:{hash}", result)
│
└── "standard" mode (existing):
    └── Current behavior (single research query)
```

**Nuevas skills:**
- `nx-research-feed` — protocolo de ejecución feed semanal
- `nx-research-gate` — protocolo de research gate (compartido con Catalyst)

**Nuevos tools:**
- `write_memory` con formato estructurado (ya existe, solo se estandariza)

### 3. hephaestus.agent.md

**Cambios necesarios:**

Nuevo `PHASE 0: RESEARCH CONTEXT LOAD`:

```
PHASE 0: RESEARCH CONTEXT LOAD (NUEVO)
├── search_memory("research:*:{tag:match})  
│   └── Buscar: best practices para tech stack actual
│
├── search_memory("research:*:*:severity:warning")
│   └── Buscar: warnings activos que afectan este build
│
├── IF research findings found:
│   └── Load into context: "RESEARCH CONTEXT AVAILABLE:
│        - {finding 1} ({source}, {confidence})
│        - {finding 2} ..."
│
└── IF no findings: continue normally

PHASE 1: HOTLOAD (existing, después de research)
PHASE 2: BUILD (existing)
...
```

**Nuevos tools:**
- `search_memory` con filtros de tags — mismo tool, nuevo patrón de uso

**Quality Gate check nuevo:**
```
- [ ] Research context checked (best practices for tech stack)
- [ ] No warnings/anti-patterns affecting this build
```

### 4. metis.agent.md

**Cambios necesarios:**

Nuevo `PHASE 1b: RESEARCH QUERY GENERATION`:

```
PHASE 1b: RESEARCH QUERY GENERATION (NUEVO)
├── Analyst technology/pattern stack needed for the task
├── Generate 1-3 research_queries[]:
│   └── {technology} + {pattern} + {best practice 2026}
│
├── Output structured for Librarian:
│   [
│     { query: "mojo async best practices 2026", priority: "high" },
│     { query: "mcp server security patterns 2026", priority: "medium" },
│     { query: "...", priority: "low" }
│   ]
│
└── Return to Catalyst → Catalyst forwards to Librarian
```

---

## E. Nuevo Skills

### Skill 1: `nx-research-gate`

**Path:** `agents/skills/research-gate/SKILL.md`

**Propósito:** Protocolo que Catalyst y Librarian cargan para ejecutar el Research Gate.

**Contenido:**
```
# nx-research-gate — SKILL

## Purpose
Pre-build validation gate: checks if a modern library/best practice exists before Hephaestus builds.

## Phases

### PHASE 1: QUERY GENERATION (Catalyst/Metis)
- Input: task description
- Output: research_queries[] (1-3 queries)
- Query template: "{technology} {pattern} best practice {year}"

### PHASE 2: MEMORY CHECK (Catalyst)
- search_memory("research:*:*:tag:{technology}")
- IF fresh findings exist → SKIP Librarian, inject context
- IF stale or missing → PROCEED to Librarian

### PHASE 3: EXECUTE (Librarian)
- Parallel webfetch/websearch per query
- Format: structured JSON with sources, confidence, freshness
- Store: write_memory("research_gate:{task_hash}", result)

### PHASE 4: INJECT (Catalyst)
- Wrap findings into task context
- Prepend to task description before delegating to Hephaestus
```

### Skill 2: `nx-research-feed`

**Path:** `agents/librarian/skills/nx-research-feed/SKILL.md`

**Propósito:** Ejecución autónoma del feed de conocimiento continuo.

**Contenido:**
```
# nx-research-feed — SKILL

## Purpose
Weekly autonomous research feed that keeps the system updated on best practices and ecosystem changes.

## Phases

### PHASE 1: LOAD SOURCES
- Read config/research-feed-sources.json
- Validate source URLs are accessible
- Filter: skip sources checked < 7 days ago

### PHASE 2: FETCH IN PARALLEL
- For each source category (changelog, best_practice, community):
  - webfetch(url) with 10s timeout
  - If timeout → mark as "unavailable", skip this cycle

### PHASE 3: EXTRACT & CLASSIFY
- Parse each response for:
  - New versions, deprecations, breaking changes
  - New patterns, best practices
  - Security advisories
- Assign: title, summary, tags[], action_items[]
- Classify by affected_agent: ["hephaestus", "catalyst", "momis", "all"]

### PHASE 4: STORE
- For each finding:
  write_memory("research_feed:{date}:{hash}", {
    meta: { type, date_ingested, date_source, freshness, confidence },
    source: { url, title, type },
    content: { summary, key_findings, action_items, affected_patterns },
    tags: [...],
    routing_impact: { affected_agents, recommendation, severity }
  })

### PHASE 5: NOTIFY
- Write summary: write_memory("research_feed:latest_summary", { count, top_findings })
- All agents check this in PHASE 0

## Sources Config
See config/research-feed-sources.json
```

---

## F. Nuevo Agente: "Oracle — Research Router"

### ¿Es necesario?

**NO como agente independiente.** Tras analizar, el Oracle que menciona el adaptive-router es una función que puede ser absorbida por **Metis + Librarian fusionados temporalmente**. Crear un agente Oracle separado añadiría complejidad de orquestación sin beneficio claro.

**Alternativa:** Load `nx-oracle-consult` skill ya existe (`agents/oracle/skills/nx-oracle-consult/SKILL.md`). Este skill puede ser cargado por Metis cuando se necesita análisis arquitectónico + research. No requiere nuevo agente.

### Decisión de diseño

| Opción | Pros | Contras | Veredicto |
|--------|------|---------|-----------|
| Nuevo agente Oracle | Separación clara de concerns | +1 agente en routing, más hops, más latencia | ❌ |
| Metis + Librarian fusionados | Sin nuevo agente, Metis ya analiza | Metis no tiene network access | ⚠️ |
| Skill existente nx-oracle-consult + Metis | Reutiliza skill existente, Metis analiza, Librarian investiga | Metis necesita poder cargar nx-oracle-consult | ✅ |

**Decisión final:** Metis carga `nx-oracle-consult` para generar queries de research. Librarian ejecuta las queries. No se crea nuevo agente.

---

## G. Flujo Completo Catalyst → Research Gate → Hephaestus

```
USER: "Implement a new MCP server for file operations"

Catalyst PHASE 0a: Adaptive Router
├── Complexity: COMPLEX (new service, multi-file)
├── Confidence: 75% (task clear but ecosystem uncertain)
└── Result: COMPLEX + < 90% → RESEARCH GATE ACTIVATED

Catalyst PHASE 0b: RESEARCH GATE
├── 1. search_memory("research:*:*:tag:mcp")
│     └── Result: findings from 2 weeks ago → warm → valid
│         ├── "MCP server best practices" (freshness: warm)
│         └── "MCP security patterns" (freshness: warm)
│
├── 2. Metis: load skill("nx-oracle-consult")
│     └── Generate queries:
│         ├── "mcp server file operations best practices 2026" (high)
│         └── "mcp protocol changes 2026" (high)
│
├── 3. Librarian (parallel):
│     ├── webfetch: mcp docs → "Use transport-agnostic design"
│     ├── websearch: "mcp best practices 2026" → "Resource templates recommended"
│     └── websearch: "mcp protocol changes" → "v2025-03: roots added"
│
├── 4. Store: write_memory("research_gate:{task_hash}", {
│       findings: [
│         "Use transport-agnostic design (source: mcp docs, verified)",
│         "Resource templates recommended over manual routing (source: community blog, pending)",
│         "MCP v2025-03 added roots feature (source: spec, verified)"
│       ]
│     })
│
└── 5. Inject into task:
      "TASK: Implement MCP server for file operations
       RESEARCH CONTEXT:
       - [verified] Use transport-agnostic design (mcp docs)
       - [pending] Resource templates recommended over manual routing
       - [verified] MCP v2025-03 added roots feature (spec)"

Catalyst PHASE 0c: Recalculate confidence
├── Before: 75%
├── After research: 88% (+13% from resolved uncertainties)
└── Route: HEPHAESTUS with light verify (now 70-89%)

Hephaestus PHASE 0: Research context load
├── search_memory("research:*:*:tag:file_operations")
├── Load research context → "RESEARCH CONTEXT AVAILABLE"
└── Proceed with PHASE 1 (hotload) with research-informed approach

Hephaestus PHASE 1-5: Build with best practices
├── Uses transport-agnostic design (from research)
├── Implements resource templates (flagged as pending → warns in code review)
└── Momus review checks: "Did you follow the research recommendations?"
```

---

## H. Resumen de Archivos a Crear/Modificar

### Archivos NUEVOS

| Archivo | Tipo | Esfuerzo |
|---------|------|----------|
| `agents/skills/research-gate/SKILL.md` | Skill - Research Gate protocol | 2h |
| `agents/librarian/skills/nx-research-feed/SKILL.md` | Skill - Research Feed protocol | 2h |
| `config/research-feed-sources.json` | Config - Feed sources | 30min |
| `agents/research-pipeline/ARCHITECTURE.md` | Docs - This document | N/A (ya hecho) |

### Archivos a MODIFICAR

| Archivo | Cambio | Esfuerzo |
|---------|--------|----------|
| `agents/omo/catalyst.agent.md` | Añadir PHASE 0b RESEARCH GATE CHECK + skill nx-research-gate + quality gate checks | 1h |
| `agents/omo/librarian.agent.md` | Añadir PHASE 1 DETERMINE MODE + skills nx-research-feed + nx-research-gate + store format | 1.5h |
| `agents/omo/hephaestus.agent.md` | Añadir PHASE 0 RESEARCH CONTEXT LOAD + search_memory en skills + quality gate | 1h |
| `agents/omo/metis.agent.md` | Añadir PHASE 1b RESEARCH QUERY GENERATION + skill nx-oracle-consult | 1h |
| `agents/skills/adaptive-router/SKILL.md` | Añadir Section 13: Research Gate integration (cómo el adaptive-router chequea research antes de rutear) | 1h |

### Total Esfuerzo

| Componente | Tiempo |
|-----------|--------|
| Skills nuevos (research-gate + research-feed) | 4h |
| Modificaciones agentes (catalyst, librarian, hephaestus, metis) | 4.5h |
| Config (research-feed-sources.json) | 0.5h |
| Adaptive router update (Section 13) | 1h |
| **Total** | **~10h (1.25 días)** |

### Esfuerzo adicional opcional

| Feature | Tiempo | ROI |
|---------|--------|-----|
| Dashboard para monitorear research freshness | 4h | Medium |
| Alertas cuando una best practice se vuelve stale | 2h | High |
| Testing automatizado del Research Gate (que no añada latencia indebida) | 3h | High |
| **Total opcional** | **9h** | |

---

## I. Estimación en el Master Plan

### Añadir al Plan existente

```
WAVE: 5 — Research Pipeline Integration (PARALLEL con Wave 4)
├── [P] STORY: Research Gate protocol
│     └── Tasks:
│           [ ] Crear skill nx-research-gate (2h)
│           [ ] Modificar catalyst.agent.md — PHASE 0b (1h)
│           [ ] Modificar hephaestus.agent.md — PHASE 0 research load (1h)
│           [ ] Modificar metis.agent.md — PHASE 1b query generation (1h)
│           [ ] Modificar adaptive-router — Section 13 (1h)
│
├── [P] STORY: Research Feed continuous knowledge
│     └── Tasks:
│           [ ] Crear skill nx-research-feed (2h)
│           [ ] Modificar librarian.agent.md — PHASE 1 modes (1.5h)
│           [ ] Crear config/research-feed-sources.json (0.5h)
│
└── [S] STORY: Research Memory Layer
      └── Tasks:
            [ ] Estandarizar formato de memoria research (incluido en skills)
            [ ] Tests de latencia: Research Gate no debe añadir >60s a tasks SIMPLE
```

### Posición en WAVES

```
WAVE 1: Foundation (existing)
WAVE 2: Agent definitions (existing)
WAVE 3: Memory & consciousness (existing)
WAVE 4: Core workflows (existing — bmad-catalyst-orchestration, etc.)
═══════════════════════════════════════════════════════════════
WAVE 5: Research Pipeline ← THIS (1.25 días efectivos)

Puede correr PARALELO con Wave 4 porque:
- No toca los mismos archivos que Wave 4 (Wave 4 son workflows BMad)
- Las modificaciones son en agent files y skills, no en core workflows
- Riesgo bajo de conflictos de merge
```

---

## J. Anti-patterns a evitar

| Anti-pattern | Riesgo | Mitigación |
|-------------|--------|------------|
| Research Gate añade latencia a todo | Tasks simples se ralentizan | Gate solo se activa para COMPLEX y MEDIUM < 90% confianza |
| Research Feed satura la memoria con datos stale | Memoria vectorial se llena | Freshness policy: stale > 90d se archiva, no se borra |
| Hephaestus ignora research findings | Research inútil | Findings se inyectan en task description como contexto; Momus verifica adherencia |
| Metis genera queries irrelevantes | Gate ejecuta research innecesario | Límite de 3 queries por gate; si 0 findings relevantes → no se inyectan |
| Duplicación de research (mismo topic cada gate) | Research cacheable | Memory check antes de ejecutar Librarian; si findings fresh (<7d) → SKIP |

---

## K. Conclusión

El diseño integra research como **parte nativa del flujo OMO** mediante:

1. **Research Gate** — checkpoint pre-build que responde "¿hay algo mejor que lo que voy a hacer?"
2. **Research Feed** — conocimiento continuo que mantiene el sistema actualizado automáticamente
3. **Research Memory Layer** — findings con metadatos que todos los agentes consultan en PHASE 0

**10 horas de implementación** (~1.25 días efectivos), puede correr en paralelo con Wave 4 del Master Plan. No requiere nuevo agente (Oracle se implementa como Metis + Librarian + skill existente nx-oracle-consult).

El diseño garantiza que:
- Tasks SIMPLE no pagan latencia de research
- Tasks COMPLEX se benefician de best practices actualizadas
- El sistema mejora con el tiempo (más research = mejores decisiones)
- No hay duplicación de esfuerzo (caché en memoria)
