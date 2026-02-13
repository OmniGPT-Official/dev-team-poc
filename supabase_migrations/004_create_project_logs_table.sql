-- Migration 004: Project Development Logs Table
-- Tracks supervisor validations, document checks, and workflow progress

CREATE TABLE IF NOT EXISTS project_development_logs (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Log metadata
    log_type VARCHAR(50) NOT NULL, -- 'validation', 'error', 'warning', 'info', 'milestone'
    phase VARCHAR(50) NOT NULL, -- 'prd_creation', 'architecture_creation', 'repo_creation', 'deployment'

    -- Validation results
    is_valid BOOLEAN DEFAULT NULL, -- NULL for non-validation logs
    validation_target VARCHAR(100), -- 'prd_document', 'architecture_document', 'github_repo', etc.

    -- Log content
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}', -- Additional structured data (e.g., document preview, error details)

    -- Context
    created_by VARCHAR(100) DEFAULT 'supervisor', -- 'supervisor', 'system', 'workflow'
    severity VARCHAR(20) DEFAULT 'info', -- 'critical', 'error', 'warning', 'info', 'success'

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_project_logs_project_id ON project_development_logs(project_id);
CREATE INDEX idx_project_logs_type ON project_development_logs(log_type);
CREATE INDEX idx_project_logs_phase ON project_development_logs(phase);
CREATE INDEX idx_project_logs_created_at ON project_development_logs(created_at DESC);

-- Composite index for common queries
CREATE INDEX idx_project_logs_project_phase ON project_development_logs(project_id, phase, created_at DESC);

COMMENT ON TABLE project_development_logs IS 'Tracks supervisor validations, errors, and workflow progress for each project';
COMMENT ON COLUMN project_development_logs.log_type IS 'Type of log entry: validation, error, warning, info, milestone';
COMMENT ON COLUMN project_development_logs.phase IS 'Which workflow phase this log belongs to';
COMMENT ON COLUMN project_development_logs.is_valid IS 'For validation logs: true if validation passed, false if failed, null for non-validation logs';
COMMENT ON COLUMN project_development_logs.details IS 'Additional structured data like document previews, error stack traces, etc.';
