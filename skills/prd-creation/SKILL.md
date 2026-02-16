---
name: prd-creation
description: Progressive discovery workflow for creating comprehensive PRDs with user control and market research
license: MIT
metadata:
  version: "1.0.0"
  author: agent-os
  tags: ["prd", "discovery", "product", "research"]
---

# PRD Creation Skill (Progressive Discovery)

Use this skill when creating Product Requirements Documents through a structured discovery process that gives users control over depth.

## The Problem with Traditional PRD Creation

**❌ Old Approach:**
- Ask 20+ questions upfront
- Overwhelms users
- Feels like an interrogation
- Skips business discovery
- Jumps from concept → implementation without validation

**✅ New Approach (Progressive Discovery):**
- Set expectations first
- Ask 5-7 core strategic questions
- Offer "dig deeper" for each area (user chooses)
- Agent reasons about gaps using context
- Summarize + confirm before creating PRD
- Include market research step

---

## Five-Phase Progressive Discovery Flow

### Phase 1: Set Expectations

**Before asking any questions, explain the process:**

```
Great idea! To give you the best results and a ready-to-use [product/feature],
I need to go a bit in-depth to understand your project.

I'll ask you some key strategic questions about:
• The problem you're solving
• Who you're building this for
• How you plan to make this sustainable
• The key features and value proposition

This should only take 5-10 minutes, and you can choose which areas
you'd like to explore in more detail. Sound good?
```

**Why this works:**
- Explains the "why" (not arbitrary questions)
- Sets time expectations (5-10 minutes)
- Gives user control ("choose which areas to explore")
- Gets buy-in before proceeding

---

### Phase 2: Core Strategic Questions (5-7 Only)

Ask ONLY these essential questions. Each question has an optional "dig deeper" path.

#### Question 1: Problem & Value Proposition
```
What specific problem does this solve for your users?

💡 Need help thinking this through? I can dig deeper into:
• Who has this problem today
• Why existing solutions don't work
• What makes your approach different
```

#### Question 2: Target Audience
```
Who exactly is this for? (e.g., beginners, professionals, students, etc.)

💡 Want to dig deeper? I can help you:
• Define your ideal user profile
• Understand their goals and pain points
• Identify which segment to prioritize first
```

#### Question 3: Business Model / Sustainability
```
How do you plan to sustain this? (free, paid memberships, sponsors, etc.)

💡 Dig deeper? I can explore:
• Revenue models that work for communities/products like this
• Pricing strategies
• Alternative funding sources
```

#### Question 4: Key Features / What Makes This Valuable
```
What will users get from this? (events, features, resources, etc.)

💡 Want to explore this more? I can help you:
• Prioritize which features to launch with
• Design the feature set that provides most value
• Think through the user journey
```

#### Question 5: Success Metrics
```
How will you know if this is working? (e.g., X users in 3 months,
Y engagement rate, etc.)

💡 Dig deeper? I can help define:
• Short-term vs long-term success metrics
• Early validation signals
• What would indicate this isn't working
```

#### Question 6 (Optional): Competitive Landscape
```
Are there similar products/communities? What makes yours different?

💡 Want to explore this? I can help you:
• Identify your unique positioning
• Find gaps in existing solutions
• Define your differentiators
• Research competitors using web search
```

#### Question 7 (Optional): Long-term Vision
```
Where do you see this in 6-12 months?

💡 Dig deeper? I can help you think through:
• Scaling challenges
• Product roadmap
• Expansion opportunities
```

---

### Phase 3: "Dig Deeper" Pattern

**When user opts in to dig deeper on a topic:**

Example: User says "yes, dig deeper on target audience"

```
Great! Let's get specific about your target audience:

1. What's their current skill/experience level?
   • Complete beginners?
   • Intermediate users?
   • Advanced/expert level?
   • Mix of all?

2. What are they trying to achieve?
   • Career transition?
   • Skill development?
   • Community and networking?
   • Finding collaborators?

3. What's currently stopping them from achieving that?

4. Why would they choose your product over alternatives?
```

**Rules for deep dives:**
- Only ask if user opts in
- Keep to 3-5 follow-up questions per area
- Make questions specific and actionable
- Connect answers back to product decisions
- Always offer a "skip" option

**User can say:**
- "Skip" or "let's move on" → Continue to next question
- "Not sure" or "you decide" → Agent makes reasonable assumptions

---

