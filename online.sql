-- Pitch Royale: online spelen (accounts, vrienden, onderlinge uitslagen)
-- Plak dit in Supabase > SQL Editor en klik op Run. Je mag het vaker runnen.
-- Zie ONLINE.md voor de rest van de instellingen.

-- ---------- spelers ----------
-- Elke account heeft een gebruikersnaam: 3 tot 16 tekens, kleine letters,
-- cijfers, punt of liggend streepje. De game maakt er zelf een rij van
-- (de trigger hieronder) zodra iemand een account maakt.
create table if not exists public.profiles (
    id          uuid primary key references auth.users (id) on delete cascade,
    username    text not null unique check (username ~ '^[a-z0-9_.]{3,16}$'),
    created_at  timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- Ingelogde spelers mogen namen opzoeken (om een vriend toe te voegen).
drop policy if exists "players read profiles" on public.profiles;
create policy "players read profiles" on public.profiles
    for select to authenticated
    using (true);

grant select on public.profiles to authenticated;

create or replace function public.pr_new_player()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (id, username)
    values (new.id, lower(new.raw_user_meta_data ->> 'username'));
    return new;
end;
$$;

drop trigger if exists pr_new_player on auth.users;
create trigger pr_new_player
    after insert on auth.users
    for each row
    when (new.raw_user_meta_data ->> 'username' is not null)
    execute function public.pr_new_player();

-- ---------- vrienden ----------
-- Een verzoek is 'pending' tot de ander het accepteert ('accepted').
-- Weigeren of een vriend weghalen wist de rij.
create table if not exists public.friendships (
    id          uuid primary key default gen_random_uuid(),
    requester   uuid not null references public.profiles (id) on delete cascade,
    addressee   uuid not null references public.profiles (id) on delete cascade,
    status      text not null default 'pending' check (status in ('pending', 'accepted')),
    created_at  timestamptz not null default now(),
    check (requester <> addressee)
);

-- tussen twee spelers maar één rij, welke kant het verzoek ook stuurde
create unique index if not exists friendships_pair
    on public.friendships (least(requester, addressee), greatest(requester, addressee));

alter table public.friendships enable row level security;

drop policy if exists "see own friendships" on public.friendships;
create policy "see own friendships" on public.friendships
    for select to authenticated
    using (auth.uid() in (requester, addressee));

drop policy if exists "send a request" on public.friendships;
create policy "send a request" on public.friendships
    for insert to authenticated
    with check (auth.uid() = requester and status = 'pending');

drop policy if exists "accept a request" on public.friendships;
create policy "accept a request" on public.friendships
    for update to authenticated
    using (auth.uid() = addressee)
    with check (auth.uid() = addressee and status = 'accepted');

drop policy if exists "remove a friendship" on public.friendships;
create policy "remove a friendship" on public.friendships
    for delete to authenticated
    using (auth.uid() in (requester, addressee));

grant select, insert, update, delete on public.friendships to authenticated;

-- ---------- uitslagen ----------
-- Na elke online wedstrijd schrijft de thuisspeler (rood) de uitslag weg.
-- Daaruit komt "Onderling" (gewonnen, gelijk, verloren) in de vriendenlijst.
create table if not exists public.matches (
    id          uuid primary key default gen_random_uuid(),
    played_at   timestamptz not null default now(),
    red         uuid not null references public.profiles (id) on delete cascade,
    blue        uuid not null references public.profiles (id) on delete cascade,
    score_red   smallint not null check (score_red between 0 and 99),
    score_blue  smallint not null check (score_blue between 0 and 99),
    check (red <> blue)
);

create index if not exists matches_red  on public.matches (red);
create index if not exists matches_blue on public.matches (blue);

alter table public.matches enable row level security;

drop policy if exists "see own matches" on public.matches;
create policy "see own matches" on public.matches
    for select to authenticated
    using (auth.uid() in (red, blue));

drop policy if exists "home side records the result" on public.matches;
create policy "home side records the result" on public.matches
    for insert to authenticated
    with check (auth.uid() = red);

grant select, insert on public.matches to authenticated;
