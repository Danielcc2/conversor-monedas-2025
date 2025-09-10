-- Perfiles y preferencias para Conversor de Divisas (Blog Viajes 2025)

-- Tabla de perfiles vinculada a auth.users
create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  name text,
  created_at timestamptz default now()
);

-- Trigger para crear perfil al registrarse
create or replace function public.handle_new_user()
returns trigger language plpgsql as $$
begin
  insert into public.profiles (id, name)
  values (new.id, coalesce(new.raw_user_meta_data->>'name', ''))
  on conflict (id) do nothing;
  return new;
end; $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- Preferencias de divisas por usuario
create table if not exists public.preferences (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  default_from text not null,
  default_to text not null,
  updated_at timestamptz default now()
);

-- Activar RLS
alter table public.profiles enable row level security;
alter table public.preferences enable row level security;

-- Policies para que cada usuario solo vea/edite lo suyo
do $$ begin
  create policy profiles_select_own on public.profiles for select using (id = auth.uid());
exception when duplicate_object then null; end $$;

do $$ begin
  create policy profiles_update_own on public.profiles for update using (id = auth.uid());
exception when duplicate_object then null; end $$;

do $$ begin
  create policy prefs_select_own on public.preferences for select using (user_id = auth.uid());
exception when duplicate_object then null; end $$;

do $$ begin
  create policy prefs_upsert_own on public.preferences for insert with check (user_id = auth.uid());
exception when duplicate_object then null; end $$;

do $$ begin
  create policy prefs_update_own on public.preferences for update using (user_id = auth.uid());
exception when duplicate_object then null; end $$;

