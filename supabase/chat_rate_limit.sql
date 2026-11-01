-- Apply once before enabling production chat. No messages, addresses or raw IPs are stored.
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
create table private.chat_quota (
  bucket text not null, identity text not null, period_start timestamptz not null,
  used integer not null, primary key (bucket, identity, period_start)
);
alter table private.chat_quota enable row level security;
revoke all on private.chat_quota from public, anon, authenticated;
-- Explicitly privileged only for atomic private counters; browser roles cannot execute it.
create function public.take_chat_quota(p_identity text) returns boolean
language plpgsql security definer set search_path = '' as $$
declare
  minute_start timestamptz := date_trunc('minute', now());
  day_start timestamptz := date_trunc('day', now() at time zone 'UTC') at time zone 'UTC';
  minute_count integer; day_count integer; global_count integer;
begin
  if p_identity !~ '^[0-9a-f]{64}$' then raise exception 'Invalid identity'; end if;
  delete from private.chat_quota where period_start < now() - interval '2 days';
  -- All requests acquire counters in the same order. Atomic upserts prevent concurrent bypass.
  insert into private.chat_quota values ('global', 'all', day_start, 1)
    on conflict (bucket,identity,period_start) do update set used = private.chat_quota.used + 1 returning used into global_count;
  insert into private.chat_quota values ('day', p_identity, day_start, 1)
    on conflict (bucket,identity,period_start) do update set used = private.chat_quota.used + 1 returning used into day_count;
  insert into private.chat_quota values ('minute', p_identity, minute_start, 1)
    on conflict (bucket,identity,period_start) do update set used = private.chat_quota.used + 1 returning used into minute_count;
  return minute_count <= 6 and day_count <= 40 and global_count <= 500;
end;
$$;
revoke all on function public.take_chat_quota(text) from public, anon, authenticated;
grant execute on function public.take_chat_quota(text) to service_role;
