-- Public environmental data only. No personal locations or public writes.
create table public.air_locations (
 station_id text primary key, name text not null,
 latitude double precision not null check (latitude between -90 and 90),
 longitude double precision not null check (longitude between -180 and 180)
);
create table public.daily_air (
 station_id text not null references public.air_locations, date date not null,
 pm25 real not null check (pm25 >= 0), readings smallint not null check (readings >= 16),
 source text not null, primary key (station_id, date)
);
create table public.comparison_snapshots (
 station_id text not null references public.air_locations, year smallint not null,
 phases jsonb not null, complete boolean not null, model_version text not null,
 is_live boolean not null default false check (is_live = false),
 primary key (station_id, year)
);
alter table public.air_locations enable row level security;
alter table public.daily_air enable row level security;
alter table public.comparison_snapshots enable row level security;
revoke all on public.air_locations, public.daily_air, public.comparison_snapshots from anon, authenticated;
grant select on public.air_locations, public.daily_air, public.comparison_snapshots to anon, authenticated;
create policy public_read on public.air_locations for select to anon, authenticated using (true);
create policy public_read on public.daily_air for select to anon, authenticated using (true);
create policy public_read on public.comparison_snapshots for select to anon, authenticated using (true);
