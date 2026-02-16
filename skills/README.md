# Agent OS Skills

This directory contains specialized skills for Agent OS agents, following the Agno Skills framework.

## What are Skills?

Skills are structured directories containing instructions, scripts, and reference documentation that agents can load on-demand. They provide specialized capabilities and domain knowledge without bloating the main agent prompts.

## Directory Structure

Each skill is a directory with:
- `SKILL.md` - Required: Instructions with YAML frontmatter
- `scripts/` - Optional: Executable scripts the agent can run
- `references/` - Optional: Reference documentation to load on-demand

## Available Skills

### 1. PRD Creation (`prd-creation/`)
**Purpose:** Progressive discovery workflow for creating comprehensive PRDs with user control

**When to use:**
- Starting a new product discovery conversation
- User wants to create a PRD but unsure where to start
- Need to validate product idea with market research
- Want to ensure strategic depth without overwhelming the user

**Key features:**
- Five-phase progressive discovery workflow
- Set expectations before asking questions
- Only 5-7 core strategic questions (not 20+)
- User-controlled "dig deeper" for areas they care about
- Built-in market research step using web search
- Mandatory summary + confirmation before document creation
- Smart assumption-making when user says "you decide"
- Prevents jumping from concept → implementation without validation

**Used by:** Product Lead Agent

---

### 2. Database Schema Design (`database-schema-design/`)
**Purpose:** Design and validate database schemas using Supabase PostgreSQL

**When to use:**
- Creating database architecture for new projects
- Reviewing existing database schemas
- Designing Row Level Security (RLS) policies
- Planning database migrations
- Optimizing database performance

**Key features:**
- Complete schema design guidelines
- RLS policy templates
- Environment variable documentation
- Anti-pattern detection
- Migration best practices

**Used by:** Database Engineer Agent, Lead Engineer Agent

---

### 3. Architecture Creation (`architecture-creation/`)
**Purpose:** Create comprehensive technical architecture documents including database design

**When to use:**
- Converting PRDs to technical specifications
- Planning new projects or features
- Documenting system architecture
- Designing full-stack applications

**Key features:**
- Technology stack decision framework
- Database schema integration
- Environment variable documentation
- File structure planning
- Link preservation from PRDs

**Used by:** Lead Engineer Agent

---

### 4. Code Review (`code-review/`)
**Purpose:** Comprehensive code review including database validation and security checks

**When to use:**
- Reviewing completed implementations
- Validating code before deployment
- Checking database schema quality
- Security audits
- Performance optimization

**Key features:**
- Multi-layer review (frontend, backend, database)
- Security vulnerability detection
- Database schema validation
- RLS policy verification
- Environment variable checks
- File linking validation

**Used by:** Lead Engineer Agent, Security Engineer Agent

---

## How to Use Skills

### Loading Skills in Agents

```python
from agno.agent import Agent
from agno.skills import Skills, LocalSkills

agent = Agent(
    name="Lead Engineer Agent",
    skills=Skills(loaders=[LocalSkills("/path/to/skills")]),
    # ... other config
)
```

### Agent Tools for Skills

When skills are loaded, agents automatically get these tools:

1. `get_skill_instructions(skill_name)` - Load full skill instructions
2. `get_skill_reference(skill_name, reference_path)` - Load reference docs
3. `get_skill_script(skill_name, script_path, execute, args, timeout)` - Run scripts

### Example: Agent Using Database Schema Design Skill

```python
# Agent automatically discovers available skills from system prompt
# When user asks for database design:
response = agent.run("Design a database schema for a task management app")

# Agent internally calls:
# get_skill_instructions("database-schema-design")
# ... reads the skill guidelines and creates schema
```

## Creating New Skills

See [Agno Skills Documentation](https://docs.agno.com/skills) for details on creating skills.

### Quick Start

1. Create skill directory:
```bash
mkdir skills/my-skill
mkdir skills/my-skill/{scripts,references}
```

2. Create `SKILL.md`:
```yaml
---
name: my-skill
description: Short description (max 1024 chars)
license: MIT
metadata:
  version: "1.0.0"
  author: agent-os
  tags: ["tag1", "tag2"]
---

# My Skill

Instructions go here...
```

3. Add scripts (optional):
```bash
# Create executable script
cat > skills/my-skill/scripts/helper.py << 'EOF'
#!/usr/bin/env python3
# Your script code
EOF
chmod +x skills/my-skill/scripts/helper.py
```

4. Add references (optional):
```bash
# Create reference documentation
cat > skills/my-skill/references/guide.md << 'EOF'
# Reference Guide
Documentation goes here...
EOF
```

## Skill Naming Conventions

- Use lowercase with hyphens: `database-schema-design`
- Max 64 characters
- No consecutive hyphens
- Descriptive and specific

## Best Practices

1. **Keep instructions concise** - Focus on when/how to use the skill
2. **Provide examples** - Show good vs bad patterns
3. **Include checklists** - Help agents validate their work
4. **Add references** - Link to detailed documentation
5. **Use scripts** - Automate validation and checks
6. **Version your skills** - Track changes in metadata

## Integration with Workflows

Skills integrate seamlessly with Agent OS workflows:

1. **Product Requirements Workflow**
   - Product Lead creates PRD
   - Uses architecture-creation skill for technical specs

2. **Software Development Workflow**
   - Lead Engineer uses database-schema-design for schema
   - Uses architecture-creation for full architecture
   - Uses code-review for validation

3. **Database Management**
   - Database Engineer uses database-schema-design skill
   - Creates migrations and RLS policies
   - Validates existing schemas

## Troubleshooting

### Skills not loading
- Check SKILL.md has valid YAML frontmatter
- Verify `name` field matches directory name
- Ensure file permissions are correct

### Scripts not executing
- Add shebang line: `#!/usr/bin/env python3`
- Make script executable: `chmod +x script.py`
- Test script manually first

### References not found
- Check file paths are relative to skill directory
- Verify reference files exist in `references/` directory

## Contributing

When adding new skills:
1. Follow the naming conventions
2. Include comprehensive SKILL.md
3. Add examples and checklists
4. Document integration points
5. Update this README

## Resources

- [Agno Skills Documentation](https://docs.agno.com/skills)
- [Creating Skills Guide](https://docs.agno.com/skills/creating)
- [Loading Skills Guide](https://docs.agno.com/skills/loading)