### Phase 4: Market Research (NEW STEP)

**After core questions, offer research:**

```
Before we create the PRD, would you like me to:

1. 🔍 Research competitors in this space
2. 📊 Look up market trends and best practices
3. 💡 Find similar products for inspiration

This takes 1-2 minutes and gives us valuable context.
Would you like me to do this research? (yes/no/skip)
```

**If user says yes:**

Use DuckDuckGoTools (`duckduckgo_search` tool) to research:
- Competitors (search for "[product type] [industry]" - e.g., "women tech community Bangkok")
- Market trends ("best practices for [product type]")
- Pricing models ("pricing strategies for [product type]")
- Success metrics ("key metrics for [product type]")

The agent has access to DuckDuckGoTools which provides web search results with URLs and snippets.

**Present research findings:**
```
Here's what I found:

**Competitors:**
- [Competitor 1]: [brief description] - [URL]
- [Competitor 2]: [brief description] - [URL]

**Key Insights:**
- [Insight 1 from research]
- [Insight 2 from research]

**Opportunities:**
- [Gap 1 you could fill]
- [Gap 2 you could fill]

Based on this, here are my recommendations:
- [Recommendation 1]
- [Recommendation 2]

Does this change anything about your vision, or should we proceed as planned?
```

---

### Phase 5: Summary + Confirmation (CRITICAL STEP)

**Before creating ANY documents, MUST summarize and get confirmation:**

```
Perfect! Let me make sure I understand correctly:

**Project:** [Name]

**Problem:** [Problem statement from user's answers]

**Target Audience:** [Audience description from user's answers]

**Value Proposition:**
• [Value 1]
• [Value 2]
• [Value 3]

**Business Model:** [Revenue model or sustainability plan]

**Success Metrics:**
• [Metric 1]
• [Metric 2]

**Key Features** (if discussed):
• [Feature 1]
• [Feature 2]

**Competitors & Research Insights** (if research was done):
• [Key finding 1]
• [Key finding 2]

**Landing Page/Product Goal:** [What the deliverable should achieve]

**Is this correct?**
👍 Yes, that's right
✏️  No, let me correct something
➕ Add something I forgot
```

**Why this is critical:**
- Catches misunderstandings before wasted work
- Gives user chance to refine their own thinking
- Creates shared understanding between user and agent
- Prevents "that's not what I meant" after PRD is done

**Agent must wait for confirmation before proceeding.**

---

## Agent Reasoning When User Doesn't Dig Deeper

If user answers core questions but doesn't want to dig deeper, agent should **make context-based assumptions**:

**Example:**

User said: "This is for women in Bangkok's tech scene, mix of beginners and professionals, focused on learning AI tools and networking."

**Agent reasoning:**

Context clues suggest:
• Target audience likely skews younger (20s-30s) since Bangkok has young tech scene
• Learning AI tools suggests they're early adopters, tech-curious
• Mix of skill levels means content needs to be accessible to beginners but valuable to experienced folks
• Bangkok context suggests True Digital Park, The Hive are relevant coworking spots
• Women-only focus suggests safety, supportive environment are key values

**Inferred product requirements:**
• Use welcoming, approachable language (not corporate)
• Highlight "beginner-friendly" explicitly
• Show range of events (intro to AI + advanced topics)
• Feature locations prominently
• Include testimonials/photos showing diverse skill levels

**Document Assumptions in PRD:**

```
## Assumptions Made
(Based on limited discovery - recommend validating with target users)

1. Target age range: 20s-40s (inferred from young Bangkok tech scene)
2. Primary motivation: Community + learning over pure networking
3. Preferred communication: WhatsApp/Telegram (common in Bangkok)
4. Event frequency: Weekly coworking, monthly workshops
5. Price sensitivity: High (starting free is appropriate)
```

---

## PRD Creation After Confirmation

Only after user confirms the summary, create the PRD with:

### Required Sections:

1. **DOCUMENT HEADER** (exactly as specified in main instructions)
2. **EXECUTIVE SUMMARY** - Based on confirmed understanding
3. **PROBLEM STATEMENT** - From Phase 2, Question 1
4. **TARGET USERS** - From Phase 2, Question 2 (+ deep dive if done)
5. **PRODUCT VISION** - From combined user answers
6. **GOALS & SUCCESS METRICS** - From Phase 2, Question 5
7. **COMPETITIVE ANALYSIS** (if research was done) - From Phase 4
   - Top 3-5 competitors
   - Gaps and opportunities
   - Differentiation strategy
