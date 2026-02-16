---
name: architecture-creation
description: Create comprehensive technical architecture documents including database design and environment configuration
license: MIT
metadata:
  version: "1.0.0"
  author: agent-os
  tags: ["architecture", "technical-spec", "database", "planning"]
---

# Architecture Creation Skill

Use this skill when creating technical architecture documents from Product Requirements Documents (PRDs) or Feature Specifications.

## When to Use

- User provides a PRD or Feature Specification
- Product Lead delegates a project for technical planning
- Creating architecture for a new feature or project
- Documenting existing system architecture
- Planning system redesign or refactoring

## Process

1. **Read and Analyze PRD**: Extract requirements, features, constraints
2. **Determine Technology Stack**: Choose appropriate technologies based on complexity
3. **Design System Architecture**: Define components, data flow, integrations
4. **Design Database Schema**: Create data models, relationships, RLS policies (if needed)
5. **Document Environment Variables**: List all required configuration
6. **Plan File Structure**: Organize code, assets, configuration files
7. **Create Implementation Guide**: Provide clear instructions for engineers

## CRITICAL: Document Header Format

Every Architecture document MUST start with this exact header (first 6 lines):

```
DOCUMENT TYPE: Technical Architecture Document
PROJECT TYPE: [New Project / Existing Project]
PROJECT ID: [Project ID from context]
PROJECT NAME: [Exact project name]
TECH STACK: [Primary technologies - e.g., "Next.js, TypeScript, Tailwind CSS, Supabase" or "HTML5/CSS3/JavaScript"]

====================================================================================================
```

**Document Title Format:** `Architecture_[ProjectName]_[ProjectID]`

Example: `Architecture_TaskManager_39726658`

## Required Sections

### 1. Technology Stack Decision
- **Chosen Stack**: List all technologies (frontend, backend, database, deployment)
- **Justification**: Explain why this stack fits the requirements
- **Alternatives Considered**: Briefly mention why alternatives were rejected

### 2. Overview
- High-level system description
- Key components and their responsibilities
- Integration points with external services

### 3. GitHub Repository (CRITICAL for Existing Projects)
If this is an **EXISTING PROJECT**, include:
```markdown
**GitHub Repository:** https://github.com/owner/repo-name
```
This tells the Software Engineer to UPDATE the existing repo, not create a new one.

### 4. File/Folder Structure
Show the complete directory structure:
```
/
  index.html
  css/
    styles.css
  js/
    script.js
  supabase/
    migrations/
      20240101_initial_schema.sql
  .env.example
  README.md
```

### 5. Frontend Architecture
- Page layouts and components
- Routing strategy (if applicable)
- State management approach
- UI component breakdown

### 6. **Database Schema** (NEW REQUIREMENT)
**If the project requires a database**, include a comprehensive database section:

#### Database Schema Design
```sql
-- Full SQL schema with all tables, columns, types, constraints
-- Include comments explaining design decisions
-- Document all foreign key relationships
```

#### Entity Relationships
- List all table relationships (one-to-many, many-to-many)
- Explain junction tables if used

#### Row Level Security Policies
```sql
-- All RLS policies for data isolation
-- Document policy logic and use cases
```

#### Indexes and Performance
```sql
-- Indexes for query optimization
-- Explain which queries benefit from each index
```

### 7. **Environment Variables** (NEW REQUIREMENT)
**Always include** a comprehensive list of required environment variables:

```bash
# Database Configuration (if using Supabase)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... # Server-side only

# Vercel Configuration (if deploying to Vercel)
VERCEL_TOKEN=xxxxx

# GitHub Configuration (if using GitHub API)
GITHUB_TOKEN=ghp_xxxxx

# Other API Keys (example)
STRIPE_SECRET_KEY=sk_test_xxxxx
SENDGRID_API_KEY=SG.xxxxx
```

**For each environment variable**, document:
- Where to obtain it (e.g., "From Supabase Dashboard > Settings > API")
- Whether it's required or optional
- Whether it's client-side (safe to expose) or server-side (must be secret)

