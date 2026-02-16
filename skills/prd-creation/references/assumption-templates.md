# Making Smart Assumptions

When users say "I don't know", "you decide", or skip questions, use context clues to make intelligent assumptions.

## Assumption Framework

### Step 1: Gather Context Clues
- What industry/domain is this in?
- What has the user already told you?
- What's typical for this type of product?
- What patterns exist in similar products?

### Step 2: Make Logical Inferences
- If X is true, what else is likely true?
- What's the simplest/most common approach?
- What would industry best practices suggest?

### Step 3: Document Assumptions
- State what you're assuming
- Explain your reasoning
- Mark for validation later

---

## Common Assumption Patterns

### Pattern 1: Geographic Assumptions

**User says**: "This is for students in the US"

**Context clues**:
- US students → likely ages 18-25
- US → English language primary
- Students → price sensitive, mobile-first

**Assumptions to make**:
```
1. Target age: 18-25 (inferred from "students")
2. Primary language: English
3. Device preference: Mobile-first (Gen Z behavior)
4. Price sensitivity: High (students have limited budgets)
5. Tech familiarity: High (digital natives)
```

---

### Pattern 2: Industry Assumptions

**User says**: "This helps restaurants"

**Context clues**:
- Restaurants → busy, need quick solutions
- Restaurant staff → varied tech literacy
- Restaurant operations → peak hours, time-sensitive

**Assumptions to make**:
```
1. Primary users: Restaurant owners/managers (assume main decision-makers)
2. Tech literacy: Mixed (some staff tech-savvy, some not)
3. Usage pattern: Peak at lunch/dinner prep times
4. Key pain points: Speed, ease of use, reliability
5. Mobile vs desktop: Both (office for setup, mobile for floor use)
```

---

### Pattern 3: Audience Size Assumptions

**User says**: "I don't know how many users to expect"

**Context clues**:
- Type of product (niche vs broad appeal)
- Geographic scope (local vs global)
- Marketing plan (word-of-mouth vs paid ads)

**Assumptions to make**:
```
For LOCAL community product:
- Month 1: 20-50 early adopters
- Month 3: 100-200 active users
- Month 6: 500+ community members

For NICHE SaaS product:
- Month 1: 10-20 beta testers
- Month 3: 50-100 paying customers
- Month 6: 200-500 paid users

For BROAD consumer app:
- Month 1: 100-500 signups
- Month 3: 1,000-5,000 users
- Month 6: 10,000+ users
```

---

### Pattern 4: Tech Stack Assumptions

**User doesn't mention tech preferences**

**Context clues**:
- Project complexity (simple landing page vs full app)
- Features mentioned (auth, database, real-time)
- User's background (technical vs non-technical)

**Assumptions to make**:
```
For SIMPLE landing page (no auth, no database):
- Tech stack: HTML5, CSS3, Vanilla JavaScript
- Hosting: Vercel static hosting
- Why: No build tools needed, fast, beginner-friendly

For INTERACTIVE app (dashboard, forms, no database):
- Tech stack: React + Vite, Tailwind CSS
- Hosting: Vercel
- Why: Component-based, modern, scalable

For FULL-STACK app (auth, database, API):
- Tech stack: Next.js, TypeScript, Supabase, Tailwind
- Hosting: Vercel
- Why: Full-stack support, built-in auth, database, serverless
```

---

### Pattern 5: Business Model Assumptions

**User says**: "Not sure about pricing yet"

**Context clues**:
- Target audience (consumers vs businesses)
- Product value (saves time, saves money, creates revenue)
- Competitive landscape (free alternatives vs paid tools)

**Assumptions to make**:
```
For B2C consumer product:
- Start: Free tier to build audience
- Later: $5-15/month for premium features
- Why: Consumers price-sensitive, need to try before buy

For B2B SaaS product:
- Start: Free trial (14-30 days)
- Pricing: $29-99/month per user
- Why: Businesses pay for ROI, need trial to prove value

For Community/Platform:
- Start: Free for all
- Later: Sponsors, premium features, or events
- Why: Network effects need free tier, monetize at scale
```

---

## How to Document Assumptions

### Template for PRD "ASSUMPTIONS" Section:

