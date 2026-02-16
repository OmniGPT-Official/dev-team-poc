---
name: database-schema-design
description: Design and validate database schemas with Supabase PostgreSQL best practices
license: MIT
metadata:
  version: "1.0.0"
  author: agent-os
  tags: ["database", "supabase", "postgresql", "schema"]
---

# Database Schema Design Skill

Use this skill when designing or validating database schemas for projects that require data persistence.

## When to Use

- User asks for database schema design or data modeling
- Architecture document requires database integration
- Reviewing existing database schema for issues
- Planning migrations or schema changes
- Integrating Supabase Auth, Storage, or Realtime features

## Process

1. **Analyze Requirements**: Review PRD/Architecture for data needs
2. **Design Schema**: Create normalized tables with proper relationships
3. **Define Constraints**: Add NOT NULL, UNIQUE, CHECK, foreign keys
4. **Plan Indexes**: Optimize for expected query patterns
5. **Configure RLS**: Set up Row Level Security policies for data isolation
6. **Document Environment Variables**: List all required database connection strings
7. **Validate Against Best Practices**: Check for anti-patterns and performance issues

## Schema Design Checklist

### Tables
- [ ] Use UUID for primary keys: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- [ ] Add timestamps: `created_at TIMESTAMPTZ DEFAULT NOW()`, `updated_at TIMESTAMPTZ`
- [ ] Use appropriate data types (TEXT, INTEGER, JSONB, UUID, etc.)
- [ ] Add NOT NULL constraints for required fields
- [ ] Use UNIQUE constraints for unique fields (email, username, etc.)

### Relationships
- [ ] Define foreign keys with ON DELETE CASCADE/SET NULL as appropriate
- [ ] Use junction tables for many-to-many relationships
- [ ] Name foreign key columns consistently (e.g., `user_id`, `project_id`)
- [ ] Add indexes on foreign key columns

### Security
- [ ] Enable Row Level Security: `ALTER TABLE tablename ENABLE ROW LEVEL SECURITY;`
- [ ] Create RLS policies for SELECT, INSERT, UPDATE, DELETE
- [ ] Use `auth.uid()` for user-based data isolation
- [ ] Protect sensitive data with appropriate policies

### Performance
- [ ] Add indexes for frequently queried columns
- [ ] Use partial indexes where appropriate
- [ ] Consider JSONB for flexible schema fields
- [ ] Plan for query optimization (avoid N+1 queries)

## Example Schema Output

```sql
-- Users table (integrates with Supabase Auth)
CREATE TABLE users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projects table
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT CHECK (status IN ('active', 'archived', 'deleted')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status) WHERE status != 'deleted';

-- RLS Policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own data" ON users
  FOR SELECT USING (auth.uid() = id);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own projects" ON projects
  FOR ALL USING (auth.uid() = user_id);
```

## Environment Variables to Document

Always document these required environment variables:

```bash
# Supabase Configuration (from Supabase Dashboard > Settings > API)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... # Server-side only, NEVER expose to client

# Supabase Database Direct Connection (for migrations, optional)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```

## Integration with Architecture Documents

When creating Architecture or Technical Documents that require a database:

1. Add a **Database Schema** section with full SQL definitions
2. Include an **Environment Variables** section with Supabase configuration
3. Document RLS policies and security considerations
4. Specify migration files location (e.g., `supabase/migrations/`)
5. Reference database relationships in the architecture diagrams

## Common Patterns

### Multi-tenant with RLS
```sql
-- Each user sees only their own data
CREATE POLICY "Users can view own records" ON tablename
  FOR SELECT USING (auth.uid() = user_id);
```

### Public read, authenticated write
```sql
-- Anyone can read, only authenticated users can write
CREATE POLICY "Public read access" ON tablename
  FOR SELECT USING (true);
CREATE POLICY "Authenticated write access" ON tablename
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');
```

### Admin-only access
```sql
-- Only users with admin role can access
CREATE POLICY "Admin only" ON tablename
  USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  );
```

## References

- See `references/supabase-best-practices.md` for Supabase-specific patterns
- See `references/postgresql-data-types.md` for PostgreSQL data type reference
- See `scripts/validate_schema.py` for automated schema validation

## Anti-Patterns to Avoid

- ❌ Using INTEGER for primary keys (use UUID instead)
- ❌ Storing sensitive data without encryption
- ❌ Missing indexes on foreign keys
- ❌ No RLS policies (data accessible to everyone)
- ❌ Hardcoding user IDs instead of using `auth.uid()`
- ❌ Using SELECT * in production queries
- ❌ No timestamps for audit trails
- ❌ Overly normalized schemas (too many joins)
- ❌ JSONB abuse (putting relational data in JSONB)
