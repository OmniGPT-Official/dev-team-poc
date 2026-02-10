-- Create enum type for OAuth providers
CREATE TYPE public.oauth_provider AS ENUM (
    'google_sheets',
    'google_gmail',
    'slack',
    'notion'
);

-- Convert provider column from text to enum
ALTER TABLE public.user_oauth_connections
    ALTER COLUMN provider TYPE public.oauth_provider
    USING provider::public.oauth_provider;
