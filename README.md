# WhatsApp CRM Demo

A multichannel sales inbox for teams who sell over WhatsApp — chats, broadcasts,
a supervisor dashboard, and an **anti-ban rate limiter with a warm-up ramp**,
which is the part worth actually reading the code for.

This is a distilled, from-scratch rebuild of patterns from a production
WhatsApp CRM I built for a sales team: real architecture and business logic,
generic data and branding, and a simulated WhatsApp provider instead of a
live number — so it runs anywhere with `docker compose up` and no external
account.

![Inbox screenshot](docs/screenshot-inbox.png)

## Why the rate limiter is the interesting part

WhatsApp bans numbers that look automated, and "automated" mostly means
*sudden volume on a number with no history*. A brand-new number sending 250
messages on day one looks like spam even if a human typed every one of them.

The fix is a ramp: a newly connected line starts at a low ceiling and grows
into its real limit over about a month.

```
days connected   daily limit   hourly limit   new chats/day
0                20            8              3
3                40            12             8
7                70            15             15
14               100           18             20
21               130           20             25
30+              (commercial policy applies as-is)
```

The number enforced right now is always

```
effective_limit = min(commercial_policy, warm_up_tier_for(days_connected))
```

Two lines can share the same commercial policy (say, 250/day) and behave
completely differently depending on how long they've been connected — and a
line that gets reconnected (after a ban, a logout, anything that forces a new
QR scan) goes back to day zero, because WhatsApp treats that the same way it
treats a brand-new number.

The second decision worth noting: **going over the limit doesn't block the
send.** It lets the message through and raises an alert for a supervisor
instead. A hard block protects nobody — the actual ban risk comes from
aggregate volume and how many conversations are cold opens, not from any one
message — and it costs you the sale. See [`rate_limiter.py`](backend/app/services/rate_limiter.py)
for the full reasoning, and [`conversations.py`](backend/app/api/v1/endpoints/conversations.py)
for how sends use it.

## What else is in here

- **Cold vs. warm contacts.** A broadcast skips contacts who've never written
  in first by default (opening many cold conversations at once is the
  clearest spam signal there is), lists who got skipped so the agent can
  follow up, and only includes them with an explicit override — which raises
  an alert rather than silently complying. See [`broadcasts.py`](backend/app/services/broadcasts.py).
- **Role-based access with a twist.** Admins and supervisors can send inside
  any agent's conversation (the message goes out through that agent's line,
  so the customer sees one continuous thread — but it's recorded as sent by
  whoever actually typed it).
- **A live supervisor dashboard**, with usage computed against the *effective*
  limit, not the raw commercial policy — showing 10% used against a policy of
  250 is meaningless if the real ceiling right now is 20 because the line is
  still warming up.

  ![Supervisor dashboard](docs/screenshot-dashboard.png)

- **A simulated WhatsApp provider.** A background task periodically makes a
  random open conversation "reply," so the inbox feels alive during a
  walkthrough with nothing real connected. See [`simulator.py`](backend/app/services/simulator.py).

The admin panel is where the warm-up ramp becomes concrete: three lines, one
policy, three different effective limits.

![Admin panel showing the warm-up ramp](docs/screenshot-admin.png)

## Stack

FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL · React + TypeScript + Vite ·
Docker Compose. Plain SQL for the schema (no migration framework — this is a
demo, not a long-lived project), JWT auth, role-based permissions.

## Running it

```bash
git clone <this-repo>
cd whatsapp-crm-demo
docker compose up -d --build
docker compose exec backend python -m scripts.seed_demo
```

Then open **http://localhost:5173**. All demo accounts use the password
`demo1234`:

| Role | Email | What it shows |
|---|---|---|
| Admin | `admin@demo.com` | Line management, policies, warm-up reset |
| Supervisor | `supervisor@demo.com` | Live agent status, alerts |
| Agent | `nicole@demo.com` | A line that just connected (20 msgs/day cap) |
| Agent | `marcus@demo.com` | A line 10 days into the ramp (70/day) |
| Agent | `priya@demo.com` | A fully warmed up line (full policy, 250/day) |

A background task makes the seeded conversations "reply" every ~12 seconds,
so the inbox has activity without you doing anything.

### Running the backend outside Docker

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
# a local Postgres reachable at the DATABASE_URL in .env.example
python -m scripts.seed_demo
uvicorn app.main:app --reload
```

### Tests

```bash
cd backend
pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql+asyncpg://demo:demo@localhost:5432/demo pytest -q
```

21 tests covering the warm-up ramp's edge cases, the cold/warm broadcast
split, and the "allowed but alerted" rate-limit behavior end to end through
the real HTTP API.

## Project layout

```
backend/
  app/
    core/        config, JWT, auth dependencies
    db/          SQLAlchemy models, session
    services/
      rate_limiter.py   the warm-up ramp (start here)
      broadcasts.py      cold/warm contact logic
      simulator.py       fake WhatsApp replies for the demo
    api/v1/endpoints/    auth, conversations, broadcasts, dashboard, admin
  db/init/       plain-SQL schema
  scripts/       seed_demo.py
  tests/
frontend/
  src/
    pages/       Login, Inbox, SupervisorDashboard, Admin
    api/         typed HTTP client
```

## What this demo leaves out on purpose

The production project this is distilled from also syncs with an ERP for
orders/payments, integrates with a cloud PBX for call-effectiveness metrics,
and runs real WhatsApp sessions through per-line residential proxies (so a
ban on one number doesn't put the others at risk by sharing an IP). Those are
real integrations with another company's infrastructure and aren't something
to publish — the parts here are the ones that are interesting as *general*
engineering, not tied to anyone's specific stack.

## License

MIT — see [LICENSE](LICENSE).
