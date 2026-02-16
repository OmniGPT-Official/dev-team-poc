---
name: code-review
description: Comprehensive code review including database schema validation, security checks, and best practices enforcement
license: MIT
metadata:
  version: "1.0.0"
  author: agent-os
  tags: ["code-review", "quality", "security", "database"]
---

# Code Review Skill

Use this skill when reviewing code for quality, security, database integrity, and best practices.

## When to Use

- User asks for code review or feedback
- Software Engineer completes implementation
- Before deploying to production
- When validating pull requests
- Reviewing existing codebase for improvements

## Process

1. **Read Repository Files**: List all files and read key code files
2. **Review Frontend Code**: Check HTML, CSS, JavaScript/TypeScript
3. **Review Backend Code**: Check API routes, server-side logic, auth
4. **Review Database Code**: Validate schema, migrations, queries, RLS policies (NEW)
5. **Check Environment Variables**: Verify all required vars are documented (NEW)
6. **Security Review**: Check for vulnerabilities, exposed secrets, SQL injection
7. **Performance Review**: Identify bottlenecks, inefficient queries
8. **Best Practices**: Verify code follows conventions and standards
9. **Provide Feedback**: Clear, actionable recommendations

## Review Categories

### 1. Code Quality
- [ ] Code is readable and self-documenting
- [ ] Functions are small and focused (single responsibility)
- [ ] Variable and function names are descriptive
- [ ] No commented-out code or unused imports
- [ ] Consistent code style and formatting
- [ ] Proper error handling with try/catch
- [ ] No hardcoded values (use constants or env vars)

### 2. Security Review
- [ ] No API keys or secrets hardcoded in code
- [ ] All environment variables use proper prefixes (VITE_, NEXT_PUBLIC_)
- [ ] User input is validated and sanitized
- [ ] SQL queries use parameterized statements (no string concatenation)
- [ ] Authentication is properly implemented
- [ ] Authorization checks are in place for protected routes
- [ ] CORS is properly configured (not overly permissive)
- [ ] XSS vulnerabilities are prevented
- [ ] CSRF protection is implemented (for forms)

### 3. **Database Review** (NEW REQUIREMENT)

#### Schema Validation
- [ ] Tables use UUID for primary keys
- [ ] All tables have `created_at` and `updated_at` timestamps
- [ ] Foreign keys are properly defined with ON DELETE CASCADE/SET NULL
- [ ] Appropriate data types are used (TEXT, INTEGER, JSONB, UUID, etc.)
- [ ] NOT NULL constraints are added for required fields
- [ ] UNIQUE constraints are added for unique fields
- [ ] CHECK constraints are used for value validation

#### Indexes and Performance
- [ ] Indexes exist on foreign key columns
- [ ] Indexes exist on frequently queried columns
- [ ] No missing indexes that cause slow queries
- [ ] Partial indexes are used where appropriate
- [ ] No unnecessary indexes (index bloat)

#### Row Level Security (RLS)
- [ ] RLS is enabled on all user data tables
- [ ] RLS policies exist for SELECT, INSERT, UPDATE, DELETE
- [ ] Policies use `auth.uid()` for user-based isolation
- [ ] No data leakage between users
- [ ] Admin-only tables have appropriate policies
- [ ] Public read policies are intentional (not accidental)

#### Query Quality
- [ ] Queries use proper JOINs (avoid N+1 queries)
- [ ] SELECT statements specify columns (avoid SELECT *)
- [ ] Queries are parameterized (prevent SQL injection)
- [ ] Transactions are used for multi-step operations
- [ ] Query results are properly typed

#### Migration Files
- [ ] Migrations are sequential and numbered
- [ ] Migrations are idempotent (can run multiple times safely)
- [ ] Destructive migrations have rollback steps
- [ ] Migrations include comments explaining changes
- [ ] Migration file names follow convention: `YYYYMMDD_description.sql`

### 4. **Environment Variables** (NEW REQUIREMENT)
- [ ] All required env vars are documented in `.env.example`
- [ ] Sensitive vars (API keys, DB passwords) are not in the repo
- [ ] Client-side vars use proper prefixes (NEXT_PUBLIC_, VITE_)
- [ ] Server-side vars are clearly marked as secret
- [ ] Instructions for obtaining each var are included
- [ ] Vercel env vars match `.env.example` (if deploying to Vercel)

### 5. File Structure & Organization
- [ ] Files are organized in logical directories
- [ ] Related files are grouped together
- [ ] No duplicate code across files
- [ ] Shared utilities are extracted to reusable modules
- [ ] Component hierarchy is clear (for React/Next.js)

### 6. Frontend Code Review

#### HTML
- [ ] Semantic HTML elements are used
- [ ] All images have alt attributes
- [ ] Links have descriptive text (not "click here")
- [ ] Forms have proper labels and validation
- [ ] No broken file references (CSS, JS, images)
- [ ] Relative paths are correct for subdirectories

#### CSS
- [ ] CSS is organized and maintainable
- [ ] No unused CSS rules
- [ ] Responsive design is implemented
- [ ] CSS variables are used for theming
- [ ] No inline styles (unless necessary)
- [ ] Cross-browser compatibility is considered