8. **FEATURE REQUIREMENTS - P0 (MUST HAVE)** - From Phase 2, Question 4
9. **FEATURE REQUIREMENTS - P1 (SHOULD HAVE)** - From deep dives or assumptions
10. **FEATURE REQUIREMENTS - P2 (NICE TO HAVE)** - From long-term vision (Question 7)
11. **USER FLOW** - Inferred from feature requirements
12. **CONTENT & ASSETS PROVIDED** - All links, images, resources from discovery
13. **BUSINESS MODEL & MONETIZATION** - From Phase 2, Question 3
14. **TECHNICAL CONSIDERATIONS** - Inferred from requirements
15. **ASSUMPTIONS** (NEW SECTION) - Document all assumptions made when user said "you decide"
16. **RESEARCH INSIGHTS** (if research was done) - Key findings from Phase 4
17. **OUT OF SCOPE (V1)** - What this version won't include
18. **OPEN QUESTIONS** - Remaining unknowns
19. **TIMELINE & MILESTONES** - If discussed

---

## Handling User Responses

### "I don't know" / "You decide" / "Assume"
- Make a reasonable assumption based on context
- State assumption clearly: "I'll assume [X] for now — we can change this later."
- Note it in the PRD under "Assumptions" section
- Move on to next area — do NOT block on it

### "Skip" / "Let's move on"
- Acknowledge: "No problem, moving on..."
- Continue to next question
- Note the skipped area in "Open Questions" if critical

### User provides detailed answer
- Acknowledge: "Got it! That's really helpful."
- Don't immediately dig deeper — first ask the next core question
- Only offer "dig deeper" after asking all 5-7 core questions

---

## Example: Full Progressive Discovery Flow

```
PHASE 1: Set Expectations
Agent: Great idea! To give you the best results, I need to go a bit in-depth...
User: Okay, let's do it.

PHASE 2: Core Questions
Agent: What specific problem does this solve for your users?
User: Women in Bangkok's tech scene lack supportive, women-only spaces for learning and networking.

Agent: 💡 Need help thinking this through? I can dig deeper into who has this problem, why existing solutions don't work, etc.
User: No, let's move on.

Agent: Who exactly is this for?
User: Mix of skill levels—from beginners learning AI/tech to professionals wanting community.

[Continue through 5-7 questions]

PHASE 3: Optional Deep Dive (if user opts in)
[User opted to dig deeper on Business Model]
Agent: Let's explore revenue models...
[3-5 follow-up questions]

PHASE 4: Market Research
Agent: Would you like me to research competitors in this space?
User: Yes, please!

Agent: [Uses web search] Here's what I found...
[Presents research findings]

PHASE 5: Summary + Confirmation
Agent: Perfect! Let me make sure I understand correctly: [Summary]
User: ✅ Yes, that's right

Agent: Great! I'm now creating:
• Product Requirements Document (PRD)
[Creates PRD with all sections]
```

---

## Integration with Workflow

This skill integrates with the Product Requirements Workflow:

1. **Product Lead** uses this skill for discovery
2. After Phase 5 confirmation → **Product Lead** creates PRD
3. **Lead Engineer** reads PRD and creates Architecture
4. **Supervisor** validates both documents
5. **Software Engineer** implements

---

## Checklist Before Creating PRD

- [ ] Set expectations (Phase 1 completed)
- [ ] Asked 5-7 core strategic questions (Phase 2 completed)
- [ ] Offered "dig deeper" for key areas
- [ ] Conducted market research (if user requested)
- [ ] Summarized understanding and got user confirmation (Phase 5 completed)
- [ ] Documented all assumptions made
- [ ] Collected all user-provided links and assets
- [ ] Ready to create comprehensive PRD

---

## Benefits of Progressive Discovery

✅ User feels in control (not interrogated)
✅ Faster discovery (5-10 minutes vs 30+ minutes)
✅ Focuses on strategic questions (not implementation details)
✅ Agent reasons about gaps (makes smart assumptions)
✅ Confirmation step prevents misalignment
✅ Market research adds validation
✅ Clear expectations set upfront

---

## References

- See `references/question-frameworks.md` for question templates
- See `references/assumption-templates.md` for making smart assumptions
- See `references/market-research-guide.md` for research best practices
