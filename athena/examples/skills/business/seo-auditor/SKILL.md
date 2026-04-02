---
name: seo-auditor
description: Scrapes a URL, runs Lighthouse equivalent checks, and outputs a strategic content/architecture plan.
argument-hint: "scan <url>"
allowed-tools:
  - WebFetch
  - Bash
auto-invoke: false
model: default
---

# Technical SEO & Content Auditor

Performs a comprehensive technical and structural scan of a targeted domain, identifying immediate content gaps and architecture failures.

## Triggers

"audit website", "seo check", "why isn't this ranking"

## Core Mechanics

1. Pulls raw DOM structure.
2. Evaluates H1-H6 hierarchy, semantic tags, and internal link depth.
3. Outputs a prioritized `seo_triage_plan.md` focusing on "Barnacle SEO" opportunities.

## Reference Paths

- `.context/memories/protocols/marketing/279-seo-channel-strategy.md`
