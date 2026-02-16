# Supabase Best Practices

Comprehensive guide for designing database schemas with Supabase PostgreSQL.

## Table of Contents
1. [Primary Keys](#primary-keys)
2. [Foreign Keys](#foreign-keys)
3. [Timestamps](#timestamps)
4. [Row Level Security (RLS)](#row-level-security)
5. [Indexes](#indexes)
6. [Data Types](#data-types)
7. [Supabase Auth Integration](#supabase-auth-integration)

---

## Primary Keys

### ✅ Best Practice: Use UUID for Primary Keys

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- other columns
);
```

**Why UUID over SERIAL/INT?**
- ✅ Globally unique (safe for distributed systems)
- ✅ No enumeration attacks (can't guess next ID)
- ✅ Better for public-facing APIs
- ✅ Supabase Auth uses UUIDs

**When to use SERIAL/INT:**
- Internal lookup tables with small datasets
- When human-readable IDs are important
- Legacy system integration

---

## Foreign Keys

### ✅ Use Proper ON DELETE Behavior

```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  -- other columns
);
```

**ON DELETE CASCADE**
- Use when child records should be deleted with parent
- Example: User deleted → Delete their projects

**ON DELETE SET NULL**
- Use when child record should persist but lose reference
- Example: User deleted → Keep their public posts but set author_id to NULL

**ON DELETE RESTRICT** (default)
- Prevents deleting parent if children exist
- Example: Can't delete category if products still use it

### ✅ Always Index Foreign Keys

```sql
CREATE INDEX idx_projects_user_id ON projects(user_id);
```

PostgreSQL doesn't auto-index foreign keys - you must create them manually for performance.

---

## Timestamps

### ✅ Always Include created_at and updated_at

```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tasks_updated_at
  BEFORE UPDATE ON tasks
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

**Why TIMESTAMPTZ (not TIMESTAMP)?**
- ✅ Stores with timezone information
- ✅ Converts to user's timezone automatically
- ✅ Handles daylight saving time correctly

---

## Row Level Security (RLS)

### ✅ Enable RLS on All User Data Tables

```sql
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
```

### Common RLS Patterns

#### 1. Users Can CRUD Own Data
```sql
CREATE POLICY "Users can CRUD own tasks" ON tasks
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

#### 2. Public Read, Authenticated Write
```sql
-- Anyone can read
CREATE POLICY "Public read access" ON posts
  FOR SELECT
  USING (true);

-- Only authenticated users can insert
CREATE POLICY "Authenticated users can insert" ON posts
  FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

-- Only owners can update/delete
CREATE POLICY "Users can update own posts" ON posts
  FOR UPDATE
  USING (auth.uid() = user_id);
```

#### 3. Role-Based Access
```sql
-- Check if user has admin role
CREATE POLICY "Admin full access" ON sensitive_data
  USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  );
```

#### 4. Shared/Collaborative Access
```sql
-- Users can see projects they're members of
CREATE POLICY "Members can view projects" ON projects
  USING (
    EXISTS (
      SELECT 1 FROM project_members
      WHERE project_id = projects.id
      AND user_id = auth.uid()
    )
  );
```

### ✅ Test RLS Policies

```sql
-- Test as specific user
SET request.jwt.claims.sub = 'user-uuid-here';

-- Run queries to verify RLS works
SELECT * FROM tasks;  -- Should only see user's tasks

-- Reset
RESET request.jwt.claims.sub;
```

---

## Indexes

### ✅ Index Foreign Keys
```sql
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
```

### ✅ Index Frequently Queried Columns
```sql
-- If you often filter by status
CREATE INDEX idx_tasks_status ON tasks(status);

-- If you often filter by email
CREATE INDEX idx_users_email ON users(email);
```

### ✅ Use Partial Indexes for Specific Queries
```sql
-- Only index active tasks (ignore completed)
CREATE INDEX idx_active_tasks
  ON tasks(user_id, created_at)
  WHERE status != 'completed';

-- Only index published posts
CREATE INDEX idx_published_posts
  ON posts(created_at DESC)
  WHERE published = true;
```

### ✅ Compound Indexes for Multi-Column Queries
```sql
-- If you often query: WHERE user_id = X ORDER BY created_at DESC
CREATE INDEX idx_tasks_user_created
  ON tasks(user_id, created_at DESC);
```

---

## Data Types

### Text vs VARCHAR
```sql
-- ✅ Use TEXT (not VARCHAR)
CREATE TABLE users (
  name TEXT NOT NULL,
  bio TEXT
);
```

**Why TEXT over VARCHAR?**
- No performance difference in PostgreSQL
- No arbitrary length limits
- Simpler schema

**When to use VARCHAR(n):**
- When you need to enforce exact length (e.g., postal codes)
- Legacy system compatibility

### JSON vs JSONB
```sql
-- ✅ Use JSONB (not JSON)
CREATE TABLE products (
  id UUID PRIMARY KEY,
  metadata JSONB,
  settings JSONB DEFAULT '{}'::jsonb
);

-- Can index JSONB fields
CREATE INDEX idx_products_metadata ON products USING GIN (metadata);

-- Can query JSONB efficiently
SELECT * FROM products WHERE metadata->>'category' = 'electronics';
```

**Why JSONB over JSON?**
- ✅ Binary format (faster queries)
- ✅ Can create indexes
- ✅ Supports operators like @>, ?, ?&, ?|

### Enums vs TEXT with CHECK

#### ❌ Avoid PostgreSQL ENUMs
```sql
-- Don't do this (hard to modify)
CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done');
```

#### ✅ Use TEXT with CHECK Constraint
```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY,
  status TEXT CHECK (status IN ('todo', 'in_progress', 'done')) DEFAULT 'todo'
);
```

**Why?**
- ✅ Easier to add new values (just ALTER TABLE)
- ✅ No type casting needed
- ✅ Works better with ORMs

---

## Supabase Auth Integration

### ✅ Extend Supabase Auth Users Table

```sql
-- Don't create a separate users table
-- Instead, extend auth.users with a public profile table

CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  bio TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS policies
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Anyone can view profiles
CREATE POLICY "Public profiles are viewable" ON profiles
  FOR SELECT USING (true);

-- Users can update own profile
CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE
  USING (auth.uid() = id);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

---

## Common Anti-Patterns to Avoid

### ❌ DON'T: Use INTEGER for Primary Keys
```sql
-- Avoid this
CREATE TABLE users (
  id SERIAL PRIMARY KEY  -- ❌
);

-- Use this instead
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid()  -- ✅
);
```

### ❌ DON'T: Forget Indexes on Foreign Keys
```sql
-- Slow queries without index
CREATE TABLE tasks (
  project_id UUID REFERENCES projects(id)  -- ❌ No index
);

-- Add index
CREATE INDEX idx_tasks_project_id ON tasks(project_id);  -- ✅
```

### ❌ DON'T: Disable RLS for User Data
```sql
-- Never do this for user data
ALTER TABLE user_tasks DISABLE ROW LEVEL SECURITY;  -- ❌ Security risk!
```

### ❌ DON'T: Use SELECT * in Production
```sql
-- Inefficient
SELECT * FROM users;  -- ❌

-- Specify columns
SELECT id, email, full_name FROM users;  -- ✅
```

### ❌ DON'T: Store Unencrypted Sensitive Data
```sql
-- Never store these without encryption
CREATE TABLE users (
  password TEXT,  -- ❌ Use auth.users instead
  credit_card TEXT,  -- ❌ Use vault or external service
  ssn TEXT  -- ❌ Use vault or external service
);
```

---

## Migration Best Practices

### ✅ Make Migrations Idempotent
```sql
-- Can run multiple times safely
CREATE TABLE IF NOT EXISTS tasks (...);

-- Or check for existence first
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'tasks') THEN
    CREATE TABLE tasks (...);
  END IF;
END $$;
```

### ✅ Use Transactions
```sql
BEGIN;

CREATE TABLE projects (...);
CREATE INDEX idx_projects_user_id ON projects(user_id);
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

COMMIT;
```

### ✅ Test Rollback
```sql
-- Always have a rollback plan
BEGIN;

-- Migration
ALTER TABLE tasks ADD COLUMN priority INTEGER;

-- If something goes wrong
ROLLBACK;

-- If successful
COMMIT;
```

---

## Checklist for Every Table

- [ ] UUID primary key with gen_random_uuid()
- [ ] created_at TIMESTAMPTZ DEFAULT NOW()
- [ ] updated_at TIMESTAMPTZ DEFAULT NOW() with trigger
- [ ] Foreign keys with appropriate ON DELETE
- [ ] Indexes on all foreign key columns
- [ ] Indexes on frequently queried columns
- [ ] NOT NULL constraints on required fields
- [ ] CHECK constraints for value validation
- [ ] RLS enabled if table contains user data
- [ ] RLS policies for SELECT, INSERT, UPDATE, DELETE
- [ ] Comments explaining complex logic