#### JavaScript/TypeScript
- [ ] Modern ES6+ syntax is used
- [ ] No global variables pollution
- [ ] Event listeners are properly removed when needed
- [ ] Async/await is used for promises
- [ ] Type safety is enforced (for TypeScript)
- [ ] No console.log statements in production code

### 7. File Linking & Cross-Reference Checks (CRITICAL)

**Every code review MUST verify:**
- [ ] HTML → CSS linking: `<link rel="stylesheet" href="...">` points to existing CSS file
- [ ] HTML → JS linking: `<script src="...">` points to existing JS file
- [ ] Relative paths are correct for directory depth (e.g., `css/styles.css` not `styles.css`)
- [ ] CSS `url()` references point to valid images/fonts
- [ ] Navigation links (`<a href="...">`) use correct relative paths
- [ ] Image `src` attributes point to real images or valid URLs
- [ ] No broken references to non-existent files
- [ ] File names in repo match references exactly (case-sensitive)

**If ANY file linking issue is found, mark review as CHANGES_REQUESTED.**

### 8. Performance Review
- [ ] Images are optimized and properly sized
- [ ] No unnecessary API calls or database queries
- [ ] Code splitting is used (for large apps)
- [ ] Lazy loading is implemented for heavy components
- [ ] Database queries use indexes
- [ ] No N+1 query problems

## Review Output Format

### Approved Review
```markdown
## ✅ CODE REVIEW: APPROVED

**Summary:** All checks passed. Code is ready for deployment.

### Highlights
- Clean, readable code with good naming conventions
- Proper error handling throughout
- Database schema follows best practices with RLS enabled
- All environment variables documented
- No security vulnerabilities found

### Minor Suggestions (Optional)
- Consider adding unit tests for complex functions
- Could extract repeated logic into a utility function
```

### Changes Requested Review
```markdown
## ⚠️ CODE REVIEW: CHANGES REQUESTED

**Summary:** Found [X] issues that must be addressed before deployment.

### Critical Issues
1. **Security:** API key exposed in `config.js` line 12
   - Fix: Move to environment variable SUPABASE_SERVICE_ROLE_KEY

2. **Database:** Missing RLS policy on `tasks` table
   - Fix: Add policy to prevent users from accessing other users' tasks

3. **Broken Link:** `index.html` references `css/style.css` but file is `css/styles.css`
   - Fix: Rename file or update reference

### Warnings
1. **Performance:** N+1 query in `getUserPosts` function
   - Recommendation: Use JOIN to fetch posts with user data in single query

### Recommendations (Optional)
- Consider using TypeScript for better type safety
- Add loading states for async operations
```

## Database Review Examples

### ❌ Bad: Missing RLS
```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY,
  user_id UUID,
  title TEXT
);
-- No RLS! Anyone can read all tasks
```

### ✅ Good: Proper RLS
```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own tasks" ON tasks
  FOR ALL USING (auth.uid() = user_id);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
```

### ❌ Bad: SQL Injection Risk
```javascript
// NEVER do this
const query = `SELECT * FROM users WHERE email = '${userEmail}'`;
```

### ✅ Good: Parameterized Query
```javascript
// Use parameterized queries
const { data } = await supabase
  .from('users')
  .select('*')
  .eq('email', userEmail);
```

## Integration with Workflow

### In Software Development Workflow
After Software Engineer implements code:
1. Lead Engineer calls this skill to review the code
2. Skill checks all categories including database
3. Returns APPROVED or CHANGES_REQUESTED
4. If changes requested, Software Engineer fixes issues
5. Loop repeats until approved

### Database-Specific Review Steps
When reviewing a project with database:
1. **Read migration files** in `supabase/migrations/` or `prisma/migrations/`
2. **Check schema** against architecture document requirements
3. **Verify RLS policies** are enabled and correctly configured
4. **Test queries** for SQL injection vulnerabilities
5. **Validate indexes** on foreign keys and frequently queried columns
6. **Check environment variables** for database connection strings

## Review Severity Levels

### 🔴 Critical (Must Fix Before Deploy)
- Security vulnerabilities (exposed secrets, SQL injection)
- Missing RLS policies on user data
- Broken file references
- Missing required environment variables
- Data loss risks (missing ON DELETE CASCADE)

### 🟡 Warning (Should Fix Soon)
- Performance issues (missing indexes, N+1 queries)
- Code quality issues (duplicate code, poor naming)
- Missing error handling
- Incomplete validation

### 🟢 Recommendation (Nice to Have)
- Code style improvements
- Additional tests
- Documentation enhancements
- Refactoring opportunities

## Checklist Before Approving Code

- [ ] All security checks passed
- [ ] Database schema validated (if applicable)
- [ ] Environment variables documented
- [ ] No broken file references
- [ ] Code quality meets standards
- [ ] Performance is acceptable
- [ ] Error handling is comprehensive
- [ ] Best practices are followed
- [ ] No hardcoded secrets or keys

## References

- See `references/security-checklist.md` for security review guidelines
- See `references/database-review-guide.md` for database-specific checks
- See `../database-schema-design/SKILL.md` for schema best practices
