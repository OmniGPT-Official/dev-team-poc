-- Migration: Create projects table for storing user project metadata
-- Description: Stores comprehensive project information including docs, repos, deployments
-- Date: 2025-02-13

-- ============================================================================
-- PROJECTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS projects (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,

    -- Project Info
    project_name TEXT NOT NULL,
    project_description TEXT,
    project_type TEXT NOT NULL CHECK (project_type IN ('new', 'existing')),

    -- Documents & URLs
    prd_doc_url TEXT,                    -- PRD or Feature Spec Google Docs URL
    architecture_doc_url TEXT,           -- Architecture Google Docs URL
    github_repo_url TEXT,                -- Full GitHub repo URL
    github_repo_name TEXT,               -- Just the repo name (e.g., "my-app")
    github_owner TEXT,                   -- GitHub username/org
    vercel_deployment_url TEXT,          -- Vercel deployment URL
    vercel_project_id TEXT,              -- Vercel project ID

    -- Knowledge Base Integration
    knowledge_base_id TEXT,              -- Reference to knowledge base entry

    -- Status & Metadata
    status TEXT DEFAULT 'planning' CHECK (status IN ('planning', 'in_development', 'deployed', 'archived')),
    tags TEXT[],                         -- Array of tags for categorization
    tech_stack JSONB DEFAULT '{}',       -- Technologies used (e.g., {"frontend": "React", "backend": "FastAPI"})

    -- Workflow Tracking
    prd_created_at TIMESTAMPTZ,
    architecture_created_at TIMESTAMPTZ,
    repo_created_at TIMESTAMPTZ,
    deployed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Index for user queries (fast lookup of user's projects)
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);

-- Index for project name search
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(project_name);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

-- Full-text search on project name and description
CREATE INDEX IF NOT EXISTS idx_projects_search ON projects
    USING gin(to_tsvector('english', project_name || ' ' || COALESCE(project_description, '')));

-- Index for knowledge base lookups
CREATE INDEX IF NOT EXISTS idx_projects_knowledge_base_id ON projects(knowledge_base_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_projects_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_projects_updated_at();

-- ============================================================================
-- ROW LEVEL SECURITY (Optional - uncomment if using RLS)
-- ============================================================================

-- Enable RLS
-- ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own projects
-- CREATE POLICY projects_user_isolation ON projects
--     FOR ALL
--     USING (user_id = auth.uid());

-- ============================================================================
-- SAMPLE QUERIES (for reference)
-- ============================================================================

-- Find all projects for a user:
-- SELECT * FROM projects WHERE user_id = 'user-uuid' ORDER BY created_at DESC;

-- Find projects by name (fuzzy search):
-- SELECT * FROM projects
-- WHERE to_tsvector('english', project_name || ' ' || COALESCE(project_description, ''))
--       @@ plainto_tsquery('english', 'e-commerce');

-- Get project details with status:
-- SELECT project_name, status, github_repo_url, vercel_deployment_url
-- FROM projects
-- WHERE user_id = 'user-uuid' AND status = 'deployed';

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE projects IS 'Stores comprehensive metadata for all user projects including docs, repos, and deployments';
COMMENT ON COLUMN projects.id IS 'Unique project identifier';
COMMENT ON COLUMN projects.user_id IS 'Owner of the project';
COMMENT ON COLUMN projects.project_name IS 'Human-readable project name';
COMMENT ON COLUMN projects.project_description IS 'Detailed description of what the project does';
COMMENT ON COLUMN projects.project_type IS 'Whether this is a new project or existing product enhancement';
COMMENT ON COLUMN projects.prd_doc_url IS 'Google Docs URL for PRD or Feature Spec';
COMMENT ON COLUMN projects.architecture_doc_url IS 'Google Docs URL for Architecture document';
COMMENT ON COLUMN projects.github_repo_url IS 'Full GitHub repository URL';
COMMENT ON COLUMN projects.vercel_deployment_url IS 'Live deployment URL on Vercel';
COMMENT ON COLUMN projects.knowledge_base_id IS 'Reference to knowledge base entry for RAG search';
COMMENT ON COLUMN projects.status IS 'Current project status in the development lifecycle';
COMMENT ON COLUMN projects.tech_stack IS 'JSON object storing technologies used in the project';
