-- Nexo IA MVP: chat persistente, RAG vectorial y archivos originales.
-- Pegar una sola vez en Supabase SQL Editor. No contiene credenciales.

create schema if not exists extensions;
do $$
declare
    vector_schema text;
begin
    select n.nspname into vector_schema
    from pg_extension e
    join pg_namespace n on n.oid = e.extnamespace
    where e.extname = 'vector';

    if vector_schema is null then
        execute 'create extension vector with schema extensions';
    elsif vector_schema <> 'extensions' then
        execute 'alter extension vector set schema extensions';
    end if;
end $$;

create table if not exists public.chat_sessions (
    id text primary key check (char_length(id) between 1 and 64),
    created_at timestamptz not null default now()
);

create table if not exists public.conversation_turns (
    id bigint generated always as identity primary key,
    session_id text not null references public.chat_sessions(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null check (char_length(content) <= 12000),
    created_at timestamptz not null default now()
);

create index if not exists conversation_turns_session_order_idx
    on public.conversation_turns (session_id, id desc);

create or replace function public.trim_conversation_history()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    delete from public.conversation_turns
    where session_id = new.session_id
      and id not in (
          select id
          from public.conversation_turns
          where session_id = new.session_id
          order by id desc
          limit 16
      );
    return new;
end;
$$;

drop trigger if exists trim_conversation_history_after_insert
    on public.conversation_turns;
create trigger trim_conversation_history_after_insert
after insert on public.conversation_turns
for each row execute function public.trim_conversation_history();

create table if not exists public.documents (
    id uuid primary key,
    session_id text not null references public.chat_sessions(id) on delete cascade,
    filename text not null check (char_length(filename) between 1 and 255),
    content_type text not null,
    storage_path text not null unique,
    chars integer not null check (chars > 0),
    chunk_count integer not null check (chunk_count > 0),
    domain_score real not null,
    created_at timestamptz not null default now()
);

create index if not exists documents_session_created_idx
    on public.documents (session_id, created_at desc);

create table if not exists public.document_chunks (
    id bigint generated always as identity primary key,
    document_id uuid not null references public.documents(id) on delete cascade,
    chunk_index integer not null check (chunk_index >= 0),
    chunk_text text not null,
    embedding extensions.vector(768) not null,
    created_at timestamptz not null default now(),
    unique (document_id, chunk_index)
);

create index if not exists document_chunks_embedding_hnsw_idx
    on public.document_chunks using hnsw (embedding extensions.vector_cosine_ops);

create or replace function public.match_document_chunks(
    match_session_id text,
    query_embedding extensions.vector(768),
    match_count integer default 4,
    min_similarity real default 0.35
)
returns table (
    filename text,
    chunk_text text,
    similarity double precision
)
language sql
stable
set search_path = public, extensions
as $$
    select
        d.filename,
        c.chunk_text,
        (1 - (c.embedding <=> query_embedding))::double precision as similarity
    from public.document_chunks c
    join public.documents d on d.id = c.document_id
    where d.session_id = match_session_id
      and 1 - (c.embedding <=> query_embedding) >= min_similarity
    order by c.embedding <=> query_embedding
    limit greatest(1, least(match_count, 20));
$$;

-- Solo el backend, con SUPABASE_SERVICE_ROLE_KEY, puede acceder a estos datos.
alter table public.chat_sessions enable row level security;
alter table public.conversation_turns enable row level security;
alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;

revoke all on public.chat_sessions, public.conversation_turns,
    public.documents, public.document_chunks from anon, authenticated;
grant usage on schema public, extensions to service_role;
grant all on public.chat_sessions, public.conversation_turns,
    public.documents, public.document_chunks to service_role;
grant usage, select on sequence public.conversation_turns_id_seq,
    public.document_chunks_id_seq to service_role;
grant execute on function public.match_document_chunks(
    text, extensions.vector, integer, real
) to service_role;
revoke execute on function public.match_document_chunks(
    text, extensions.vector, integer, real
) from public, anon, authenticated;

-- Bucket privado: los archivos no quedan expuestos mediante URL pública.
insert into storage.buckets (id, name, public, file_size_limit)
values ('nexo-documents', 'nexo-documents', false, 10485760)
on conflict (id) do update
set public = false, file_size_limit = excluded.file_size_limit;

-- `storage.objects` es una tabla administrada por Supabase: no cambiar su
-- propietario, RLS ni políticas desde este script. El bucket queda privado y
-- el backend accede con service_role, que no se expone al navegador.
