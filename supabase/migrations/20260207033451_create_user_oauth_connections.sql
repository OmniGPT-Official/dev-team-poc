-- Create user_oauth_connections table for per-user OAuth token storage
create table public.user_oauth_connections (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    provider text not null,                    -- 'google_sheets', 'google_gmail', 'slack', 'notion'
    provider_account_id text not null,         -- unique id from provider (e.g. email)
    account_label text,                        -- user-friendly name
    access_token text not null,
    refresh_token text,
    token_uri text,
    scopes text[] default '{}',
    expires_at timestamptz,
    metadata jsonb default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_user_provider_account unique (user_id, provider, provider_account_id)
);

-- Index for fast lookups by user + provider
create index idx_user_oauth_connections_user_provider
    on public.user_oauth_connections (user_id, provider);

-- Auto-update updated_at on row changes
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_user_oauth_connections_updated_at
    before update on public.user_oauth_connections
    for each row
    execute function public.update_updated_at_column();

-- RLS: users can only access their own rows
alter table public.user_oauth_connections enable row level security;

create policy "Users can view their own connections"
    on public.user_oauth_connections for select
    using (auth.uid() = user_id);

create policy "Users can insert their own connections"
    on public.user_oauth_connections for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own connections"
    on public.user_oauth_connections for update
    using (auth.uid() = user_id);

create policy "Users can delete their own connections"
    on public.user_oauth_connections for delete
    using (auth.uid() = user_id);

-- Grant access to authenticated users (RLS enforces row-level access)
grant select, insert, update, delete on public.user_oauth_connections to authenticated;
