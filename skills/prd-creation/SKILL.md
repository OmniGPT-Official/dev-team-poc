---
name: prd-creation
description: Progressive discovery workflow for creating comprehensive PRDs with user control and market research
license: MIT
metadata:
  version: "2.0.0"
  author: agent-os
  tags: ["prd", "discovery", "product", "research"]
---

# PRD Creation Skill (Progressive Discovery)

Use this skill when creating Product Requirements Documents through a conversational discovery process that gives users control over depth.

## Overview

This skill provides the Product Lead with:
- **Question frameworks** for each discovery area (see `references/question-frameworks.md`)
- **Assumption templates** for when users say "you decide" (see `references/assumption-templates.md`)
- **Market research patterns** using DuckDuckGo web search

## Discovery Flow

1. **Welcome & set expectations** — Briefly explain what you need, set 5-10 min time estimate, get buy-in
2. **Strategic questions** — Cover 5 core areas (problem, audience, business model, features, metrics) with "dig deeper" options
3. **Deep dives** — 3-5 follow-ups per area, only when user opts in
4. **Market research** — Optional competitor/trend research via web search
5. **Summary & confirmation** — Present findings, get user approval before creating anything

## Core Question Areas

Each area has a core question and optional deep-dive follow-ups. See `references/question-frameworks.md` for detailed templates.

### Problem & Value Proposition
Core: What specific problem does this solve for your users?
Deep dive: Problem validation, current solutions, differentiation, "aha moment"

### Target Audience
Core: Who exactly is this for?
Deep dive: Demographics, psychographics, behaviors, segmentation priority

### Business Model
Core: How do you plan to sustain this?
Deep dive: Revenue model, pricing strategy, alternative funding

### Key Features
Core: What will users get from this?
Deep dive: Feature prioritization (P0/P1/P2), user journey, core loop

### Success Metrics
Core: How will you know if this is working?
Deep dive: Leading indicators, lagging indicators, failure signals

### Competitive Landscape (optional)
Core: What similar products exist? What makes yours different?
Deep dive: Positioning, gaps, differentiators + web research

### Long-term Vision (optional)
Core: Where do you see this in 6-12 months?
Deep dive: Scaling challenges, roadmap, business evolution

## "Dig Deeper" Rules

- Only when user opts in
- 3-5 targeted follow-ups per area
- Specific and actionable questions
- Always tie answers back to product decisions
- Offer "skip" at any point

## Market Research (Optional)

When user agrees, use DuckDuckGo to search for:
- `"[product type] [industry]"` — competitors
- `"best practices for [product type]"` — industry patterns
- `"pricing strategies for [product type]"` — monetization models
- `"[product type] competitors"` — competitive landscape

Present: Competitors, key insights, gaps/opportunities, recommendations.

## Making Smart Assumptions

When user says "I don't know" / "you decide" / "skip":
1. Infer from context clues (industry, geography, audience profile)
2. State clearly: "I'll assume X for now — we can adjust later"
3. Document in PRD "ASSUMPTIONS MADE" section
4. Never block — make assumption and move on

See `references/assumption-templates.md` for detailed patterns by category.

## Handling User Responses

| User says | Action |
|-----------|--------|
| Detailed answer | Acknowledge, continue to next area |
| "Dig deeper" | Ask 3-5 targeted follow-ups from frameworks |
| "Skip" / "Move on" | Note in Open Questions if critical, continue |
| "I don't know" / "You decide" | Make smart assumption, state it, continue |

## Checklist Before Creating PRD

- [ ] Set expectations and got buy-in
- [ ] Covered 5+ core strategic areas
- [ ] Offered deep dives on key areas
- [ ] Conducted market research (if requested)
- [ ] Summarized and got user confirmation
- [ ] Documented all assumptions
- [ ] Collected all user-provided links and assets

## References

- `references/question-frameworks.md` — Detailed question templates per area
- `references/assumption-templates.md` — Smart assumption patterns and examples
