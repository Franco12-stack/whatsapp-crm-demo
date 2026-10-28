# WhatsApp CRM Demo

A full multichannel sales platform for teams who sell over WhatsApp — chats
with a CRM side panel and call logging, broadcasts, a supervisor dashboard,
support tickets, goals, and an **anti-ban rate limiter with a warm-up ramp**,
which is the part worth actually reading the code for.

This is a distilled, from-scratch rebuild of patterns from a production
WhatsApp CRM I built for a sales team: real architecture and business logic
across every module, generic data and branding, and a simulated WhatsApp
provider instead of a live number — so it runs anywhere with
`docker compose up` and no external account.

**One-click deploy** (free Render hosting, no setup — login details are in
[Running it](#running-it)):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Franco12-stack/whatsapp-crm-demo)

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

## Every module

| Module | What it does |
|---|---|
| **Chats** | The inbox — threads, sending, a CRM side panel (account, lifetime value, last order), call logging, and an "AI suggest reply" button. |
| **Agenda** | Follow-up reminders tied to a contact, scheduled from a conversation. |
| **Contact today** | Warm conversations that have gone quiet 2+ days — a nudge list before a lead goes cold. |
| **Broadcasts** | Bulk sends with the cold/warm split, a recipient picker, and a history of past sends. |
| **My metrics** | An agent's own activity: messages, calls, broadcasts, open tickets, warm/cold split. |
| **Report** | The same metrics, aggregated across the whole team — for a supervisor/admin. |
| **Dashboard** | Live per-agent status against each line's *effective* warm-up limit, plus the alert feed. |
| **Goals** | Monthly targets per agent, with progress computed live (never stale). |
| **Distribute** | Move a conversation to another agent's WhatsApp line. |
| **Promotions** | Reusable broadcast templates — pick one to prefill a broadcast. |
| **Products** | A small catalog so a quote can reference real stock and price. |
| **Support** | A ticket kanban (open / in progress / resolved), with priorities and an admin note. |
| **Administration** | WhatsApp line management, commercial policy, warm-up reset. |
| **AI Assistant** | A reply suggestion button in the chat — honestly labeled as canned/keyword-matched, not a live model call (see below). |

<table>
<tr><td><img src="docs/screenshot-dashboard.png" width="420"/></td><td><img src="docs/screenshot-support.png" width="420"/></td></tr>
<tr><td align="center"><sub>Supervisor dashboard — the warm-up ramp in action</sub></td><td align="center"><sub>Support ticket kanban</sub></td></tr>
<tr><td><img src="docs/screenshot-broadcasts.png" width="420"/></td><td><img src="docs/screenshot-distribute.png" width="420"/></td></tr>
<tr><td align="center"><sub>Broadcasts — recipient picker + history</sub></td><td align="center"><sub>Distribute — reassign a conversation</sub></td></tr>
<tr><td><img src="docs/screenshot-metrics.png" width="420"/></td><td><img src="docs/screenshot-contact-today.png" width="420"/></td></tr>
<tr><td align="center"><sub>My metrics</sub></td><td align="center"><sub>Contact today — quiet warm leads</sub></td></tr>
<tr><td><img src="docs/screenshot-agenda.png" width="420"/></td><td><img src="docs/screenshot-promotions.png" width="420"/></td></tr>
<tr><td align="center"><sub>Agenda</sub></td><td align="center"><sub>Promotions</sub></td></tr>
<tr><td><img src="docs/screenshot-products.png" width="420"/></td><td><img src="docs/screenshot-admin.png" width="420"/></td></tr>
<tr><td align="center"><sub>Products</sub></td><td align="center"><sub>Administration — the ramp, concretely</sub></td></tr>
</table>

## Design decisions worth reading the code for

- **Cold vs. warm contacts.** A broadcast skips contacts who've never written
  in first by default (opening many cold conversations at once is the
  clearest spam signal there is), lists who got skipped so the agent can
  follow up, and only includes them with an explicit override — which raises
  an alert rather than silently complying. See [`broadcasts.py`](backend/app/services/broadcasts.py).
- **Role-based access with a twist.** Admins and supervisors can send inside
  any agent's conversation (the message goes out through that agent's line,
  so the customer sees one continuous thread — but it's recorded as sent by
  whoever actually typed it). Supervisors can *see* WhatsApp lines (needed for
  Distribute) but only admins can edit a policy or reset a warm-up.
- **Usage shown against the effective limit, not the raw policy** — showing
  10% used against a policy of 250 is meaningless if the real ceiling right
  now is 20 because the line is still warming up. Dashboard, Report, and My
  metrics all share one computation (`metrics.py`) so they can't quietly
  disagree on what "this week" means.
- **Goal progress is computed live, never stored** — so it can't go stale
  the way a cached counter would.
- **The AI assistant and the WhatsApp provider are both honestly simulated.**
  A background task makes conversations "reply" so the inbox feels alive; the
  "Suggest reply" button does keyword matching, not a live model call. Both
  say so in the code and, for the AI one, in the API response itself
  (`note: "Demo mode..."`). Wiring a real LLM or a real WhatsApp account into
  a public demo would mean shipping credentials — not worth it to show what's
  genuinely the least interesting part of either integration.

## Stack

FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL · React + TypeScript + Vite ·
Docker Compose. Plain SQL for the schema (no migration framework — this is a
demo, not a long-lived project), JWT auth, role-based permissions.

## Running it

### Option A — one-click deploy (no local setup)

Click the **Deploy to Render** button above, sign in with GitHub, and
confirm. Render provisions a free Postgres database and two web services
from `render.yaml`. No seed step to run — the backend seeds itself on first
boot. Two things to know about the free tier:

- It takes a few minutes the first time (building two Docker images).
- Free services spin down after 15 minutes idle; the first request after
  that wakes it back up in under a minute.

The frontend's API URL is baked in at build time pointing at
`https://whatsapp-crm-demo-backend.onrender.com`. If Render had to rename
your backend service (because that exact name was taken), open the
**whatsapp-crm-demo-frontend** service in the Render dashboard → Environment,
fix `VITE_API_BASE_URL` to match the backend's actual URL, and trigger
**Manual Deploy → Deploy latest commit**.

### Option B — locally with Docker

```bash
git clone <this-repo>
cd whatsapp-crm-demo
docker compose up -d --build
```

No seed step to run here either — same auto-seed as above. (The manual
command still works if you ever want to force a re-check:
`docker compose exec backend python -m scripts.seed_demo`.)

Then open **http://localhost:5173**. All demo accounts use the password
`demo1234`:

| Role | Email | What it shows |
|---|---|---|
| Admin | `admin@demo.com` | Line management, policies, warm-up reset, promotions/products |
| Supervisor | `supervisor@demo.com` | Live agent status, alerts, team report, distribute |
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

33 tests covering the warm-up ramp's edge cases, the cold/warm broadcast
split, role scoping across every module (who can see what, who can edit
what), and the "allowed but alerted" rate-limit behavior end to end through
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
    api/v1/endpoints/
      conversations.py  chats, calls, follow-ups, reassignment
      broadcasts.py     bulk sends + history
      dashboard.py      supervisor live status + alerts
      metrics.py        shared My metrics / Report computation
      admin.py          WhatsApp line management
      support.py        ticket kanban
      appointments.py   Agenda
      goals.py          monthly targets with live progress
      promotions.py     broadcast templates
      products.py       catalog
      ai.py             the "suggest reply" stub
  db/init/       plain-SQL schema
  scripts/       seed_demo.py
  tests/
frontend/
  src/
    pages/       one file per module (Inbox, Agenda, Broadcasts, Metrics,
                  SupervisorDashboard, Goals, Reassign, Promotions, Products,
                  Support, Admin, ContactToday, Login)
    api/         typed HTTP client
```

## What this demo leaves out on purpose

The production project this is distilled from also syncs with a real ERP for
orders/payments, integrates with a real cloud PBX, calls a real LLM for reply
suggestions, and runs real WhatsApp sessions through per-line residential
proxies (so a ban on one number doesn't put the others at risk by sharing an
IP). Those are real integrations with another company's infrastructure and
credentials, and aren't something to publish — what's here is every pattern
and business decision generalized away from them, which is the part that's
actually interesting as engineering.

## License

MIT — see [LICENSE](LICENSE).