```markdown
## ASSUMPTIONS MADE
(Based on limited discovery - recommend validating with target users)

### Target Audience Assumptions:
1. [Assumption] - [Reasoning based on context clue]
2. [Assumption] - [Reasoning based on context clue]

### Product Assumptions:
1. [Assumption] - [Reasoning based on industry best practices]
2. [Assumption] - [Reasoning based on similar products]

### Business Model Assumptions:
1. [Assumption] - [Reasoning based on target audience]
2. [Assumption] - [Reasoning based on competitive analysis]

### Technical Assumptions:
1. [Assumption] - [Reasoning based on feature requirements]
2. [Assumption] - [Reasoning based on scalability needs]

**VALIDATION NEEDED:**
- [ ] Validate target age range with user research
- [ ] Confirm pricing expectations with potential customers
- [ ] Test tech stack assumptions with prototype
```

---

## Real-World Example

**User Input**: "I want to create a community for women in tech in Bangkok"

**Assumptions Made**:

```markdown
## ASSUMPTIONS MADE
(Based on limited discovery - recommend validating with target users)

### Target Audience Assumptions:
1. Age range: 20s-40s - Bangkok has a young tech scene, and "women in tech" typically
   skews younger for early-career professionals and students
2. Skill levels: Mixed (beginners to professionals) - Community appeals to both learning
   and experienced members
3. Motivation: Career development + networking + community - Women-only spaces suggest
   need for supportive environment beyond just technical learning
4. Language: English + Thai - Bangkok is international, tech community uses English,
   but local context suggests Thai also needed

### Product Assumptions:
1. Event format: Regular meetups (monthly) + coworking sessions (weekly) - Common pattern
   for tech communities
2. Communication: WhatsApp/LINE/Telegram - Most popular messaging apps in Bangkok
3. Location: Central Bangkok (Sukhumvit, Silom area) - Where tech companies and coworking
   spaces are concentrated
4. Initial size: 50-100 founding members in first 3 months - Typical for local niche communities

### Business Model Assumptions:
1. Start free to build community - Common for community products, monetize later
2. Future revenue: Event fees ($5-10), sponsors (tech companies), premium features -
   Standard community monetization
3. Costs: Minimal (using existing cafes/coworking spaces) - No need for dedicated space initially

### Technical Assumptions:
1. Landing page only for v1 - Email signup, event calendar, WhatsApp link
2. No custom app needed initially - Use existing tools (WhatsApp, Google Forms, Eventbrite)
3. Tech stack: Simple HTML/CSS/JS - No complex features needed for v1

**VALIDATION NEEDED:**
- [ ] Survey potential members on preferred event times/locations
- [ ] Test willingness to pay for premium features
- [ ] Validate communication channel preferences (WhatsApp vs LINE vs Telegram)
- [ ] Confirm skill level distribution with pilot event
```

---

## Best Practices

### DO:
✅ Make assumptions based on context clues
✅ Document all assumptions transparently
✅ Mark assumptions for validation
✅ Use industry best practices as guide
✅ Reference similar products/communities

### DON'T:
❌ Guess randomly without reasoning
❌ Hide assumptions in the document
❌ Make assumptions that contradict user input
❌ Over-engineer based on assumptions
❌ Block on unknowns (make assumption and move on)

---

## When to Push Back vs Make Assumptions

### Push back when:
- Critical business decision (pricing model, target market)
- Legal/compliance requirements (privacy, data handling)
- Technical feasibility unknown (complex integrations)
- User explicitly needs to decide (brand identity, core features)

### Make assumptions when:
- Nice-to-have details (color scheme, font choices)
- Standard practices (mobile responsive, HTTPS)
- Implementation details (tech stack if not specified)
- Timeline/milestones if user is flexible
- Edge cases and error handling

---

## Assumption Quality Checklist

Before documenting an assumption, verify:
- [ ] Is this based on actual context from the user?
- [ ] Is this a reasonable inference from industry norms?
- [ ] Would most people in this industry agree with this?
- [ ] Can this be validated easily later?
- [ ] Does this help move the project forward?
- [ ] Is this clearly marked as an assumption (not fact)?
