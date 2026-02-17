-- Add 'instagram' to oauth_provider enum
ALTER TYPE public.oauth_provider ADD VALUE IF NOT EXISTS 'instagram';
