-- Schema for the WhatsApp CRM demo. Kept as plain SQL (no migration
-- framework) on purpose: it's one file, easy to read top to bottom, and the
-- demo doesn't need migration history.

create extension if not exists "pgcrypto";

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    full_name text not null,
    email text not null unique,
    password_hash text not null,
    role text not null default 'agent' check (role in ('admin', 'supervisor', 'agent')),
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists whatsapp_lines (
    id uuid primary key default gen_random_uuid(),
    phone_number text not null unique,
    label text not null,
    status text not null default 'connected',
    agent_id uuid unique references users(id) on delete set null,
    policy_daily integer not null default 250,
    policy_hourly integer not null default 30,
    policy_new_chats_daily integer not null default 30,
    warmup_started_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create table if not exists contacts (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    phone_number text not null,
    crm_account text,
    lifetime_value integer not null default 0,
    last_order_at timestamptz,
    created_at timestamptz not null default now()
);

create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    contact_id uuid not null references contacts(id),
    line_id uuid not null references whatsapp_lines(id),
    first_inbound_at timestamptz,
    last_message_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id),
    direction text not null check (direction in ('inbound', 'outbound')),
    body text not null,
    sent_by_user_id uuid references users(id),
    sent_at timestamptz not null default now()
);

create table if not exists alerts (
    id uuid primary key default gen_random_uuid(),
    kind text not null,
    title text not null,
    detail text,
    user_id uuid references users(id),
    acknowledged boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists call_logs (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id),
    user_id uuid references users(id),
    duration_seconds integer not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists broadcast_runs (
    id uuid primary key default gen_random_uuid(),
    body text not null,
    sent_by_user_id uuid not null references users(id),
    sent_count integer not null default 0,
    skipped_cold_count integer not null default 0,
    forced boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists support_tickets (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    description text not null,
    priority text not null default 'medium' check (priority in ('low', 'medium', 'high', 'urgent')),
    state text not null default 'open' check (state in ('open', 'in_progress', 'resolved')),
    reported_by_user_id uuid not null references users(id),
    admin_note text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists appointments (
    id uuid primary key default gen_random_uuid(),
    agent_id uuid not null references users(id),
    contact_id uuid not null references contacts(id),
    title text not null,
    scheduled_at timestamptz not null,
    done boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists goals (
    id uuid primary key default gen_random_uuid(),
    agent_id uuid not null unique references users(id),
    target_messages_month integer not null default 500,
    target_conversations_month integer not null default 40,
    created_at timestamptz not null default now()
);

create table if not exists promotions (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    body text not null,
    active boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists products (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    price_cents integer not null default 0,
    stock integer not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_conversations_line on conversations(line_id);
create index if not exists idx_messages_conversation on messages(conversation_id);
create index if not exists idx_messages_sent_at on messages(sent_at);
create index if not exists idx_broadcast_runs_sent_by on broadcast_runs(sent_by_user_id);
create index if not exists idx_support_tickets_state on support_tickets(state);
create index if not exists idx_call_logs_conversation on call_logs(conversation_id);
create index if not exists idx_appointments_agent on appointments(agent_id);
