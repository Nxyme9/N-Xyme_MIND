---
description: End-to-end pipeline for generating a highly personalized, non-generic portfolio site using NotebookLM data and external visual assets.
created: 2026-02-27
last_updated: 2026-02-27
---

# /notebook-portfolio — The Zero-to-Agency Pipeline

> **Latency Profile**: HIGH (Multi-Modal / Multi-Agent)
> **Source**: Zinho Automates / Protocol 221 (Grounded Generation)
> **Philosophy**: A "$10k Portfolio" requires real data and real assets. Generic templates and placeholder text are prohibited.

## Trigger

User asks to build, design, or scaffold a portfolio website, personal site, or complex landing page.

---

## Phase 1: Context Preparation (The Data Dump)

**Do not write a single line of HTML until this phase is complete.**

1. Instruct the user to open Google NotebookLM and create a new notebook.
2. Instruct the user to upload all foundational raw materials:
   - Full Resume / CV
   - Detailed descriptions of past projects / Case Studies
   - Professional Bio
   - Client Testimonials
   - Reference websites (links or PDFs of sites they like)
3. Once the notebook is ready, proceed to Phase 2.

---

## Phase 2: The Structural Build

Execute the build using the `/notebooklm-bridge` pattern. Use the exact prompt below to initialize the structural code generation.

**Prompt to execute:**
> "Create a detailed portfolio website based on the [insert Notebook name] notebook from NotebookLM. Follow Protocol 221 strictly. Build the structural HTML, CSS, and JS using *only* the real extracted data from the notebook. Do not use 'Lorem Ipsum' or hallucinated projects."

*Result*: Athena builds the initial web structure grounded purely in reality.

---

## Phase 3: Visual Asset Generation (Halt & Delegate)

**Halt execution.** Do not leave empty `<img src="">` tags. Demand high-quality external assets from the user before proceeding to polish.

Instruct the user:
> "Structure complete. To achieve the 'Agency' look, we need custom assets. Please use Higgsfield AI (or Midjourney/Runway) to generate:
>
> 1. A dynamic Hero background video (Note: convert this to a `.jpg` image sequence for smooth web interpolation).
> 2. Custom thumbnails for each project generated in Phase 2.
> 3. Your headshot. If your current headshot is poor quality, use the 'Studio Relight' feature to adjust the lighting to professional studio standards."

Wait for the user to provide the directory containing these new assets.

---

## Phase 4: Integration & Visual Polish

Once the user provides the generated assets, stitch them into the build and harmonize the design.

**Prompt to execute:**
> "Add the hero image sequence, the custom project thumbnails, and the relit about-section headshot to the portfolio code. Extract the dominant color palettes from these new image assets and immediately adjust the CSS hero gradients, button accents, and overall color scheme to match perfectly. Add smooth scale animations (`1.05x`) for interactive elements."

*Result*: A cohesive, data-grounded, visually stunning portfolio site built in minutes.

---

## Tagging

# workflow #portfolio #notebooklm #design #higgsfield #assets