### 8. Styling Strategy
- CSS framework (Tailwind, Bootstrap, custom CSS)
- Design system and theme variables
- Responsive breakpoints

### 9. Data Layer (if applicable)
- Database choice and rationale
- API design (REST, GraphQL)
- Authentication and authorization flow
- Data validation strategy

### 10. Assets & User-Provided Links
**CRITICAL: PRESERVE ALL LINKS from PRD/Feature Spec**

Include every link mentioned in the source document:
- Image URLs (Unsplash, user-provided images)
- Font links (Google Fonts, Adobe Fonts)
- Icon libraries (FontAwesome, Material Icons)
- External scripts (analytics, chat widgets)
- Social media URLs
- Contact links (email, phone, WhatsApp)
- Video/media URLs
- Documentation/reference links

**Rule: If a link exists in the PRD, it MUST exist in the Architecture document.**

### 11. Build & Deployment
- Build tools and process
- Deployment platform (Vercel, Netlify, Railway)
- CI/CD pipeline (if applicable)
- Environment-specific configurations

### 12. Browser/Environment Support
- Target browsers and versions
- Node.js version requirements
- Device compatibility (desktop, mobile, tablet)

### 13. Implementation Notes
- Key technical considerations
- Potential gotchas and edge cases
- Best practices for this specific project
- Testing strategy

## Example: Database-Integrated Architecture

```markdown
## Database Schema

### Tables

**users** (extends Supabase Auth)
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**tasks** (user's tasks)
```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT CHECK (status IN ('todo', 'in_progress', 'done')) DEFAULT 'todo',
  due_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
```

### Row Level Security

```sql
-- Users can only see their own tasks
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD own tasks" ON tasks
  FOR ALL USING (auth.uid() = user_id);
```

### Environment Variables

```bash
# Supabase Configuration
SUPABASE_URL=https://xxxxx.supabase.co                    # From Supabase Dashboard
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... # Public key (safe for client)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI... # Server-only (NEVER expose)

# Database Direct Connection (for migrations)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```
```

## Technology Stack Decision Framework

### Simple Static Sites (landing pages, portfolios)
**Stack:** HTML5, CSS3, Vanilla JavaScript
**Database:** None (or simple localStorage)
**Deploy:** Vercel static, GitHub Pages

### Interactive Web Apps (dashboards, SaaS)
**Stack:** React/Next.js, TypeScript, Tailwind CSS
**Database:** Supabase (if data persistence needed)
**Deploy:** Vercel

### Full-Stack Applications (auth, database, APIs)
**Stack:** Next.js, TypeScript, Supabase, Tailwind CSS
**Database:** Supabase PostgreSQL + Auth + Storage
**Deploy:** Vercel

### Content-Heavy Sites (blogs, CMS)
**Stack:** Next.js + MDX, Tailwind CSS
**Database:** Supabase (for user comments, analytics)
**Deploy:** Vercel

## Checklist Before Finalizing Architecture

- [ ] Document header is complete and formatted correctly
- [ ] Technology stack is appropriate for project complexity
- [ ] File structure is clearly defined
- [ ] **Database schema is included** (if project needs data persistence)
- [ ] **All environment variables are documented** with clear instructions
- [ ] **All links from PRD are preserved** in the architecture document
- [ ] GitHub repository URL is included (for existing projects)
- [ ] Styling strategy is defined
- [ ] Build and deployment process is documented
- [ ] Implementation notes provide clear guidance for engineers
- [ ] Security considerations are addressed (RLS policies, auth flow)

## Integration with Other Agents

### Product Lead → Lead Engineer
Product Lead provides PRD URL → Lead Engineer uses this skill to create Architecture

### Lead Engineer → Database Engineer
If architecture requires database → Lead Engineer consults Database Engineer to design schema

### Lead Engineer → Software Engineer
Architecture document guides Software Engineer's implementation

## References

- See `references/tech-stack-decision-guide.md` for technology selection criteria
- See `references/environment-variables-guide.md` for env var best practices
- See `../database-schema-design/SKILL.md` for database design guidelines
