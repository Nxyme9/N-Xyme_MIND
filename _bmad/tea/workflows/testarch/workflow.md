---
name: testarch
description: Risk-based test strategy and automation - Design and implement a comprehensive test strategy based on risk assessment and prioritization.
argument-hint: "[project-path] [risk-level]"
---

# Test Architecture Workflow

## Purpose

Design and implement a risk-based test strategy that maximizes test coverage while minimizing redundant testing effort.

## Modes

This workflow supports three modes:

- **Create** (`steps-c/`): Generate new test architecture and strategy
- **Edit** (`steps-e/`): Modify existing test strategy
- **Validate** (`steps-v/`): Verify test strategy completeness

## Workflow Steps

### Step 1: Risk Assessment

Analyze the system to identify:
- Critical business functions
- High-risk areas (complexity, dependencies, change frequency)
- Integration points and data flows
- Regulatory/compliance requirements

### Step 2: Test Strategy Design

Based on risk assessment, determine:
- Test types to implement (unit, integration, E2E, performance)
- Test prioritization approach
- Coverage targets per risk level
- Automation vs manual testing decisions

### Step 3: Test Architecture

Define:
- Test framework and tooling
- Test data management approach
- Test environment requirements
- CI/CD integration points
- Reporting and metrics

### Step 4: Implementation Plan

Create:
- Phased rollout schedule
- Resource allocation
- Skill development plan
- Quality gates for acceptance

## Integration

This workflow integrates with:
- `automate` workflow for test automation
- `trace` workflow for requirements traceability
- `ci` workflow for continuous testing