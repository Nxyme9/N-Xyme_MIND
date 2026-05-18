---
name: bmad-review-adversarial-general
description: Perform a Cynical Review and produce a findings report. Use when user says "critical review" or "tear this apart".
argument-hint: "[document-or-plan-path] [review-focus]"
---

# Adversarial Review — General

## Overview
A cynical, thorough review of a document, plan, or decision. Find every weakness, assumption, oversight, and risk.

## On Activation
1. **Read input.** Understand what's being reviewed.
2. **Apply adversarial lenses.** Below.
3. **Report findings.** Categorized by severity.

## Adversarial Lenses
1. **The Optimist** — "This is great because..."
2. **The Pessimist** — "This will fail because..."
3. **The Realist** — "The actual constraint is..."
4. **The Lawyer** — "What are we assuming without checking?"
5. **The Historian** — "We've seen this fail before when..."

## Output Format
```
## CRITICAL (must fix)
- [finding] — risk, impact, suggested fix

## MAJOR (should fix)
...

## MINOR (consider)
...

## NIT (ignore if busy)
...
```