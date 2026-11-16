-- Pitch Royale: statistieken
-- Plak dit in Supabase > SQL Editor en klik op Run.
-- Vervang eerst JOUW-EMAIL@voorbeeld.nl (onderaan) door het e-mailadres
-- waarmee je straks op stats.html inlogt.

create table if not exists public.events (
    id          uuid primary key default gen_random_uuid(),
    created_at  timestamptz not null default now(),
    visitor     text not null check (char_length(visitor) between 8 and 40),
    session     text not null check (char_length(session) between 8 and 40),
    type        text not null check (type in ('visit', 'time', 'match', 'wk_start')),
    device      text check (char_length(device) <= 20),
    os          text check (char_length(os) <= 20),
    browser     text check (char_length(browser) <= 30),
    screen      text check (char_length(screen) <= 20),
    lang        text check (char_length(lang) <= 16),
    referrer    text check (char_length(referrer) <= 100),
    data        jsonb not null default '{}'::jsonb check (pg_column_size(data) <= 4000)
);

create index if not exists events_created_at on public.events (created_at);

-- Row level security: zonder een regel hieronder mag niemand iets.
alter table public.events enable row level security;

-- De game (iedereen, zonder login) mag alleen een regel TOEVOEGEN.
-- Lezen, wijzigen of wissen kan zo niet.
drop policy if exists "game adds events" on public.events;
create policy "game adds events" on public.events
    for insert to anon, authenticated
    with check (true);

-- Alleen jij mag LEZEN, ingelogd met dit e-mailadres.
drop policy if exists "owner reads events" on public.events;
create policy "owner reads events" on public.events
    for select to authenticated
    using ((auth.jwt() ->> 'email') = 'JOUW-EMAIL@voorbeeld.nl');

grant insert on public.events to anon, authenticated;
grant select on public.events to authenticated;
