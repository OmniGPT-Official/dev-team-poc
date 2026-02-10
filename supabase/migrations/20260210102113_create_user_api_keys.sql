create table public.user_api_keys (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    provider text not null,          -- 'elevenlabs', 'vercel', 'supabase', etc.
    api_key text not null,
    label text,                      -- optional friendly name
    metadata jsonb default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_user_api_keys_user_provider unique (user_id, provider)
);

-- Index for fast lookups
create index idx_user_api_keys_user_provider
    on public.user_api_keys (user_id, provider);

-- Reuse existing updated_at trigger function from OAuth migration
create trigger trg_user_api_keys_updated_at
    before update on public.user_api_keys
    for each row
    execute function public.update_updated_at_column();

-- RLS: users can only access their own rows
alter table public.user_api_keys enable row level security;

create policy "Users can view their own api keys"
    on public.user_api_keys for select using (auth.uid() = user_id);
create policy "Users can insert their own api keys"
    on public.user_api_keys for insert with check (auth.uid() = user_id);
create policy "Users can update their own api keys"
    on public.user_api_keys for update using (auth.uid() = user_id);
create policy "Users can delete their own api keys"
    on public.user_api_keys for delete using (auth.uid() = user_id);

grant select, insert, update, delete on public.user_api_keys to authenticated;
